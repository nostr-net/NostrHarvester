#!/usr/bin/env python3
import asyncio
import logging
import json
from relay_manager import RelayManager
from event_processor import EventProcessor
from storage import Storage
from config_manager import ConfigManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


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

    def query_events(self, filters=None):
        """Query stored events with optional filters"""
        return self.storage.query_events(filters)

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
