import logging
import json
import asyncio
from collections import defaultdict

logger = logging.getLogger(__name__)

class EventProcessor:
    def __init__(self, storage):
        self.storage = storage
        self.processing_queue = asyncio.Queue()
        self.seen_events = set()
        self._queue_task = None

    async def start(self):
        """Initialize and start the event processing queue"""
        logger.info("Starting event processor queue")
        self._queue_task = asyncio.create_task(self.process_queue())

    async def process_event(self, event, relay_url, response_time_ms=None):
        """Add event to processing queue"""
        logger.debug(f"Queuing event {event.get('id')} from {relay_url}")
        await self.processing_queue.put((event, relay_url, response_time_ms))

    async def process_queue(self):
        """Process events from the queue"""
        logger.info("Event queue processor started")
        while True:
            try:
                event, relay_url, response_time_ms = await self.processing_queue.get()
                await self.handle_event(event, relay_url, response_time_ms)
                self.processing_queue.task_done()
            except Exception as e:
                logger.error(f"Error processing event: {e}")

    async def handle_event(self, event, relay_url, response_time_ms):
        """Process and store a single event"""
        try:
            event_id = event.get('id')
            if not event_id:
                logger.warning("Event missing ID, skipping")
                return

            # Check if we've seen this event before
            if event_id not in self.seen_events:
                self.seen_events.add(event_id)
                # Store the event and its source
                await self.storage.store_event(event)
                await self.storage.store_event_source(event_id, relay_url, response_time_ms)
                logger.debug(f"Stored new event {event_id} from {relay_url}")
            else:
                # Just store the additional source
                await self.storage.store_event_source(event_id, relay_url, response_time_ms)
                logger.debug(f"Added source {relay_url} for existing event {event_id}")

        except Exception as e:
            logger.error(f"Error handling event: {e}")

    async def stop(self):
        """Stop the event processor"""
        if self._queue_task:
            self._queue_task.cancel()
            try:
                await self._queue_task
            except asyncio.CancelledError:
                pass