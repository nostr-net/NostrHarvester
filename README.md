# Nostr Harvester

This project indexes Nostr events and exposes them via a FastAPI service.

## Running with Docker

1. Ensure Docker and Docker Compose are installed.
2. Copy the provided `docker-compose.yml` and start the services:

```bash
docker-compose up --build
```

Ensure you have a `indexer/config.json` file (or copy from `indexer/config.json.example`) specifying your relay list; this file will be mounted into the indexer container.

The API will be available at `http://localhost:8000`.

The indexer service will also be started, connecting to relays and populating the database.

### Environment Variables

The application reads PostgreSQL connection details from environment variables. When using the provided `docker-compose.yml`, these are set automatically:

- `PGDATABASE` – database name (default: `nostr`)
- `PGUSER` – database user (default: `nostr`)
- `PGPASSWORD` – database password (default: `nostr`)
- `PGHOST` – PostgreSQL host (default: `db` in Docker)
- `PGPORT` – PostgreSQL port (default: `5432`)

You can override them by editing `docker-compose.yml` or providing your own environment file.

See `api/api_documentation.md` for API usage examples.
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

