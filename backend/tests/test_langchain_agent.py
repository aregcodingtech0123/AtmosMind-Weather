"""Tests for AtmosMindAgent (mocked LLM — no Gemini API calls)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from langchain_agent import AtmosMindAgent
from langchain_memory import (
    ChatMemoryConfig,
    create_windowed_memory,
    get_windowed_history_messages,
)


@pytest.mark.asyncio
async def test_agent_persists_turn_to_memory():
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock(
        return_value=AIMessage(content="**Forecast**\n\nExpect mild temperatures in Berlin.")
    )

    session_id = "test-session-12345678"
    memory = create_windowed_memory(
        ChatMemoryConfig(session_id=session_id, window_k=5),
        use_redis=False,
    )

    agent = AtmosMindAgent(mock_llm, use_redis=False, window_k=5)
    with patch.object(agent, "_build_memory", return_value=memory):
        reply = await agent.ainvoke(
            session_id=session_id,
            user_input="What is the weather in Berlin tomorrow?",
            language="en",
            unit="metric",
        )

    assert "Berlin" in reply
    mock_llm.ainvoke.assert_awaited()

    history = get_windowed_history_messages(memory)
    assert len(history) == 2
    assert history[0].content == "What is the weather in Berlin tomorrow?"
    assert "Berlin" in history[1].content


@pytest.mark.asyncio
async def test_agent_rejects_empty_user_input():
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Should not be called."))

    agent = AtmosMindAgent(mock_llm, use_redis=False)
    reply = await agent.ainvoke(
        session_id="test-session-12345678",
        user_input="   ",
        language="en",
        unit="metric",
    )

    assert reply == "Please send a message to start the conversation."
    mock_llm.ainvoke.assert_not_awaited()
