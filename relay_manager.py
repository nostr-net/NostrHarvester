import asyncio
import json
import logging
import ssl
import websockets
from websockets.exceptions import WebSocketException

logger = logging.getLogger(__name__)

class RelayManager:
    def __init__(self, config_manager, event_processor):
        self.config_manager = config_manager
        self.event_processor = event_processor
        self.connections = {}
        self.subscription_id = "global_sub"
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        self._running = True

    async def connect_relay(self, relay_url):
        """Connect to a single relay and maintain the connection"""
        while self._running:
            try:
                async with websockets.connect(
                    relay_url,
                    ssl=self.ssl_context
                ) as websocket:
                    logger.info(f"Connected to {relay_url}")
                    self.connections[relay_url] = websocket

                    # Subscribe to all events
                    subscription = json.dumps([
                        "REQ",
                        self.subscription_id,
                        {}  # Empty filter to get all events
                    ])
                    await websocket.send(subscription)
                    logger.info(f"Subscribed to events on {relay_url}")

                    while self._running:
                        try:
                            message = await websocket.recv()
                            await self.handle_message(message, relay_url)
                        except WebSocketException:
                            break

            except WebSocketException as e:
                logger.error(f"WebSocket error for {relay_url}: {e}")
                if self._running:
                    await asyncio.sleep(5)  # Wait before reconnecting
            except Exception as e:
                logger.error(f"Unexpected error for {relay_url}: {e}")
                if self._running:
                    await asyncio.sleep(5)

    async def handle_message(self, message, relay_url):
        """Process incoming messages from relays"""
        try:
            data = json.loads(message)
            if len(data) >= 3:
                if data[0] == "EVENT":
                    # Extract the event data and calculate response time in milliseconds
                    event = data[2]

                    # Validate event timestamp
                    event_time = event.get('created_at', 0)
                    if not isinstance(event_time, int) or event_time < 0:
                        logger.warning(
                            f"Invalid event timestamp from {relay_url}: {event_time}, using 0"
                        )
                        event_time = 0

                    current_time = int(asyncio.get_event_loop().time())

                    # Calculate response time, ensuring it doesn't exceed max integer
                    # and handling future-dated events (negative response times)
                    response_time = max(0, current_time - event_time)  # ensure non-negative
                    response_time_ms = min(response_time * 1000, 2147483647)  # cap at max 32-bit int

                    # Safeguard against extreme values - add logging for diagnosis
                    if response_time > 86400:  # More than 24 hours
                        logger.warning(
                            f"Unusually high response time ({response_time}s) for event {event.get('id')} from {relay_url}. Event time: {event_time}, Current time: {current_time}"
                        )

                    logger.debug(f"Received event {event.get('id')} from {relay_url}")
                    await self.event_processor.process_event(
                        event, relay_url, int(response_time_ms)
                    )
                elif data[0] == "EOSE":
                    logger.info(f"End of stored events from {relay_url}")
                else:
                    logger.debug(f"Received message type {data[0]} from {relay_url}")
            else:
                logger.error(f"Unexpected message format from {relay_url}: {data}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from {relay_url}: {message}")
        except Exception as e:
            logger.error(f"Error processing message from {relay_url}: {e}")

    async def update_connections(self):
        """Update relay connections based on config"""
        while self._running:
            current_relays = set(self.config_manager.get_relays())
            connected_relays = set(self.connections.keys())

            # Remove disconnected relays
            for relay in connected_relays - current_relays:
                if relay in self.connections:
                    try:
                        await self.connections[relay].close()
                        logger.info(f"Disconnected from removed relay: {relay}")
                    except Exception:
                        pass
                    del self.connections[relay]

            # Add new relays
            for relay in current_relays - connected_relays:
                asyncio.create_task(self.connect_relay(relay))

            await asyncio.sleep(30)  # Check for updates every 30 seconds

    async def connect_all(self):
        """Connect to all configured relays"""
        self._running = True
        relays = self.config_manager.get_relays()
        connection_tasks = [
            asyncio.create_task(self.connect_relay(url))
            for url in relays
        ]
        # Start the update task
        update_task = asyncio.create_task(self.update_connections())
        connection_tasks.append(update_task)
        await asyncio.gather(*connection_tasks, return_exceptions=True)

    async def disconnect_all(self):
        """Disconnect from all relays"""
        self._running = False
        for url, ws in self.connections.items():
            try:
                await ws.close()
                logger.info(f"Disconnected from {url}")
            except Exception as e:
                logger.error(f"Error disconnecting from {url}: {e}")
        self.connections.clear()