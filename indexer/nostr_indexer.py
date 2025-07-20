#!/usr/bin/env python3

import asyncio
import logging
import json
from indexer.relay_manager import RelayManager
from indexer.event_processor import EventProcessor
from common.storage import Storage
from indexer.config_manager import ConfigManager
from common.config import settings
from prometheus_client import start_http_server, Gauge, Counter

logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import shared Prometheus metrics
from .metrics import (
    EVENTS_RECEIVED,
    EVENTS_PROCESSED,
    EVENTS_FAILED,
    NOTIFICATION_ERRORS,
    RELAYS_CONFIGURED,
    RELAYS_CONNECTED,
    DB_ACTIVE_CONNECTIONS,
    DB_IDLE_CONNECTIONS,
    DB_OPERATIONS
)


class NostrIndexer:
    def __init__(self):
        self.storage = Storage()
        self.event_processor = EventProcessor(self.storage)
        self.config_manager = ConfigManager()
        self.relay_manager = RelayManager(self.config_manager, self.event_processor)

    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing storage...")
        await self.storage.initialize()
        # Start Prometheus metrics server if enabled
        if settings.metrics_server_enabled:
            start_http_server(settings.metrics_server_port)
            logger.info(f"Prometheus metrics server started on port {settings.metrics_server_port}")
            asyncio.create_task(self._metrics_refresh_loop())

        logger.info("Starting event processor...")
        await self.event_processor.start()

        logger.info("Initialization complete")

    async def start(self):
        """Start the indexer"""
        try:
            logger.info("Starting Nostr indexer...")
            await self.initialize()
            await self.relay_manager.connect_all()

            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        except Exception as e:
            logger.error(f"Error running indexer: {e}")
            raise
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up...")
        await self.event_processor.stop()
        await self.relay_manager.disconnect_all()

    async def _metrics_refresh_loop(self):
        """Background task to update Prometheus metrics periodically"""
        while True:
            # Configured relay count
            RELAYS_CONFIGURED.set(len(self.config_manager.get_relays()))
            # Database pool connections
            pool = getattr(self.storage, 'pool', None)
            if pool:
                try:
                    active = len(pool._used)
                    idle = len(pool._pool)
                except Exception:
                    active = idle = 0
            else:
                active = idle = 0
            DB_ACTIVE_CONNECTIONS.set(active)
            DB_IDLE_CONNECTIONS.set(idle)
            # Wait before next update
            await asyncio.sleep(settings.metrics_refresh_interval_seconds)

    def query_events(
        self,
        pubkey=None,
        relay=None,
        q=None,
        kind=None,
        tags=None,
        since=None,
        until=None,
        limit=100,
        offset=0,
    ):
        """
        Query stored events with optional filters.

        - pubkey: Filter events by public key (hex or npub format)
        - relay: Filter events by the relay they were received from
        - q: Search for text within event content
        - kind: Filter events by kind
        - tags: Filter events containing tag key:value pairs. List of [key, value] lists
        - since: Return events created after this time (timestamp or ISO format)
        - until: Return events created before this time (timestamp or ISO format)
        - limit: Maximum number of events to return (default: 100)
        - offset: Pagination offset (default: 0)
        """
        return self.storage.query_events(
            pubkey=pubkey,
            relay=relay,
            q=q,
            kind=kind,
            tags=tags,
            since=since,
            until=until,
            limit=limit,
            offset=offset,
        )

    def get_event_sources(self, event_id):
        """Get relays where an event was found"""
        return self.storage.get_event_sources(event_id)


def main():
    indexer = NostrIndexer()
    try:
        asyncio.run(indexer.start())
    except KeyboardInterrupt:
        logger.info("Indexer stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
