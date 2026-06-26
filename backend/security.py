"""
Shared security helpers: client IP resolution, chat moderation, Redis rate limiting.
"""
from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request

from ai_chat import (
    OFFENSIVE_LANGUAGE_MESSAGE,
    _contains_offensive_language,
    _detect_prompt_language_ai,
    _get_decline_message,
    _is_offensive_any_language_ai,
    _is_weather_related_any_language_ai,
)

logger = logging.getLogger(__name__)

RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 8
RATE_LIMIT_REDIS_PREFIX = "rate_limit"

_memory_rate_limit_store: dict[str, deque[float]] = defaultdict(deque)
_memory_rate_limit_lock = threading.Lock()


def is_trusted_proxy() -> bool:
    """Honor X-Forwarded-For only when explicitly enabled (reverse proxy in front)."""
    return os.getenv("TRUSTED_PROXY", "").strip().lower() in ("1", "true", "yes")


def get_client_ip(request: Request) -> str:
    """
    Resolve the client IP for rate limiting and session fallback.

    When TRUSTED_PROXY is false (default), use the direct socket peer only.
    """
    if is_trusted_proxy():
        xff = request.headers.get("x-forwarded-for", "")
        if xff:
            return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_allowed_origins() -> list[str]:
    """Parse ALLOWED_ORIGINS (comma-separated). Defaults to local dev frontend."""
    raw = os.getenv("ALLOWED_ORIGINS", "").strip()
    if not raw:
        return ["http://localhost:3000"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


# Vercel preview/production deploys (*.vercel.app). Override via CORS_ORIGIN_REGEX.
DEFAULT_CORS_ORIGIN_REGEX = r"https://.*\.vercel\.app"


def get_cors_origin_regex() -> str | None:
    """Optional regex for dynamic browser origins (e.g. Vercel preview URLs)."""
    raw = os.getenv("CORS_ORIGIN_REGEX", DEFAULT_CORS_ORIGIN_REGEX).strip()
    return raw or None


def _rate_limit_redis_key(endpoint_key: str, client_ip: str) -> str:
    return f"{RATE_LIMIT_REDIS_PREFIX}:{endpoint_key}:{client_ip}"


def _enforce_rate_limit_redis(redis_client: Any, redis_key: str) -> None:
    """Sliding-window counter in a Redis sorted set (scores = request timestamps)."""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    member = f"{now}:{uuid.uuid4().hex}"

    pipe = redis_client.pipeline()
    pipe.zremrangebyscore(redis_key, 0, window_start)
    pipe.zcard(redis_key)
    results = pipe.execute()
    current_count = int(results[1])

    if current_count >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a minute and try again.",
        )

    pipe = redis_client.pipeline()
    pipe.zadd(redis_key, {member: now})
    pipe.expire(redis_key, RATE_LIMIT_WINDOW_SECONDS + 5)
    pipe.execute()


def _enforce_rate_limit_memory(redis_key: str) -> None:
    """In-process fallback when Redis is unavailable (dev / degraded mode)."""
    now = time.time()
    with _memory_rate_limit_lock:
        bucket = _memory_rate_limit_store[redis_key]
        while bucket and now - bucket[0] > RATE_LIMIT_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please wait a minute and try again.",
            )
        bucket.append(now)


async def enforce_rate_limit(request: Request, endpoint_key: str, redis_client: Any | None) -> None:
    """
    Per-IP sliding-window rate limit keyed as ``rate_limit:{endpoint}:{ip}``.

    Uses Redis when available; falls back to in-memory storage otherwise.
    """
    from logging_config import log_redis_event

    client_ip = get_client_ip(request)
    redis_key = _rate_limit_redis_key(endpoint_key, client_ip)

    if redis_client is not None:
        try:
            await asyncio.to_thread(_enforce_rate_limit_redis, redis_client, redis_key)
            return
        except Exception as exc:
            log_redis_event(
                "rate_limit_redis_failed",
                component="security.enforce_rate_limit",
                fallback="in_memory",
                error=str(exc),
            )

    log_redis_event(
        "rate_limit_fallback",
        component="security.enforce_rate_limit",
        fallback="in_memory",
        level="info",
    )
    await asyncio.to_thread(_enforce_rate_limit_memory, redis_key)


def clear_memory_rate_limits() -> None:
    """Test helper: reset in-process rate-limit buckets."""
    with _memory_rate_limit_lock:
        _memory_rate_limit_store.clear()


@dataclass(frozen=True)
class ChatSafetyVerdict:
    allowed: bool
    message: str = ""


async def evaluate_chat_input_safety(user_text: str, language: str = "en") -> ChatSafetyVerdict:
    """
    Legacy moderation gates for the LangChain SSE chat path.

    Blocks offensive content (regex + Gemini classifier) and off-topic prompts
    before any agent / tool invocation.
    """
    cleaned = (user_text or "").strip()
    if not cleaned:
        return ChatSafetyVerdict(allowed=False, message=_get_decline_message(language))

    if _contains_offensive_language(cleaned) or await asyncio.to_thread(
        _is_offensive_any_language_ai, cleaned
    ):
        return ChatSafetyVerdict(allowed=False, message=OFFENSIVE_LANGUAGE_MESSAGE)

    prompt_language = await asyncio.to_thread(
        _detect_prompt_language_ai, cleaned, fallback_language=language
    )
    is_weather = await asyncio.to_thread(
        _is_weather_related_any_language_ai, cleaned, prompt_language
    )
    if not is_weather:
        return ChatSafetyVerdict(
            allowed=False,
            message=_get_decline_message(prompt_language),
        )

    return ChatSafetyVerdict(allowed=True)
