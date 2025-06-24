import os
import sys
import pytest

# Ensure project root is on path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.config import Settings
from pydantic.v1 import ValidationError


def test_api_auth_token_required_when_enabled(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
    with pytest.raises(ValidationError):
        Settings()
    monkeypatch.setenv("API_AUTH_ENABLED", "false")
