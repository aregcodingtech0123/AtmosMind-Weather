"""
Redis-backed conversational memory for the AtmosMind LangChain agent.

Uses ``RedisChatMessageHistory`` for durable per-session storage and enforces a
sliding window (``ConversationBufferWindowMemory``-style, k=5–10) so Redis and
Gemini prompts never grow without bound.

Environment variables
---------------------
REDIS_URL                  Redis connection string (same as autocomplete cache)
CHAT_MEMORY_WINDOW_K       Messages to retain per session (default 10, clamped 5–10)
CHAT_SESSION_TTL_SECONDS   Redis TTL for idle sessions (default 86400 = 24 h)
"""
from __future__ import annotations

import logging
import os
import re
from typing import Sequence

from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_classic.memory import ConversationBufferWindowMemory
from pydantic import BaseModel, Field, field_validator

from logging_config import log_redis_event

logger = logging.getLogger(__name__)

CHAT_KEY_PREFIX = "atmosmind:chat:"
DEFAULT_WINDOW_K = 10
MIN_WINDOW_K = 5
MAX_WINDOW_K = 10
DEFAULT_SESSION_TTL = 86_400  # 24 hours


def get_chat_redis_url() -> str:
    """Resolve Redis URL from environment (shared with ``api._get_redis``)."""
    return os.getenv("REDIS_URL", "redis://localhost:6379/0").strip()


def _clamp_window_k(value: int) -> int:
    return max(MIN_WINDOW_K, min(MAX_WINDOW_K, int(value)))


def resolve_window_k(override: int | None = None) -> int:
    """Window size from override, env, or default — always clamped to [5, 10]."""
    if override is not None:
        return _clamp_window_k(override)
    raw = os.getenv("CHAT_MEMORY_WINDOW_K", str(DEFAULT_WINDOW_K))
    try:
        return _clamp_window_k(int(raw))
    except (TypeError, ValueError):
        return DEFAULT_WINDOW_K


def resolve_session_ttl(override: int | None = None) -> int | None:
    """Optional Redis TTL (seconds) for chat session keys."""
    if override is not None:
        return max(60, int(override))
    raw = os.getenv("CHAT_SESSION_TTL_SECONDS", str(DEFAULT_SESSION_TTL)).strip()
    if not raw:
        return DEFAULT_SESSION_TTL
    try:
        return max(60, int(raw))
    except (TypeError, ValueError):
        return DEFAULT_SESSION_TTL


_SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9._:-]{8,128}$")


def sanitize_session_id(session_id: str) -> str:
    """
    Validate client-supplied session identifiers before using them as Redis keys.
    Accepts UUIDs, device tokens, or hashed user ids.
    """
    cleaned = (session_id or "").strip()
    if not _SESSION_ID_PATTERN.fullmatch(cleaned):
        raise ValueError(
            "session_id must be 8–128 characters of letters, digits, '.', '_', ':', or '-'."
        )
    return cleaned


def trim_messages(messages: Sequence[BaseMessage], k: int) -> list[BaseMessage]:
    """Keep only the last *k* messages (sliding window)."""
    if k <= 0:
        return []
    seq = list(messages)
    return seq[-k:] if len(seq) > k else seq


class WindowedRedisChatMessageHistory(RedisChatMessageHistory):
    """
    ``RedisChatMessageHistory`` that **physically** trims Redis after every write.

    Without trimming, ``ConversationBufferWindowMemory`` only limits what the LLM
    sees while Redis still stores the full transcript. This subclass caps storage
    and token-bound context at the same ``k``.
    """

    def __init__(
        self,
        session_id: str,
        url: str,
        *,
        k: int = DEFAULT_WINDOW_K,
        key_prefix: str = CHAT_KEY_PREFIX,
        ttl: int | None = DEFAULT_SESSION_TTL,
    ) -> None:
        super().__init__(
            session_id=session_id,
            url=url,
            key_prefix=key_prefix,
            ttl=ttl,
        )
        object.__setattr__(self, "_window_k", _clamp_window_k(k))

    @property
    def k(self) -> int:
        return self._window_k

    def add_message(self, message: BaseMessage) -> None:
        super().add_message(message)
        self._enforce_window()

    def add_user_message(self, message: str) -> None:
        super().add_user_message(message)
        self._enforce_window()

    def add_ai_message(self, message: str) -> None:
        super().add_ai_message(message)
        self._enforce_window()

    def _enforce_window(self) -> None:
        messages = list(self.messages)
        trimmed = trim_messages(messages, self._window_k)
        if len(trimmed) < len(messages):
            self.clear()
            for msg in trimmed:
                super().add_message(msg)


class WindowedInMemoryChatMessageHistory(BaseChatMessageHistory):
    """In-memory fallback when Redis is unavailable (same sliding window semantics)."""

    def __init__(self, k: int = DEFAULT_WINDOW_K) -> None:
        self._window_k = _clamp_window_k(k)
        self._store = InMemoryChatMessageHistory()

    @property
    def messages(self) -> list[BaseMessage]:
        return self._store.messages

    def add_message(self, message: BaseMessage) -> None:
        self._store.add_message(message)
        self._enforce_window()

    def clear(self) -> None:
        self._store.clear()

    def _enforce_window(self) -> None:
        trimmed = trim_messages(self._store.messages, self._window_k)
        if len(trimmed) < len(self._store.messages):
            self._store.clear()
            for msg in trimmed:
                self._store.add_message(msg)


class ChatMemoryConfig(BaseModel):
    """Configuration for a single chat session's Redis-backed memory."""

    session_id: str = Field(..., min_length=8, max_length=128)
    window_k: int = Field(default=DEFAULT_WINDOW_K, ge=MIN_WINDOW_K, le=MAX_WINDOW_K)
    session_ttl_seconds: int | None = Field(default=DEFAULT_SESSION_TTL, ge=60)

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        return sanitize_session_id(value)


def create_chat_message_history(
    config: ChatMemoryConfig,
    *,
    redis_url: str | None = None,
    use_redis: bool = True,
) -> BaseChatMessageHistory:
    """
    Factory: prefer Redis; fall back to in-memory windowed history if Redis is down.
    """
    if use_redis:
        try:
            return WindowedRedisChatMessageHistory(
                session_id=config.session_id,
                url=redis_url or get_chat_redis_url(),
                k=config.window_k,
                ttl=config.session_ttl_seconds,
            )
        except Exception as exc:
            log_redis_event(
                "chat_history_unavailable",
                component="langchain_memory",
                fallback="in_memory",
                error=str(exc),
            )
    return WindowedInMemoryChatMessageHistory(k=config.window_k)


def create_windowed_memory(
    config: ChatMemoryConfig,
    *,
    redis_url: str | None = None,
    use_redis: bool = True,
) -> ConversationBufferWindowMemory:
    """
    Build ``ConversationBufferWindowMemory`` backed by windowed Redis storage.

    ``k`` controls both:
      - messages sent to Gemini (via ``load_memory_variables``)
      - messages persisted in Redis (via ``WindowedRedisChatMessageHistory``)
    """
    chat_history = create_chat_message_history(config, redis_url=redis_url, use_redis=use_redis)
    return ConversationBufferWindowMemory(
        chat_memory=chat_history,
        k=config.window_k,
        return_messages=True,
        memory_key="history",
        input_key="input",
        output_key="output",
    )


def get_windowed_history_messages(memory: ConversationBufferWindowMemory) -> list[BaseMessage]:
    """Return the last *k* messages for prompt construction."""
    variables = memory.load_memory_variables({})
    history = variables.get("history") or []
    return list(history)


def append_exchange(
    memory: ConversationBufferWindowMemory,
    user_text: str,
    assistant_text: str,
) -> None:
    """Persist a completed user/assistant turn into Redis (window enforced)."""
    memory.chat_memory.add_message(HumanMessage(content=user_text))
    memory.chat_memory.add_message(AIMessage(content=assistant_text))


def clear_session_memory(memory: ConversationBufferWindowMemory) -> None:
    """Delete all messages for the session (Redis key cleared)."""
    memory.chat_memory.clear()
