"""Unit tests for security helpers (rate limit, CORS origins, chat moderation)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

import security
from security import ChatSafetyVerdict, clear_memory_rate_limits, get_allowed_origins


def test_get_allowed_origins_defaults_to_localhost():
    with patch.dict("os.environ", {"ALLOWED_ORIGINS": ""}, clear=False):
        assert get_allowed_origins() == ["http://localhost:3000"]


def test_get_allowed_origins_parses_comma_list():
    with patch.dict(
        "os.environ",
        {"ALLOWED_ORIGINS": "https://a.example.com, http://localhost:3000"},
        clear=False,
    ):
        assert get_allowed_origins() == ["https://a.example.com", "http://localhost:3000"]


@pytest.mark.asyncio
async def test_enforce_rate_limit_memory_blocks_after_max():
    clear_memory_rate_limits()
    request = MagicMock()
    request.headers = {}
    request.client = MagicMock(host="203.0.113.10")

    with patch.object(security, "RATE_LIMIT_MAX_REQUESTS", 2):
        await security.enforce_rate_limit(request, "chat", None)
        await security.enforce_rate_limit(request, "chat", None)
        with pytest.raises(HTTPException) as exc_info:
            await security.enforce_rate_limit(request, "chat", None)
        assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_evaluate_chat_input_safety_blocks_offensive_regex():
    with patch.object(security, "_contains_offensive_language", return_value=True):
        verdict = await security.evaluate_chat_input_safety("bad word", "en")
    assert verdict == ChatSafetyVerdict(allowed=False, message=security.OFFENSIVE_LANGUAGE_MESSAGE)
