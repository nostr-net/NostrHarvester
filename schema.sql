CREATE TABLE IF NOT EXISTS events (
    id VARCHAR(64) PRIMARY KEY,
    pubkey VARCHAR(64) NOT NULL,
    created_at BIGINT NOT NULL,  -- Changed to BIGINT for larger range
    kind INTEGER NOT NULL,
    content TEXT,
    sig VARCHAR(128) NOT NULL,
    raw_data JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS event_sources (
    event_id VARCHAR(64),
    relay_url TEXT,
    first_seen_at BIGINT NOT NULL,  -- Changed to BIGINT for larger range
    response_time_ms INTEGER,
    PRIMARY KEY (event_id, relay_url),
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

-- Optimize indexes for PostgreSQL
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind);
CREATE INDEX IF NOT EXISTS idx_events_pubkey ON events(pubkey);
CREATE INDEX IF NOT EXISTS idx_event_sources_relay_url ON event_sources(relay_url);
CREATE INDEX IF NOT EXISTS idx_event_sources_first_seen ON event_sources(first_seen_at DESC);

-- Add GiST index for faster text search
CREATE INDEX IF NOT EXISTS idx_events_content_gin ON events USING gin(to_tsvector('english', content));
-- Index JSONB tags for efficient tag lookups
CREATE INDEX IF NOT EXISTS idx_events_tags_gin ON events USING gin((raw_data->'tags'));
