import json
import logging
import os
import sys
import types
import asyncio
import pytest

websockets_stub = types.ModuleType("websockets")
exceptions_module = types.ModuleType("websockets.exceptions")
exceptions_module.WebSocketException = Exception
websockets_stub.exceptions = exceptions_module
sys.modules.setdefault("websockets", websockets_stub)
sys.modules.setdefault("websockets.exceptions", exceptions_module)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from relay_manager import RelayManager

class DummyConfig:
    def get_relays(self):
        return []

class DummyProcessor:
    def __init__(self):
        self.called = False

    async def process_event(self, event, relay_url, response_time_ms=None):
        self.called = True

def test_handle_message_short_message(caplog):
    manager = RelayManager(DummyConfig(), DummyProcessor())
    msg = json.dumps(["EVENT", "subid"])  # missing event payload
    with caplog.at_level(logging.ERROR, logger="relay_manager"):
        asyncio.run(manager.handle_message(msg, "relay.test"))
    assert "Unexpected message format" in caplog.text
    assert not manager.event_processor.called

