from flask import Flask, request, jsonify
import asyncio
import logging
import json
from utils import normalize_pubkey, pubkey_to_bech32, parse_time_filter

from storage import Storage
import psycopg2

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Storage instance
storage = Storage()
asyncio.run(storage.initialize())

@app.route('/api/events', methods=['GET'])
def get_events():
    """Get events with optional filters.

    Query parameters:
    - **tag**: Filter events containing tag key:value pairs. Can be repeated.
    """
    conn = None
    try:
        # Extract and validate parameters
        raw_pubkey = request.args.get('pubkey')
        relay = request.args.get('relay')
        search_text = request.args.get('q')
        since = request.args.get('since')
        until = request.args.get('until')
        kind = request.args.get('kind')
        tags = request.args.getlist('tag')
        limit = min(int(request.args.get('limit', 100)), 1000)
        offset = max(0, int(request.args.get('offset', 0)))

        # Normalize pubkey if provided
        pubkey = normalize_pubkey(raw_pubkey) if raw_pubkey else None
        if raw_pubkey and not pubkey:
            return jsonify({
                'status': 'error',
                'message': 'Invalid pubkey format. Use either hex or npub format.'
            }), 400

        # Validate kind parameter
        if kind:
            try:
                kind = int(kind)
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid kind parameter. Must be an integer.'
                }), 400

        # Parse time filters
        since_ts = parse_time_filter(since) if since else None
        until_ts = parse_time_filter(until) if until else None

        # Parse tag filters key:value
        tag_pairs = []
        for tag in tags:
            if ':' not in tag:
                return jsonify({
                    'status': 'error',
                    'message': 'Tag filters must be in key:value format'
                }), 400
            k, v = tag.split(':', 1)
            tag_pairs.append([k, v])

        events, total_count = storage.query_events(
            pubkey=pubkey,
            relay=relay,
            q=search_text,
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

        if pubkey:
            where_clauses.append("e.pubkey = %s")
            params.append(pubkey)

        if kind is not None:
            where_clauses.append("e.kind = %s")
            params.append(kind)

        for k, v in tag_pairs:
            where_clauses.append("(e.raw_data->'tags') @> %s::jsonb")
            params.append(json.dumps([[k, v]]))

        if search_text:
            where_clauses.append("to_tsvector('english', e.content) @@ plainto_tsquery(%s)")
            params.append(search_text)

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

        return jsonify({
            'status': 'success',
            'count': len(events),
            'total': total_count,
            'offset': offset,
            'limit': limit,
            'events': events
        })

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics about indexed events and relays."""
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

            return jsonify({
                'status': 'success',
                'stats': {
                    'total_events': total_events,
                    'unique_pubkeys': unique_pubkeys,
                    'relays': relay_stats
                }
            })

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if conn:
            storage.pool.putconn(conn)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Basic health check endpoint"""
    try:
        # Test database connection
        conn = storage.pool.getconn()
        storage.pool.putconn(conn)
        return jsonify({
            'status': 'success',
            'message': 'API server is running and database is accessible'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Database connection error: {str(e)}'
        }), 500

def cleanup():
    """Cleanup database connections"""
    if storage.pool is not None:
        storage.pool.closeall()

# Add cleanup on exit
import atexit
atexit.register(cleanup)

if __name__ == '__main__':
    logger.info("Starting API server...")
    app.run(host='0.0.0.0', port=5001, debug=True)
