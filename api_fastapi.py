from fastapi import FastAPI, Query, Depends, HTTPException
import psycopg2
import psycopg2.extras
import logging
from typing import Optional, List, Dict, Any
import atexit
import asyncio
from utils import normalize_pubkey, parse_time_filter
from storage import Storage
from fastapi.responses import JSONResponse

app = FastAPI(title="Nostr Harvester API", description="API for querying Nostr events")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Storage instance
storage = Storage()
asyncio.run(storage.initialize())

@app.get("/api/events", response_model=Dict[str, Any])
async def get_events(
    pubkey: Optional[str] = None, 
    relay: Optional[str] = None,
    q: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    kind: Optional[int] = None,
    limit: Optional[int] = Query(100, ge=1, le=1000),
    offset: Optional[int] = Query(0, ge=0)
):
    """
    Get events with optional filters.
    
    - **pubkey**: Filter events by public key (hex or npub format)
    - **relay**: Filter events by the relay they were received from
    - **q**: Search for text within event content
    - **since**: Return events created after this time (timestamp or ISO format)
    - **until**: Return events created before this time (timestamp or ISO format)
    - **kind**: Filter events by kind
    - **limit**: Maximum number of events to return (default: 100, max: 1000)
    - **offset**: Pagination offset (default: 0)
    """
    try:
        # Normalize pubkey if provided
        normalized_pubkey = normalize_pubkey(pubkey) if pubkey else None
        if pubkey and not normalized_pubkey:
            return JSONResponse(
                status_code=400,
                content={
                    'status': 'error',
                    'message': 'Invalid pubkey format. Use either hex or npub format.'
                }
            )

        # Parse time filters
        since_ts = parse_time_filter(since) if since else None
        until_ts = parse_time_filter(until) if until else None

        events, total_count = storage.query_events(
            pubkey=normalized_pubkey,
            relay=relay,
            q=q,
            kind=kind,
            since=since_ts,
            until=until_ts,
            limit=limit,
            offset=offset,
        )
        # Build query
        query = """
            SELECT DISTINCT e.* FROM events e
        """
        params = []
        where_clauses = []

        if relay:
            query += " LEFT JOIN event_sources es ON e.id = es.event_id"
            relay_url = relay if relay.startswith('wss://') else f'wss://{relay}'
            where_clauses.append("es.relay_url = %s")
            params.append(relay_url)

        if normalized_pubkey:
            where_clauses.append("e.pubkey = %s")
            params.append(normalized_pubkey)

        if kind is not None:
            where_clauses.append("e.kind = %s")
            params.append(kind)

        if q:
            where_clauses.append("to_tsvector('english', e.content) @@ plainto_tsquery(%s)")
            params.append(q)

        if since_ts:
            where_clauses.append("e.created_at >= %s")
            params.append(since_ts)
        if until_ts:
            where_clauses.append("e.created_at <= %s")
            params.append(until_ts)

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        # Add ordering and pagination
        query += " ORDER BY e.created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        # Execute query
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(query, params)
            events = cursor.fetchall()

            # Add relay sources and npub for each event
            for event in events:
                cursor.execute(
                    "SELECT relay_url FROM event_sources WHERE event_id = %s", 
                    (event['id'],)
                )
                event['relays'] = [r['relay_url'] for r in cursor.fetchall()]
                event['npub'] = pubkey_to_bech32(event['pubkey'])

            # Get total count for pagination
            count_query = f"SELECT COUNT(DISTINCT e.id) FROM ({query}) as e"
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()['count']

        return {
            'status': 'success',
            'count': len(events),
            'total': total_count,
            'offset': offset,
            'limit': limit,
            'events': events
        }

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )

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

def cleanup():
    """Cleanup database connections"""
    if storage.pool is not None:
        storage.pool.closeall()

# Add cleanup on exit
atexit.register(cleanup)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("api_fastapi:app", host="0.0.0.0", port=8000, reload=True) 
