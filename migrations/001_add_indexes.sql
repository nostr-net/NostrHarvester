-- Add necessary indexes for performance

CREATE INDEX IF NOT EXISTS idx_events_created_at_desc ON events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_pubkey_created_at ON events(pubkey, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_kind_created_at ON events(kind, created_at DESC);

-- Full-text search index on event content
CREATE INDEX IF NOT EXISTS idx_events_content_gin ON events USING gin(to_tsvector('english', content));

-- JSONB index on tags array for efficient tag lookups
CREATE INDEX IF NOT EXISTS idx_events_tags_gin ON events USING gin((raw_data->'tags'));