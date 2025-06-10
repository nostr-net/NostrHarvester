-- Initial schema migration: create events and event_sources tables

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