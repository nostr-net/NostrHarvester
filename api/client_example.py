
import requests
import time
import json

class NostrIndexerClient:
    def __init__(self, base_url):
        """Initialize the client with the API base URL
        
        Args:
            base_url (str): Base URL of the Nostr Indexer API
        """
        self.base_url = base_url.rstrip('/')
    
    def get_events(self, pubkey=None, relay=None, query=None,
                  since=None, until=None, kind=None, tags=None,
                  limit=100, offset=0):
        """Get events with optional filters
        
        Args:
            pubkey (str, optional): Public key in hex or npub format
            relay (str, optional): Relay URL to filter by
            query (str, optional): Text to search in content
            since (int/str, optional): Start time (timestamp or ISO)
            until (int/str, optional): End time (timestamp or ISO)
            kind (int, optional): Event kind
            tags (list[str], optional): Tag filters in 'key:value' format
            limit (int, optional): Max number of events to return
            offset (int, optional): Pagination offset
            
        Returns:
            dict: API response with events and metadata
        """
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
        """Get statistics about indexed events and relays
        
        Returns:
            dict: Statistics about indexed events and relays
        """
        response = requests.get(f"{self.base_url}/api/stats")
        return response.json()
    
    def check_health(self):
        """Check API health
        
        Returns:
            dict: Health status of the API
        """
        response = requests.get(f"{self.base_url}/api/health")
        return response.json()

def demonstrate_client():
    """Demonstrate usage of the Nostr Indexer client"""
    # Replace with your actual API URL
    client = NostrIndexerClient("https://your-app-domain.replit.app")
    
    # Check API health
    print("Checking API health...")
    health = client.check_health()
    print(json.dumps(health, indent=2))
    
    # Get API stats
    print("\nGetting API stats...")
    stats = client.get_stats()
    print(json.dumps(stats, indent=2))
    
    # Get recent events
    print("\nGetting recent events...")
    events = client.get_events(limit=3)
    print(f"Found {events['count']} events (showing {len(events['events'])})")
    for event in events['events']:
        print(f"Event {event['id'][:8]}... from {event['npub'][:8]}...: {event['content'][:50]}...")
    
    # Get events from the last 24 hours
    print("\nGetting events from last 24 hours...")
    yesterday = int(time.time()) - (24 * 60 * 60)
    recent_events = client.get_events(since=yesterday, limit=3)
    print(f"Found {recent_events['count']} events in the last 24 hours")
    
    # Search for specific content
    print("\nSearching for 'bitcoin'...")
    search_results = client.get_events(query="bitcoin", limit=3)
    print(f"Found {search_results['count']} events containing 'bitcoin'")
    
    # Get events from a specific relay
    print("\nGetting events from relay.damus.io...")
    relay_events = client.get_events(relay="wss://relay.damus.io", limit=3)
    print(f"Found {relay_events['count']} events from relay.damus.io")

if __name__ == "__main__":
    demonstrate_client()
