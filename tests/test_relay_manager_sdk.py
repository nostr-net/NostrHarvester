import os
import sys
import pytest

# Ensure project root is on path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from indexer.relay_manager import RelayManager
except ImportError:
    pytest.skip(
        "Skipping RelayManager tests: nostr_sdk dependency not installed",
        allow_module_level=True,
    )


class DummyConfig:
    def get_relays(self):
        return []


class DummyProcessor:
    async def process_event(self, *args, **kwargs):
        pass


def test_relay_manager_init_and_disconnect():
    manager = RelayManager(DummyConfig(), DummyProcessor())
    # Should have connect_all and disconnect_all methods
    assert hasattr(manager, "connect_all"), "RelayManager missing connect_all method"
    assert hasattr(manager, "disconnect_all"), "RelayManager missing disconnect_all method"