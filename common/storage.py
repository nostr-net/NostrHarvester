import os
import json
import logging
import asyncio
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor
from .utils import pubkey_to_bech32
from .config import settings

logger = logging.getLogger(__name__)

class Storage:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.pool = None
        self.db_config = {
            'dbname': settings.pg_database,
            'user': settings.pg_user,
            'password': settings.pg_password,
            'host': settings.pg_host,
            'port': settings.pg_port,
        }
        self._max_retries = 3
        self._retry_delay = 1  # seconds

    async def _init_pool(self):
        """Initialize the connection pool with retries"""
        for attempt in range(self._max_retries):
            try:
                if not self.pool:
                    self.pool = SimpleConnectionPool(
                        settings.pool_min_size,
                        settings.pool_max_size,
                        **self.db_config
                    )
                return True
            except Exception as e:
                if attempt == self._max_retries - 1:
                    logger.error(f"Failed to initialize connection pool after {self._max_retries} attempts: {e}")
                    raise
                logger.warning(f"Failed to initialize pool (attempt {attempt + 1}), retrying...")
                await asyncio.sleep(self._retry_delay)
        return False

    async def initialize(self):
        """Initialize the database with required schema"""
        async with self.lock:
            logger.info("Initializing PostgreSQL database")
            try:
                await self._init_pool()

                # Run versioned database migrations instead of legacy schema file
                await self._run_migrations()
            except Exception as e:
                logger.error(f"Error initializing database: {e}")
                raise

    async def _run_migrations(self):
        """Run any pending SQL migration scripts in migrations/ directory."""
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version VARCHAR(255) PRIMARY KEY,
                        applied_at TIMESTAMP NOT NULL DEFAULT now()
                    )
                """)
                conn.commit()
                migrations_dir = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), '..', 'migrations')
                )
                if not os.path.isdir(migrations_dir):
                    logger.warning(
                        f"No migrations directory found at {migrations_dir}, skipping migrations"
                    )
                    return
                for filename in sorted(os.listdir(migrations_dir)):
                    if not filename.endswith('.sql'):
                        continue
                    version = filename.split('_', 1)[0]
                    cursor.execute(
                        "SELECT 1 FROM schema_migrations WHERE version = %s", (version,)
                    )
                    if cursor.fetchone():
                        continue
                    logger.info(f"Applying migration {filename}")
                    with open(os.path.join(migrations_dir, filename), 'r') as f:
                        cursor.execute(f.read())
                    cursor.execute(
                        "INSERT INTO schema_migrations (version) VALUES (%s)", (version,)
                    )
                    conn.commit()
            logger.info("Database migrations applied successfully")
        finally:
            self.pool.putconn(conn)

    async def store_event(self, event):
        """Store a Nostr event"""
        if not self.pool:
            await self.initialize()

        async with self.lock:
            conn = self.pool.getconn()
            try:
                with conn.cursor() as cursor:
                    # Ensure created_at is within valid range for BIGINT
                    created_at = event.get('created_at', 0)
                    if not isinstance(created_at, int) or created_at < 0:
                        logger.warning(f"Invalid created_at value: {created_at}, using 0 instead")
                        created_at = 0

                    cursor.execute("""
                        INSERT INTO events (
                            id, pubkey, created_at, kind, content, sig, raw_data
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                    """, (
                        event.get('id'),
                        event.get('pubkey'),
                        created_at,
                        event.get('kind'),
                        event.get('content'),
                        event.get('sig'),
                        json.dumps(event)
                    ))
                    if cursor.rowcount > 0:
                        logger.debug(f"Stored new event {event.get('id')}")
                conn.commit()
            except Exception as e:
                logger.error(f"Error storing event {event.get('id')}: {e}")
                conn.rollback()
                raise
            finally:
                self.pool.putconn(conn)

    async def store_event_source(self, event_id, relay_url, response_time_ms=None):
        """Store the relay source for an event with timing information"""
        if not self.pool:
            await self.initialize()

        async with self.lock:
            conn = self.pool.getconn()
            try:
                with conn.cursor() as cursor:
                    # Store timestamp in seconds
                    current_time = int(asyncio.get_event_loop().time())

                    # Ensure response_time_ms is within valid integer range
                    if response_time_ms and response_time_ms > 2147483647:  # max 32-bit integer
                        logger.warning(f"Response time {response_time_ms}ms exceeds maximum value, capping at 2147483647")
                        response_time_ms = 2147483647

                    # Handle negative response times (clock skew or future events)
                    if response_time_ms and response_time_ms < 0:
                        logger.warning(f"Negative response time {response_time_ms}ms, setting to 0")
                        response_time_ms = 0

                    cursor.execute("""
                        INSERT INTO event_sources (
                            event_id, relay_url, first_seen_at, response_time_ms
                        ) VALUES (%s, %s, %s, %s)
                        ON CONFLICT (event_id, relay_url) DO NOTHING
                    """, (
                        event_id,
                        relay_url,
                        current_time,
                        response_time_ms
                    ))
                    if cursor.rowcount > 0:
                        logger.debug(f"Added source {relay_url} for event {event_id}")
                conn.commit()
            except Exception as e:
                logger.error(f"Error storing event source for {event_id}: {e}")
                conn.rollback()
            finally:
                self.pool.putconn(conn)

    def query_events(
        self,
        pubkey=None,
        relay=None,
        q=None,
        kind=None,
        tags=None,
        since=None,
        until=None,
        limit=100,
        offset=0,
        not_pubkey=None,
        not_relay=None,
        not_q=None,
        not_kind=None,
        not_tags=None,
        not_since=None,
        not_until=None,
    ):
        """
        Query events with optional filters.

        Parameters:
            pubkey: Filter events by public key (hex)
            relay: Filter events by the relay they were received from
            q: Search for text within event content
            kind: Filter events by kind
            tags: Filter events containing tag key:value pairs. List of [key, value] lists
            since: Return events created after this time (timestamp or ISO format)
            until: Return events created before this time (timestamp or ISO format)
            limit: Maximum number of events to return (default: 100)
            offset: Pagination offset (default: 0)
            not_pubkey: Exclude events from this public key
            not_relay: Exclude events from this relay
            not_q: Exclude events matching this text query
            not_kind: Exclude events of this kind
            not_tags: Exclude events containing tag key:value pairs. List of [key, value] lists
            not_since: Exclude events created after this time
            not_until: Exclude events created before this time

        Returns a tuple of (events, total_count).
        """
        if not self.pool:
            raise RuntimeError("Database not initialized")

        conn = self.pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query = "SELECT DISTINCT e.* FROM events e"
                joins = []
                wheres = []
                params = []

                if relay:
                    joins.append("LEFT JOIN event_sources es ON e.id = es.event_id")
                    relay_url = relay if relay.startswith("wss://") else f"wss://{relay}"
                    wheres.append("es.relay_url = %s")
                    params.append(relay_url)

                if pubkey:
                    wheres.append("e.pubkey = %s")
                    params.append(pubkey)

                if kind is not None:
                    wheres.append("e.kind = %s")
                    params.append(kind)

                if tags:
                    for tag in tags:
                        wheres.append("(e.raw_data->'tags') @> %s::jsonb")
                        params.append(json.dumps([tag]))

                if q:
                    wheres.append(
                        "to_tsvector('english', e.content) @@ plainto_tsquery('english', %s)"
                    )
                    params.append(q)

                if since is not None:
                    wheres.append("e.created_at >= %s")
                    params.append(since)
                if until is not None:
                    wheres.append("e.created_at <= %s")
                    params.append(until)

                # Negative time filters
                if not_since is not None:
                    wheres.append("e.created_at < %s")
                    params.append(not_since)
                if not_until is not None:
                    wheres.append("e.created_at > %s")
                    params.append(not_until)

                # Negative relay and key filters
                if not_relay:
                    neg_relay = not_relay if not_relay.startswith("wss://") else f"wss://{not_relay}"
                    wheres.append(
                        "e.id NOT IN (SELECT event_id FROM event_sources WHERE relay_url = %s)"
                    )
                    params.append(neg_relay)

                if not_pubkey:
                    wheres.append("e.pubkey != %s")
                    params.append(not_pubkey)

                if not_kind is not None:
                    wheres.append("e.kind != %s")
                    params.append(not_kind)

                # Negative tag filters
                if not_tags:
                    for tag in not_tags:
                        wheres.append("NOT ((e.raw_data->'tags') @> %s::jsonb)")
                        params.append(json.dumps([tag]))

                # Negative full-text filters
                if not_q:
                    wheres.append(
                        "NOT (to_tsvector('english', e.content) @@ plainto_tsquery('english', %s))"
                    )
                    params.append(not_q)

                if joins:
                    query += " " + " ".join(joins)
                if wheres:
                    query += " WHERE " + " AND ".join(wheres)

                query += " ORDER BY e.created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])

                cursor.execute(query, params)
                events = cursor.fetchall()

                for event in events:
                    cursor.execute(
                        "SELECT relay_url FROM event_sources WHERE event_id = %s",
                        (event["id"],),
                    )
                    event["relays"] = [r["relay_url"] for r in cursor.fetchall()]
                    event["npub"] = pubkey_to_bech32(event["pubkey"])

                count_query = "SELECT COUNT(DISTINCT e.id) FROM events e"
                if joins:
                    count_query += " " + " ".join(joins)
                if wheres:
                    count_query += " WHERE " + " AND ".join(wheres)
                cursor.execute(count_query, params[:-2])
                total_count = cursor.fetchone()["count"]

                return events, total_count
        finally:
            self.pool.putconn(conn)

    async def store_events(self, events):
        if not events:
            return
        if not self.pool:
            await self.initialize()
        async with self.lock:
            conn = self.pool.getconn()
            try:
                with conn.cursor() as cursor:
                    values = [
                        (
                            e.get('id'),
                            e.get('pubkey'),
                            e.get('created_at', 0) if isinstance(e.get('created_at', 0), int) and e.get('created_at', 0) >= 0 else 0,
                            e.get('kind'),
                            e.get('content'),
                            e.get('sig'),
                            json.dumps(e),
                        )
                        for e in events
                    ]
                    args_str = ",".join(
                        cursor.mogrify("(%s,%s,%s,%s,%s,%s,%s)", v).decode() for v in values
                    )
                    cursor.execute(
                        f"INSERT INTO events (id, pubkey, created_at, kind, content, sig, raw_data) "
                        f"VALUES {args_str} ON CONFLICT (id) DO NOTHING"
                    )
                conn.commit()
            finally:
                self.pool.putconn(conn)

    async def store_event_sources_batch(self, sources):
        if not sources:
            return
        if not self.pool:
            await self.initialize()
        async with self.lock:
            conn = self.pool.getconn()
            try:
                with conn.cursor() as cursor:
                    values = []
                    for event_id, relay_url, response_time_ms in sources:
                        current_time = int(asyncio.get_event_loop().time())
                        rt = response_time_ms if isinstance(response_time_ms, int) else None
                        if rt and rt > 2147483647:
                            rt = 2147483647
                        if rt and rt < 0:
                            rt = 0
                        values.append((event_id, relay_url, current_time, rt))
                    args_str = ",".join(
                        cursor.mogrify("(%s,%s,%s,%s)", v).decode() for v in values
                    )
                    cursor.execute(
                        f"""
                        INSERT INTO event_sources (
                            event_id, relay_url, first_seen_at, response_time_ms
                        )
                        SELECT t.event_id, t.relay_url, t.first_seen_at, t.response_time_ms
                        FROM (VALUES {args_str}) AS t(
                            event_id, relay_url, first_seen_at, response_time_ms
                        )
                        WHERE EXISTS (
                            SELECT 1 FROM events e WHERE e.id = t.event_id
                        )
                        ON CONFLICT (event_id, relay_url) DO NOTHING
                        """
                    )
                conn.commit()
            finally:
                self.pool.putconn(conn)

    def get_event_sources(self, event_id):
        """Get all relays where an event was found"""
        if not self.pool:
            raise RuntimeError("Database not initialized")

        conn = self.pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT relay_url FROM event_sources 
                    WHERE event_id = %s
                """, (event_id,))
                return [row[0] for row in cursor.fetchall()]
        finally:
            self.pool.putconn(conn)

    def __del__(self):
        """Cleanup connection pool on deletion"""
        if self.pool:
            self.pool.closeall()
