-- Create materialized views for common aggregates

-- Total event and pubkey counts
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_event_counts AS
SELECT
    COUNT(*) AS total_events,
    COUNT(DISTINCT pubkey) AS unique_pubkeys
FROM events;

-- Relay statistics: number of distinct events per relay
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_relay_stats AS
SELECT
    relay_url,
    COUNT(DISTINCT event_id) AS event_count
FROM event_sources
GROUP BY relay_url;

-- Add unique index to support REFRESH MATERIALIZED VIEW CONCURRENTLY if needed
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_relay_stats_relay_url
    ON mv_relay_stats (relay_url);