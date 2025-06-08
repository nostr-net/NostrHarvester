# Nostr Harvester

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
