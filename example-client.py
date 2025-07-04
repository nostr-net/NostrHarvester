#!/usr/bin/env python3
"""
example-client.py

Demonstration script for Nostr Harvester API.
Shows usage of all API endpoints and query parameters.
"""
import os
import time
import requests


def pretty_print(title, data):
    print(f"\n=== {title} ===")
    try:
        import json

        print(json.dumps(data, indent=2))
    except Exception:
        print(data)


def main():
    # Base URL for API (update if necessary)
    base_url = os.getenv("NOSTR_API_URL", "http://localhost:8008/api")

    # Health check
    resp = requests.get(f"{base_url}/health")
    pretty_print("Health Check", resp.json())

    # Stats
    resp = requests.get(f"{base_url}/stats")
    pretty_print("Stats", resp.json())

    # Get recent events (no filters)
    resp = requests.get(f"{base_url}/events", params={"limit": 5})
    pretty_print("Recent Events (limit=5)", resp.json())

    # Filter by pubkey (hex or npub format)
    sample_pubkey = os.getenv("SAMPLE_PUBKEY", "")
    if sample_pubkey:
        resp = requests.get(
            f"{base_url}/events", params={"pubkey": sample_pubkey, "limit": 5}
        )
        pretty_print(f"Events by Pubkey ({sample_pubkey})", resp.json())

    # Filter by relay URL
    sample_relay = "wss://wot.nostr.net"
    resp = requests.get(
        f"{base_url}/events", params={"relay": sample_relay, "limit": 5}
    )
    pretty_print(f"Events by Relay ({sample_relay})", resp.json())

    # Full-text search filter
    query = "nostr"
    resp = requests.get(f"{base_url}/events", params={"q": query, "limit": 5})
    pretty_print(f"Search Events (q={query})", resp.json())

    # Kind filter
    kind = 1
    resp = requests.get(
        f"{base_url}/events", params={"kind": kind, "limit": 5}
    )
    pretty_print(f"Events by Kind (kind={kind})", resp.json())

    # Tag filters (key:value). Use SAMPLE_TAGS env var (comma-separated)
    tags_env = os.getenv("SAMPLE_TAGS", "")
    tags = [t for t in tags_env.split(",") if t]
    if tags:
        # 'tag' parameter is repeatable
        params = [("tag", t) for t in tags]
        params += [("limit", 5)]
        resp = requests.get(f"{base_url}/events", params=params)
        pretty_print(f"Events by Tags {tags}", resp.json())

    # Time range filters (since / until)
    now = int(time.time())
    since = now - 3600  # last hour
    until = now
    resp = requests.get(
        f"{base_url}/events", params={"since": since, "until": until, "limit": 5}
    )
    pretty_print(f"Events in Last Hour (since={since}, until={until})", resp.json())

    # Pagination example (limit & offset)
    p1 = requests.get(
        f"{base_url}/events", params={"limit": 3, "offset": 0}
    ).json()
    p2 = requests.get(
        f"{base_url}/events", params={"limit": 3, "offset": 3}
    ).json()
    pretty_print("Pagination Page 1 (limit=3, offset=0)", p1)
    pretty_print("Pagination Page 2 (limit=3, offset=3)", p2)


if __name__ == "__main__":
    main()