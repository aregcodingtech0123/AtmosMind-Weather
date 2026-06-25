"""Tests for Redis-backed windowed chat memory."""
from unittest.mock import patch

from langchain_core.messages import HumanMessage
from langchain_classic.memory import ConversationBufferWindowMemory

from langchain_memory import (
    WindowedInMemoryChatMessageHistory,
    append_exchange,
    create_windowed_memory,
    get_windowed_history_messages,
    resolve_window_k,
    sanitize_session_id,
    trim_messages,
    ChatMemoryConfig,
)


def test_trim_messages_sliding_window():
    msgs = [HumanMessage(content=f"m{i}") for i in range(12)]
    trimmed = trim_messages(msgs, k=5)
    assert len(trimmed) == 5
    assert trimmed[0].content == "m7"
    assert trimmed[-1].content == "m11"


def test_resolve_window_k_clamped_to_five_through_ten():
    assert resolve_window_k(3) == 5
    assert resolve_window_k(99) == 10
    assert resolve_window_k(7) == 7


def test_windowed_in_memory_history_never_exceeds_k():
    history = WindowedInMemoryChatMessageHistory(k=5)
    for i in range(12):
        history.add_message(HumanMessage(content=f"u{i}"))
    assert len(history.messages) == 5
    assert history.messages[0].content == "u7"


def test_conversation_buffer_window_memory_returns_last_k():
    config = ChatMemoryConfig(session_id="test-session-001", window_k=5)
    memory = create_windowed_memory(config, use_redis=False)

    for i in range(8):
        append_exchange(memory, f"user-{i}", f"assistant-{i}")

    history = get_windowed_history_messages(memory)
    assert len(history) == 5
    assert history[0].content == "assistant-5"
    assert history[-1].content == "assistant-7"


def test_sanitize_session_id_accepts_uuid_like_tokens():
    token = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert sanitize_session_id(token) == token


def test_conversation_buffer_window_memory_type():
    config = ChatMemoryConfig(session_id="test-session-002", window_k=6)
    memory = create_windowed_memory(config, use_redis=False)
    assert isinstance(memory, ConversationBufferWindowMemory)
    assert memory.k == 6


@patch("langchain_memory.WindowedRedisChatMessageHistory")
def test_create_windowed_memory_uses_redis_when_available(MockHistory):
    """MEM-05: Redis-backed history is constructed when use_redis=True."""
    mock_store = WindowedInMemoryChatMessageHistory(k=8)
    MockHistory.return_value = mock_store

    config = ChatMemoryConfig(session_id="test-session-abc12345", window_k=8)
    memory = create_windowed_memory(config, use_redis=True)

    MockHistory.assert_called_once()
    call_kwargs = MockHistory.call_args.kwargs
    assert call_kwargs["session_id"] == "test-session-abc12345"
    assert call_kwargs["k"] == 8
    assert isinstance(memory, ConversationBufferWindowMemory)
    assert memory.chat_memory is mock_store
