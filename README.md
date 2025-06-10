# Nostr Harvester

This project indexes Nostr events and exposes them via a FastAPI service.

## Running with Docker

1. Ensure Docker and Docker Compose are installed.
2. Copy the provided `docker-compose.yml` and start the services:

```bash
docker-compose up --build
```

Ensure you have a `indexer/config.json` file (or copy from `indexer/config.json.example`) specifying your relay list; this file will be mounted into the indexer container.

The API will be available at `http://localhost:8008`.
The web UI will be available at `http://localhost:8080`.

The indexer service will also be started, connecting to relays and populating the database.

### Environment Variables

The application reads PostgreSQL connection details from environment variables. When using the provided `docker-compose.yml`, these are set automatically:

- `PGDATABASE` – database name (default: `nostr`)
- `PGUSER` – database user (default: `nostr`)
- `PGPASSWORD` – database password (default: `nostr`)
- `PGHOST` – PostgreSQL host (default: `db` in Docker)
- `PGPORT` – PostgreSQL port (default: `5432`)
- `RELAY_CONFIG_PATH` – path to indexer relay config file (default: `config.json`)
- `APP_CONFIG_PATH` – path to general application JSON config file for hierarchical overrides (default: `config.json`)
- `HEALTH_ENABLED` – enable health endpoint (`true`/`false`, default: `true`)
- `METRICS_ENABLED` – enable metrics endpoint (`true`/`false`, default: `true`)
- `LOG_LEVEL` – logging level (e.g., `INFO`, default: `INFO`)
- `DB_LOG_LEVEL` – PostgreSQL server log severity threshold (`debug`, `info`, `notice`, `warning`, `error`, default: `warning`)
- `DB_LOG_STATEMENT` – level of statement logging (`none`, `ddl`, `mod`, `all`, default: `none`)

### Phase 2 Settings
- `EVENT_BATCH_SIZE` – number of events to batch before database write (default: `100`)
- `EVENT_BATCH_INTERVAL` – max seconds to wait for batch before write (default: `1.0`)
- `WORKER_POOL_SIZE` – number of concurrent batch worker tasks (default: `4`)
- `CIRCUIT_BREAKER_FAILURE_THRESHOLD` – consecutive failures before opening circuit breaker (default: `5`)
- `CIRCUIT_BREAKER_RECOVERY_TIMEOUT` – seconds to wait before half-open state (default: `60`)
- `RATE_LIMIT_ENABLED` – enable API rate limiting (`true`/`false`, default: `false`)
- `RATE_LIMIT_REQUESTS_PER_MINUTE` – max requests per IP per minute (default: `60`)
- `MAX_EVENT_QUERY_LIMIT` – maximum allowed `limit` parameter for `/api/events` (default: `500`)

### Phase 3 Settings
- `CACHE_ENABLED` – enable in-memory caching for expensive queries (`true`/`false`, default: `false`)
- `CACHE_TTL_SECONDS` – TTL (in seconds) for cached responses (default: `60`)
- `CACHE_MAXSIZE` – maximum number of entries in the cache (default: `128`)
- `USE_MATERIALIZED_VIEWS` – enable reading from materialized views for stats endpoint (`true`/`false`, default: `false`)
- `MATVIEW_REFRESH_INTERVAL_SECONDS` – seconds between periodic refresh of materialized views (`0` to disable, default: `0`)
- `PG_POOL_MIN_SIZE` – minimum number of connections in the database connection pool (default: `1`)
- `PG_POOL_MAX_SIZE` – maximum number of connections in the database connection pool (default: `10`)
- `CONFIG_HOT_RELOAD_ENABLED` – enable runtime hot-reloading of the relay config file (`true`/`false`, default: `false`)
- `CONFIG_HOT_RELOAD_DEBOUNCE_SECONDS` – debounce interval for config file reload in seconds (default: `1.0`)

- `METRICS_SERVER_ENABLED` – start Prometheus metrics server for indexer (`true`/`false`, default: `false`)
- `METRICS_SERVER_PORT` – port for Prometheus metrics server (default: `8000`)
- `METRICS_REFRESH_INTERVAL_SECONDS` – seconds between metrics updates (default: `5.0`)

- `REQUEST_MAX_SIZE_BYTES` – maximum request size in bytes for API requests (`0` to disable, default: `0`)
- `MAX_QUERY_LENGTH` – maximum length of text search query `q` (default: `500`)
- `API_AUTH_ENABLED` – require Bearer token authentication for all API endpoints (`true`/`false`, default: `false`)
- `API_AUTH_TOKEN` – shared secret token for Bearer authentication when enabled (default: empty)

You can override them by editing `docker-compose.yml` or providing your own environment file.

See `api/api_documentation.md` for API usage examples.

## Web UI

A simple search interface inspired by early-day Google is available at `http://localhost:8080`. Enter a query using Google-style filters (e.g., `bitcoin kind:1 tag:e:some_event_id since:2025-06-01`) to search events. Supported filters:

- `pubkey:<hex_or_npub>` filter by author public key
- `relay:<url>` filter by relay URL
- `kind:<number>` filter by event kind
- `since:<timestamp_or_ISO>` and `until:<timestamp_or_ISO>` filter by creation time
- `tag:<key>:<value>` filter by tag key:value pairs (repeatable)
- `limit:<number>` and `offset:<number>` for pagination
- free text terms for full-text content search
- prefix `-` to any filter or term to exclude matching events (e.g., `-"bitcoin"`, `-kind:1`)

Nostr Harvester indexes events from a list of Nostr relays and exposes them through a small FastAPI service.  It stores events in PostgreSQL and keeps track of which relay each event came from.

## Installation

Each service has its own Python dependencies:

```bash
# Install API service dependencies
pip install -r api/requirements.txt

# Install Indexer service dependencies
pip install -r indexer/requirements.txt
```

Optionally, install test dependencies:

```bash
pip install -e .[test]
```

## Usage

### Local Execution

#### Harvester API

Start the API using Uvicorn:

```bash
uvicorn api.api_fastapi:app --reload
```

#### Indexer

Start the indexer (ensure `indexer/config.json` is present with your relay list):

```bash
python -m indexer.nostr_indexer
```

