# Nostr Harvester

This project indexes Nostr events and exposes them via a FastAPI service.

## Running with Docker

1. Ensure Docker and Docker Compose are installed.
2. Copy the provided `docker-compose.yml` and start the services:

```bash
docker-compose up --build
```

The API will be available at `http://localhost:8000`.

### Environment Variables

The application reads PostgreSQL connection details from environment variables. When using the provided `docker-compose.yml`, these are set automatically:

- `PGDATABASE` – database name (default: `nostr`)
- `PGUSER` – database user (default: `nostr`)
- `PGPASSWORD` – database password (default: `nostr`)
- `PGHOST` – PostgreSQL host (default: `db` in Docker)
- `PGPORT` – PostgreSQL port (default: `5432`)

You can override them by editing `docker-compose.yml` or providing your own environment file.

See `api_documentation.md` for API usage examples.
Nostr Harvester indexes events from a list of Nostr relays and exposes them through a small FastAPI service.  It stores events in PostgreSQL and keeps track of which relay each event came from.

## Installation

Create a Python virtual environment and install the required packages:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For running the test suite also install the optional dependencies:

```bash
pip install -e .[test]
```

## Usage

Start the harvester API using `uvicorn`:

```bash
python api_fastapi.py
```

The script `nostr_indexer.py` contains the logic for connecting to relays and storing events.

