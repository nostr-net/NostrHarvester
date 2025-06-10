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

## Project Guidelines
- **Code Quality**: Follow PEP 8 style guide. Use type hints and docstrings.
- **Testing**: Write tests for new features. Use pytest for unit tests.
- **Documentation**: Update API docs and README with new features. Use OpenAPI for API specs.
- **Docker**: Use Docker for development and deployment. Always use "docker compose".
- **File**: Keep files small and focused. Use modules to organize code logically, less than 500 lines per file.
- **Configuration**: Use environment variables for sensitive data. Centralize configuration management.
- **Version Control**: Use Git for version control. Commit often with clear messages.
- **Dependencies**: Use `requirements.txt` for Python dependencies. Keep it up to date.