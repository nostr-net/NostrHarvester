import asyncio
import json
import logging

from common.config import settings
from common.circuit_breaker import CircuitBreaker

# Import shared Prometheus metrics
from .metrics import EVENTS_RECEIVED, NOTIFICATION_ERRORS
from nostr_sdk import Client, Filter, HandleNotification

logger = logging.getLogger(__name__)


class RelayManager:
    """
    RelayManager using nostr_sdk to connect to relays,
    subscribe to events, and forward them to the event processor.
    """

    class _NotificationHandler(HandleNotification):
        def __init__(self, event_processor):
            self._event_processor = event_processor

        async def handle(self, relay_url, subscription_id, event):
            try:
                EVENTS_RECEIVED.labels(relay_url).inc()
                # Convert Event object to JSON dict
                event_json = event.as_json()
                event_data = json.loads(event_json)

                # Compute response time in milliseconds
                now = int(asyncio.get_event_loop().time())
                created_at = event_data.get("created_at", 0)
                if not isinstance(created_at, int) or created_at < 0:
                    logger.warning(
                        f"Invalid created_at in event {event_data.get('id')}: {created_at}, using 0"
                    )
                    created_at = 0

                response_sec = max(0, now - created_at)
                if response_sec > 86400:
                    logger.warning(
                        f"Unusually high response time ({response_sec}s) for event "
                        f"{event_data.get('id')} from {relay_url}"
                    )
                response_ms = min(response_sec * 1000, 2147483647)

                await self._event_processor.process_event(event_data, relay_url, response_ms)
            except Exception as e:
                NOTIFICATION_ERRORS.inc()
                logger.error(f"Error in notification handler: {e}")

        async def handle_msg(self, relay_url, msg):
            # No-op for non-EVENT messages
            pass

    def __init__(self, config_manager, event_processor):
        self._config_manager = config_manager
        self._event_processor = event_processor
        self._client = Client()
        self._handler = self._NotificationHandler(event_processor)
        self._running = False
        # Circuit breakers per relay URL
        self._breakers: dict[str, CircuitBreaker] = {}

    async def connect_all(self):
        """
        Connect to all relays with circuit breaker protection,
        subscribe to all events, and start handling notifications.
        """
        self._running = True
        relays = self._config_manager.get_relays()
        for url in relays:
            # Initialize circuit breaker for relay if needed
            cb = self._breakers.get(url)
            if cb is None:
                cb = CircuitBreaker(
                    settings.circuit_breaker_failure_threshold,
                    settings.circuit_breaker_recovery_timeout,
                )
                self._breakers[url] = cb
            if not cb.allow_request():
                logger.warning(f"Circuit open for {url}, skipping relay connection")
                continue
            try:
                await self._client.add_relay(url)
            except Exception as e:
                logger.error(f"Error adding relay {url}: {e}")
                cb.record_failure()
            else:
                cb.record_success()
        await self._client.connect()

        await self._client.subscribe(Filter())

        # Process incoming events until stopped
        await self._client.handle_notifications(self._handler)

    async def disconnect_all(self):
        """
        Stop handling notifications and disconnect the client.
        """
        self._running = False
        try:
            close_fn = getattr(self._client, "close", None)
            if close_fn:
                result = close_fn()
                if asyncio.iscoroutine(result):
                    await result
        except Exception as e:
            logger.debug(f"Ignored exception during nostr_sdk client shutdown: {e}")