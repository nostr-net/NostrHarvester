from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import asyncio
import os
from watchgod import awatch
import hmac
from typing import Optional, List, Dict, Any
import atexit
from common.utils import normalize_pubkey, parse_time_filter
from common.storage import Storage
from common.config import settings, reload_settings
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import psycopg2
import psycopg2.extras
from cachetools import TTLCache
import re
from api.static_server import mount_static_files

# Sanitization patterns for query parameters
SAFE_QUERY_PATTERN = re.compile(r'^[\w\s\-\.\:]+$')
SAFE_PUBKEY_PATTERN = re.compile(r'^[a-fA-F0-9]{64}$|^npub1[a-zA-Z0-9]+$')
SAFE_RELAY_PATTERN = re.compile(r'^wss?://[a-zA-Z0-9\-\.]+(?::[0-9]+)?(?:/[a-zA-Z0-9\-\._~:/?#[\]@!$&\'()*+,;=]*)?$')
SAFE_TAG_PATTERN = re.compile(r'^[a-zA-Z0-9\-\._~:/?#[\]@!$&\'()*+,;=]+:[a-zA-Z0-9\-\._~:/?#[\]@!$&\'()*+,;=]*$')

app = FastAPI(title="Nostr Harvester API", description="API for querying Nostr events")

# Configure CORS with environment variable for allowed origins
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:8080,http://localhost:18080").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

# Storage instance
# Storage instance
storage = Storage()

# In-memory TTL cache for expensive query results (e.g., stats)
stats_cache = TTLCache(maxsize=settings.cache_maxsize, ttl=settings.cache_ttl_seconds)

# In-memory rate limiting: mapping of client IP to request timestamps
ip_request_log: dict[str, list[float]] = {}

@app.on_event("startup")
async def startup():
    await storage.initialize()
    # Schedule periodic refresh of materialized views if enabled
    if settings.use_materialized_views and settings.matview_refresh_interval_seconds > 0:
        asyncio.create_task(_refresh_materialized_views_loop())
    if settings.config_hot_reload_enabled:
        asyncio.create_task(_config_hot_reload_loop())


# Security hardening: API authentication middleware
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Skip authentication for public endpoints
    public_endpoints = ["/health", "/metrics", "/favicon.ico", "/robots.txt", "/"]
    
    # Also skip authentication for paths that browsers commonly request
    skip_auth_patterns = [
        "/.well-known/",  # Various browser/app checks
        "/apple-touch-icon",  # iOS devices
        "/browserconfig.xml",  # Windows tiles
        "/sitemap.xml",  # Search engines
    ]
    
    path = request.url.path
    
    if path in public_endpoints:
        return await call_next(request)
    
    # Check if path starts with any of the skip patterns
    for pattern in skip_auth_patterns:
        if path.startswith(pattern):
            return await call_next(request)
    
    if not settings.api_auth_enabled:
        return await call_next(request)
    auth_header = request.headers.get("Authorization", "")
    token = settings.api_auth_token
    # Expect header in form 'Bearer <token>'
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    provided = auth_header[len("Bearer "):].strip()
    # Constant-time comparison to mitigate timing attacks
    if not hmac.compare_digest(provided, token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await call_next(request)


# Security hardening: request size limiting middleware
@app.middleware("http")
async def request_size_limit_middleware(request: Request, call_next):
    max_bytes = settings.request_max_size_bytes
    if max_bytes > 0:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > max_bytes:
            raise HTTPException(status_code=413, detail="Request body too large")
    return await call_next(request)


# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if not settings.rate_limit_enabled:
        return await call_next(request)
    ip = request.client.host
    now = time.time()
    window_start = now - 60
    timestamps = ip_request_log.get(ip, [])
    timestamps = [t for t in timestamps if t > window_start]
    timestamps.append(now)
    ip_request_log[ip] = timestamps
    if len(timestamps) > settings.rate_limit_requests_per_minute:
        raise HTTPException(status_code=429, detail="Too many requests")
    return await call_next(request)

# Prometheus metrics definitions and middleware
REQUEST_COUNT = Counter(
    'http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'http_status']
)
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds', 'HTTP request latency', ['method', 'endpoint']
)

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    if not settings.metrics_enabled:
        return await call_next(request)
    start_time = time.time()
    response = await call_next(request)
    resp_time = time.time() - start_time
    REQUEST_LATENCY.labels(request.method, request.url.path).observe(resp_time)
    REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
    return response

@app.get("/metrics")
async def metrics_endpoint():
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="Metrics disabled")
    data = generate_latest()
    return Response(data, media_type=CONTENT_TYPE_LATEST)

@app.get("/api/events", response_model=Dict[str, Any])
async def get_events(
    pubkey: Optional[str] = None,
    relay: Optional[str] = None,
    q: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    kind: Optional[int] = None,
    tags: Optional[List[str]] = Query(None, alias='tag'),
    not_pubkey: Optional[str] = Query(None, alias='not-pubkey'),
    not_relay: Optional[str] = Query(None, alias='not-relay'),
    not_q: Optional[str] = Query(None, alias='not-q'),
    not_kind: Optional[int] = Query(None, alias='not-kind'),
    not_tags: Optional[List[str]] = Query(None, alias='not-tag'),
    not_since: Optional[str] = Query(None, alias='not-since'),
    not_until: Optional[str] = Query(None, alias='not-until'),
    limit: Optional[int] = Query(
        settings.max_event_query_limit, ge=1, le=settings.max_event_query_limit
    ),
    offset: Optional[int] = Query(0, ge=0),
):
    """
    Get events with optional filters.

    - **pubkey**: Filter events by public key (hex or npub format)
    - **relay**: Filter events by the relay they were received from
    - **q**: Search for text within event content
    - **since**: Return events created after this time (timestamp or ISO format)
    - **until**: Return events created before this time (timestamp or ISO format)
    - **kind**: Filter events by kind
    - **tag**: Filter events containing tag key:value pairs. Can be repeated.
    - **not-pubkey**: Exclude events from this public key
    - **not-relay**: Exclude events from this relay
    - **not-q**: Exclude events matching this text query
    - **not-kind**: Exclude events of this kind
    - **not-tag**: Exclude events containing tag key:value pairs. Can be repeated.
    - **not-since**: Exclude events created after this time
    - **not-until**: Exclude events created before this time
    - **limit**: Maximum number of events to return (default: 100, max: 1000)
    - **offset**: Pagination offset (default: 0)
    """
    # Input sanitization for search query
    if q is not None:
        if len(q) > settings.max_query_length:
            raise HTTPException(
                status_code=400,
                detail=f"Query parameter 'q' too long (max {settings.max_query_length})"
            )
        if not SAFE_QUERY_PATTERN.match(q):
            raise HTTPException(
                status_code=400,
                detail="Invalid characters in query parameter 'q'"
            )
    if not_q is not None:
        if len(not_q) > settings.max_query_length:
            raise HTTPException(
                status_code=400,
                detail=f"Exclusion query parameter 'not-q' too long (max {settings.max_query_length})"
            )
        if not SAFE_QUERY_PATTERN.match(not_q):
            raise HTTPException(
                status_code=400,
                detail="Invalid characters in exclusion query parameter 'not-q'"
            )
    
    # Validate pubkey format
    if pubkey is not None and not SAFE_PUBKEY_PATTERN.match(pubkey):
        raise HTTPException(
            status_code=400,
            detail="Invalid pubkey format. Must be 64-character hex or npub format."
        )
    if not_pubkey is not None and not SAFE_PUBKEY_PATTERN.match(not_pubkey):
        raise HTTPException(
            status_code=400,
            detail="Invalid not-pubkey format. Must be 64-character hex or npub format."
        )
    
    # Validate relay URL format
    if relay is not None and not SAFE_RELAY_PATTERN.match(relay):
        raise HTTPException(
            status_code=400,
            detail="Invalid relay URL format."
        )
    if not_relay is not None and not SAFE_RELAY_PATTERN.match(not_relay):
        raise HTTPException(
            status_code=400,
            detail="Invalid not-relay URL format."
        )
    
    # Validate tag format
    if tags:
        for tag in tags:
            if not SAFE_TAG_PATTERN.match(tag):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid tag format: {tag}. Must be in key:value format with safe characters."
                )
    if not_tags:
        for tag in not_tags:
            if not SAFE_TAG_PATTERN.match(tag):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid not-tag format: {tag}. Must be in key:value format with safe characters."
                )
    
    # Validate kind parameter ranges
    if kind is not None and (kind < 0 or kind > 65535):
        raise HTTPException(
            status_code=400,
            detail="Invalid kind value. Must be between 0 and 65535."
        )
    if not_kind is not None and (not_kind < 0 or not_kind > 65535):
        raise HTTPException(
            status_code=400,
            detail="Invalid not-kind value. Must be between 0 and 65535."
        )
    
    conn = None
    try:
        # Normalize pubkey if provided
        normalized_pubkey = normalize_pubkey(pubkey) if pubkey else None
        if pubkey and not normalized_pubkey:
            return JSONResponse(
                status_code=400,
                content={
                    'status': 'error', 'message': 'Invalid pubkey format. Use either hex or npub format.'
                }
            )

        # Normalize not-pubkey if provided
        normalized_not_pubkey = normalize_pubkey(not_pubkey) if not_pubkey else None
        if not_pubkey and not normalized_not_pubkey:
            return JSONResponse(
                status_code=400,
                content={
                    'status': 'error', 'message': 'Invalid not-pubkey format. Use either hex or npub format.'
                }
            )

        # Parse time filters
        since_ts = parse_time_filter(since) if since else None
        until_ts = parse_time_filter(until) if until else None

        # Parse negative time filters
        not_since_ts = parse_time_filter(not_since) if not_since else None
        not_until_ts = parse_time_filter(not_until) if not_until else None

        # Parse tag filters in the format key:value
        tag_pairs = []
        if tags:
            for tag in tags:
                if ':' not in tag:
                    return JSONResponse(
                        status_code=400,
                        content={'status': 'error', 'message': 'Tag filters must be in key:value format'}
                    )
                k, v = tag.split(':', 1)
                tag_pairs.append([k, v])

        # Parse negative tag filters in the format key:value
        not_tag_pairs = []
        if not_tags:
            for tag in not_tags:
                if ':' not in tag:
                    return JSONResponse(
                        status_code=400,
                        content={'status': 'error', 'message': 'Tag filters must be in key:value format'}
                    )
                k, v = tag.split(':', 1)
                not_tag_pairs.append([k, v])

        events, total_count = storage.query_events(
            pubkey=normalized_pubkey,
            relay=relay,
            q=q,
            kind=kind,
            tags=tag_pairs if tag_pairs else None,
            since=since_ts,
            until=until_ts,
            not_pubkey=normalized_not_pubkey,
            not_relay=not_relay,
            not_q=not_q,
            not_kind=not_kind,
            not_tags=not_tag_pairs if not_tag_pairs else None,
            not_since=not_since_ts,
            not_until=not_until_ts,
            limit=limit,
            offset=offset,
        )
        return {
            'status': 'success',
            'count': len(events),
            'total': total_count,
            'offset': offset,
            'limit': limit,
            'events': events
        }

    except Exception:
        logger.exception("Error processing request")
        # Hide internal errors from clients
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
    finally:
        if conn:
            storage.pool.putconn(conn)

@app.get("/api/stats", response_model=Dict[str, Any])
async def get_stats():
    """
    Get statistics about indexed events and relays.
    """
    # Return cached stats if enabled and unexpired
    if settings.cache_enabled and "stats" in stats_cache:
        return stats_cache["stats"]

    conn = None
    try:
        conn = storage.pool.getconn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            if settings.use_materialized_views:
                # Read aggregated stats from materialized views
                cursor.execute(
                    "SELECT total_events, unique_pubkeys FROM mv_event_counts"
                )
                row = cursor.fetchone()
                total_events = row['total_events']
                unique_pubkeys = row['unique_pubkeys']
                cursor.execute(
                    "SELECT relay_url, event_count FROM mv_relay_stats ORDER BY event_count DESC"
                )
                relay_stats = cursor.fetchall()
            else:
                # Direct aggregation queries
                cursor.execute("SELECT COUNT(*) as count FROM events")
                total_events = cursor.fetchone()['count']

                cursor.execute("SELECT COUNT(DISTINCT pubkey) as count FROM events")
                unique_pubkeys = cursor.fetchone()['count']

                cursor.execute("""
                    SELECT relay_url, COUNT(DISTINCT event_id) as event_count
                    FROM event_sources
                    GROUP BY relay_url
                    ORDER BY event_count DESC
                """)
                relay_stats = cursor.fetchall()

            result = {
                'status': 'success',
                'stats': {
                    'total_events': total_events,
                    'unique_pubkeys': unique_pubkeys,
                    'relays': relay_stats
                }
            }
            if settings.cache_enabled:
                stats_cache["stats"] = result
            return result

    except Exception:
        logger.exception("Error getting stats")
        # Hide internal errors from clients
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
    finally:
        if conn:
            storage.pool.putconn(conn)

@app.get("/health", response_model=Dict[str, Any])
async def health_check():
    """
    Basic health check endpoint (database connectivity).
    """
    if not settings.health_enabled:
        raise HTTPException(status_code=503, detail="Health checks disabled")
    try:
        conn = storage.pool.getconn()
        storage.pool.putconn(conn)
        return {
            'status': 'success',
            'message': 'API server is running and database is accessible'
        }
    except Exception as e:
        logger.exception("Database connection error")
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable"
        )

@app.get("/favicon.ico")
async def favicon():
    """
    Return empty favicon to prevent 404 errors from browsers.
    """
    return Response(content="", media_type="image/x-icon")

@app.get("/robots.txt")
async def robots():
    """
    Basic robots.txt to prevent search engine crawling.
    """
    return Response(content="User-agent: *\nDisallow: /\n", media_type="text/plain")

# Mount static files for web interface
mount_static_files(app)

@app.on_event("shutdown")
def cleanup():
    """Cleanup database connections"""
    if storage.pool is not None:
        storage.pool.closeall()

# Add cleanup on exit
atexit.register(cleanup)

async def _refresh_materialized_views_loop():
    """Background task to periodically refresh materialized views."""
    while True:
        await asyncio.sleep(settings.matview_refresh_interval_seconds)
        conn = None
        try:
            conn = storage.pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute("REFRESH MATERIALIZED VIEW mv_event_counts")
                cursor.execute("REFRESH MATERIALIZED VIEW mv_relay_stats")
                conn.commit()
                logger.info("Refreshed materialized views")
        except Exception as e:
            logger.error(f"Error refreshing materialized views: {e}")
        finally:
            if conn:
                storage.pool.putconn(conn)

async def _config_hot_reload_loop():
    """Watch the relay config file for changes and reload settings at runtime."""
    path = settings.relay_config_path
    directory = os.path.dirname(path) or "."
    filename = os.path.basename(path)
    async for changes in awatch(directory):
        for _change_type, changed_path in changes:
            if os.path.basename(changed_path) == filename:
                await asyncio.sleep(settings.config_hot_reload_debounce_seconds)
                try:
                    reload_settings()
                    logger.info(f"Reloaded configuration from {path}")
                except Exception as e:
                    logger.error(f"Error reloading configuration: {e}")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("api.api_fastapi:app", host="0.0.0.0", port=8000, reload=True)
