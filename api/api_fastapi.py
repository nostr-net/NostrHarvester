from fastapi import FastAPI, Query, Depends, HTTPException
import psycopg2
import psycopg2.extras
import logging
from typing import Optional, List, Dict, Any
import atexit
from common.utils import normalize_pubkey, parse_time_filter
from common.storage import Storage
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Nostr Harvester API", description="API for querying Nostr events")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Storage instance
storage = Storage()

@app.on_event("startup")
async def startup():
    await storage.initialize()

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
    limit: Optional[int] = Query(100, ge=1, le=1000),
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

    except Exception as e:
        logger.exception(f"Error processing request: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )
    finally:
        if conn:
            storage.pool.putconn(conn)

@app.get("/api/stats", response_model=Dict[str, Any])
async def get_stats():
    """
    Get statistics about indexed events and relays.
    """
    conn = None
    try:
        conn = storage.pool.getconn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            # Get total events
            cursor.execute("SELECT COUNT(*) as count FROM events")
            total_events = cursor.fetchone()['count']

            # Get unique pubkeys
            cursor.execute("SELECT COUNT(DISTINCT pubkey) as count FROM events")
            unique_pubkeys = cursor.fetchone()['count']

            # Get relay stats
            cursor.execute("""
                SELECT relay_url, COUNT(DISTINCT event_id) as event_count
                FROM event_sources
                GROUP BY relay_url
                ORDER BY event_count DESC
            """)
            relay_stats = cursor.fetchall()

            return {
                'status': 'success',
                'stats': {
                    'total_events': total_events,
                    'unique_pubkeys': unique_pubkeys,
                    'relays': relay_stats
                }
            }

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting stats: {str(e)}"
        )
    finally:
        if conn:
            storage.pool.putconn(conn)

@app.get("/api/health", response_model=Dict[str, Any])
async def health_check():
    """
    Basic health check endpoint
    """
    try:
        # Test database connection
        conn = storage.pool.getconn()
        storage.pool.putconn(conn)
        return {
            'status': 'success',
            'message': 'API server is running and database is accessible'
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection error: {str(e)}"
        )

@app.on_event("shutdown")
def cleanup():
    """Cleanup database connections"""
    if storage.pool is not None:
        storage.pool.closeall()

# Add cleanup on exit
atexit.register(cleanup)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("api.api_fastapi:app", host="0.0.0.0", port=8000, reload=True)
