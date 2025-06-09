# AGENTS Instructions

This repository contains a Nostr event indexer, FastAPI service, and simple web interface.

## Project Structure

- `api/` - FastAPI service exposing endpoints and documentation. Includes:
  - `api_fastapi.py` - FastAPI app.
  - `api_documentation.md` - Example usage and docs.
  - `client_example.py` - Example Python client.
  - `Dockerfile` and `requirements.txt` for container setup.

- `indexer/` - Indexer service that connects to Nostr relays and stores events in PostgreSQL. Key modules:
  - `nostr_indexer.py` - Main entry point for running the indexer.
  - `relay_manager.py` - Manages connections to relays using `nostr_sdk`.
  - `event_processor.py` - Processes incoming events and stores them via the `Storage` class.
  - `config_manager.py` and `config.json` - Manage relay configuration.
  - `Dockerfile` and `requirements.txt` for container setup.

- `common/` - Shared utilities:
  - `storage.py` - Database access layer using psycopg2.
  - `utils.py` - Helper functions for pubkey conversion and time parsing.

- `web/` - Minimal HTML/JS frontend for searching events.

- `tests/` - Pytest suite with basic placeholder tests.

Other root files include `docker-compose.yml` for running services together, `schema.sql` with PostgreSQL schema, and `pyproject.toml` defining Python dependencies.

