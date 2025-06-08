
# Nostr Indexer API Documentation

This document provides information on how to use the Nostr Indexer API, which allows you to query and retrieve Nostr events that have been indexed from various relays.

## Base URL

The API is accessible at: `https://your-app-domain.replit.app/api/`

## Endpoints

### 1. Get Events

Retrieve events with optional filtering.

**Endpoint:** `GET /api/events`

**Query Parameters:**

| Parameter | Type   | Description |
|-----------|--------|-------------|
| pubkey    | string | Filter events by public key (hex or npub format) |
| relay     | string | Filter events by the relay they were received from |
| q         | string | Search for text within event content |
| since     | string | Return events created after this time (timestamp or ISO format) |
| until     | string | Return events created before this time (timestamp or ISO format) |
| kind      | number | Filter events by kind |
| tag       | string | Filter events by tag key:value pair (repeatable) |
| limit     | number | Maximum number of events to return (default: 100, max: 1000) |
| offset    | number | Pagination offset (default: 0) |

**Response:**

```json
{
  "status": "success",
  "count": 5,
  "total": 120,
  "offset": 0,
  "limit": 5,
  "events": [
    {
      "id": "event_id",
      "pubkey": "public_key_hex",
      "npub": "npub_bech32",
      "created_at": 1677839462,
      "kind": 1,
      "content": "Hello Nostr!",
      "sig": "signature",
      "relays": ["wss://relay1.com", "wss://relay2.com"]
    },
    // More events...
  ]
}
```

### 2. Get Stats

Get statistics about indexed events and relays.

**Endpoint:** `GET /api/stats`

**Response:**

```json
{
  "status": "success",
  "stats": {
    "total_events": 15240,
    "unique_pubkeys": 425,
    "relays": [
      {
        "relay_url": "wss://relay.damus.io",
        "event_count": 4289
      },
      // More relay stats...
    ]
  }
}
```

### 3. Health Check

Check if the API server is running and the database is accessible.

**Endpoint:** `GET /api/health`

**Response:**

```json
{
  "status": "success",
  "message": "API server is running and database is accessible"
}
```

## Examples

### Python Examples

#### Installation

```bash
pip install requests
```

#### Get Events

```python
import requests

# Base URL of the API
base_url = "https://your-app-domain.replit.app/api"

# Get events from a specific user
def get_user_events(npub=None, limit=10):
    params = {
        'pubkey': npub,
        'limit': limit
    }
    response = requests.get(f"{base_url}/events", params=params)
    return response.json()

# Search for events containing specific text
def search_events(query, limit=10):
    params = {
        'q': query,
        'limit': limit
    }
    response = requests.get(f"{base_url}/events", params=params)
    return response.json()

# Get events from a specific relay
def get_relay_events(relay_url, limit=10):
    params = {
        'relay': relay_url,
        'limit': limit
    }
    response = requests.get(f"{base_url}/events", params=params)
    return response.json()

# Get events within a time range
def get_events_by_time(since=None, until=None, limit=10):
    params = {
        'limit': limit
    }
    if since:
        params['since'] = since  # Unix timestamp or ISO format
    if until:
        params['until'] = until  # Unix timestamp or ISO format
    
    response = requests.get(f"{base_url}/events", params=params)
    return response.json()

# Get API stats
def get_stats():
    response = requests.get(f"{base_url}/stats")
    return response.json()

# Check API health
def check_health():
    response = requests.get(f"{base_url}/health")
    return response.json()

# Example usage
if __name__ == "__main__":
    # Get events from a specific user
    user_events = get_user_events(npub="npub1abc123...")
    print(f"Found {user_events['count']} events for user")
    
    # Search for events containing "bitcoin"
    search_results = search_events("bitcoin")
    print(f"Found {search_results['count']} events containing 'bitcoin'")
    
    # Get latest events from a specific relay
    relay_events = get_relay_events("wss://relay.damus.io")
    print(f"Found {relay_events['count']} events from relay.damus.io")
    
    # Get events from the last 24 hours
    import time
    yesterday = int(time.time()) - (24 * 60 * 60)
    recent_events = get_events_by_time(since=yesterday)
    print(f"Found {recent_events['count']} events from the last 24 hours")
    
    # Get API stats
    stats = get_stats()
    print(f"Total events indexed: {stats['stats']['total_events']}")
    print(f"Unique pubkeys: {stats['stats']['unique_pubkeys']}")
    
    # Check API health
    health = check_health()
    print(f"API health: {health['status']}")
```

### cURL Examples

#### Get Recent Events

```bash
curl -X GET "https://your-app-domain.replit.app/api/events?limit=5"
```

#### Get Events from a Specific User

```bash
curl -X GET "https://your-app-domain.replit.app/api/events?pubkey=npub1abcdef...&limit=10"
```

#### Search for Events

```bash
curl -X GET "https://your-app-domain.replit.app/api/events?q=bitcoin&limit=10"
```

#### Get Events from a Specific Relay

```bash
curl -X GET "https://your-app-domain.replit.app/api/events?relay=wss://relay.damus.io&limit=10"
```

#### Get Events by Kind

```bash
curl -X GET "https://your-app-domain.replit.app/api/events?kind=1&limit=10"
```

#### Get Events in a Time Range

```bash
curl -X GET "https://your-app-domain.replit.app/api/events?since=1677839462&until=1677925862&limit=10"
```

#### Get API Stats

```bash
curl -X GET "https://your-app-domain.replit.app/api/stats"
```

#### Health Check

```bash
curl -X GET "https://your-app-domain.replit.app/api/health"
```

## Client Library

You can create a simple Python client library to interact with the API:

```python
import requests

class NostrIndexerClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
    
    def get_events(self, pubkey=None, relay=None, query=None,
                  since=None, until=None, kind=None, tags=None,
                  limit=100, offset=0):
        """Get events with optional filters"""
        params = {
            'limit': limit,
            'offset': offset
        }
        
        if pubkey:
            params['pubkey'] = pubkey
        if relay:
            params['relay'] = relay
        if query:
            params['q'] = query
        if since:
            params['since'] = since
        if until:
            params['until'] = until
        if kind is not None:
            params['kind'] = kind
        if tags:
            for t in tags:
                params.setdefault('tag', []).append(t)
            
        response = requests.get(f"{self.base_url}/api/events", params=params)
        return response.json()
    
    def get_stats(self):
        """Get statistics about indexed events and relays"""
        response = requests.get(f"{self.base_url}/api/stats")
        return response.json()
    
    def check_health(self):
        """Check API health"""
        response = requests.get(f"{self.base_url}/api/health")
        return response.json()

# Example usage
if __name__ == "__main__":
    client = NostrIndexerClient("https://your-app-domain.replit.app")
    
    # Get recent events
    events = client.get_events(limit=5)
    print(f"Recent events: {events['count']}")
    
    # Check top relays
    stats = client.get_stats()
    for relay in stats['stats']['relays'][:3]:
        print(f"Relay: {relay['relay_url']}, Events: {relay['event_count']}")
```
