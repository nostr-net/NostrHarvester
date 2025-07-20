import logging
import asyncio
from common.config import settings

# Import shared Prometheus metrics
from .metrics import (
    EVENTS_QUEUED,
    EVENTS_PROCESSED,
    EVENT_PROCESSING_ERRORS,
    EVENT_QUEUE_SIZE
)

logger = logging.getLogger(__name__)

class EventProcessor:
    def __init__(self, storage):
        self.storage = storage
        self.processing_queue = asyncio.Queue()
        self.seen_events = set()
        self._worker_tasks = []

    async def start(self):
        """Initialize and start the event processing batch workers"""
        logger.info("Starting event processor workers")
        for _ in range(settings.worker_pool_size):
            task = asyncio.create_task(self._batch_worker())
            self._worker_tasks.append(task)

    async def process_event(self, event, relay_url, response_time_ms=None):
        """Add event to processing queue"""
        logger.debug(f"Queuing event {event.get('id')} from {relay_url}")
        await self.processing_queue.put((event, relay_url, response_time_ms))
        EVENTS_QUEUED.inc()
        EVENT_QUEUE_SIZE.set(self.processing_queue.qsize())

    async def _batch_worker(self):
        """Batch events from the queue and process them"""
        logger.info("Batch worker started")
        batch = []
        while True:
            try:
                # Wait for first event
                item = await self.processing_queue.get()
                batch.append(item)
                # Collect up to batch size or until timeout
                while len(batch) < settings.event_batch_size:
                    try:
                        ev = await asyncio.wait_for(
                            self.processing_queue.get(), timeout=settings.event_batch_interval
                        )
                        batch.append(ev)
                    except asyncio.TimeoutError:
                        break
                await self._handle_batch(batch)
                # Mark tasks done
                for _ in batch:
                    self.processing_queue.task_done()
                batch = []
            except asyncio.CancelledError:
                break
            except Exception as e:
                EVENT_PROCESSING_ERRORS.inc()
                logger.error(f"Error in batch worker: {e}")

    async def _handle_batch(self, items):
        """Handle a batch of events, storing new events and their sources"""
        new_events = []
        sources = []
        for event, relay_url, response_time_ms in items:
            event_id = event.get('id')
            if not event_id:
                continue
            if event_id not in self.seen_events:
                self.seen_events.add(event_id)
                new_events.append(event)
            sources.append((event_id, relay_url, response_time_ms))
        if new_events:
            await self.storage.store_events(new_events)
        if sources:
            await self.storage.store_event_sources_batch(sources)
        EVENTS_PROCESSED.inc(len(items))
        EVENT_QUEUE_SIZE.set(self.processing_queue.qsize())

    async def stop(self):
        """Stop the event processor workers"""
        for task in self._worker_tasks:
            task.cancel()
        for task in self._worker_tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
