"""Shared pytest fixtures for the AtmosMind FastAPI backend."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import api
from security import ChatSafetyVerdict, clear_memory_rate_limits


@pytest.fixture(autouse=True)
def _clear_rate_limit_store():
    """Isolate rate-limit state between tests."""
    clear_memory_rate_limits()
    yield
    clear_memory_rate_limits()


@pytest.fixture(autouse=True)
def _allow_chat_input_by_default(monkeypatch):
    """Skip live Gemini moderation in tests unless a case overrides it."""

    async def _allow(_user_text: str, _language: str = "en") -> ChatSafetyVerdict:
        return ChatSafetyVerdict(allowed=True)

    monkeypatch.setattr(api, "evaluate_chat_input_safety", _allow)


@pytest.fixture
def client(monkeypatch):
    """Test client with infrastructure startup stubbed out."""
    monkeypatch.setattr(api, "_get_redis", lambda: None)
    monkeypatch.setattr(api, "fetch_popular_for_redis", lambda conn, limit=1000: [])
    monkeypatch.setattr(api, "init_schema", lambda conn: None)
    mock_conn = MagicMock()
    monkeypatch.setattr(api, "get_connection", lambda: mock_conn)
    with TestClient(api.app) as test_client:
        yield test_client
