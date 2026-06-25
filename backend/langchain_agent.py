"""
AtmosMind LangChain agent — prompt + tools + Redis windowed memory.

Usage::

    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_agent import AtmosMindAgent, create_atmosmind_agent

    agent = create_atmosmind_agent()  # reads GOOGLE_API_KEY from env
    reply = await agent.ainvoke(
        session_id="device-uuid-or-user-token",
        user_input="What's the weather in Paris tomorrow?",
        language="en",
        unit="metric",
    )

Streaming (SSE)::

    async for token in agent.astream(session_id="...", user_input="...", language="en"):
        print(token, end="", flush=True)
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_memory import (
    ChatMemoryConfig,
    append_exchange,
    create_windowed_memory,
    get_windowed_history_messages,
    resolve_session_ttl,
    resolve_window_k,
    sanitize_session_id,
)
from langchain_prompts import (
    AgentPromptSettings,
    build_prompted_messages,
    inject_location_context,
    normalize_agent_settings,
)
from langchain_tools import get_atmosmind_tools
from gemini_client import require_google_api_key
from logging_config import log_gemini_error
from observability import configure_langsmith_tracing

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5


def _message_text(message: AIMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "".join(parts).strip()
    return str(content or "").strip()


def _chunk_text(chunk: AIMessage) -> str:
    content = getattr(chunk, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "".join(parts)
    return ""


class AtmosMindAgent:
    """
    Weather assistant agent with:
      - Dynamic ``ChatPromptTemplate`` (language + unit injection)
      - Async coordinate-first LangChain tools
      - Redis ``ConversationBufferWindowMemory`` (sliding window k=5–10)
      - Token streaming for the final user-facing reply
    """

    def __init__(
        self,
        llm,
        *,
        window_k: int | None = None,
        session_ttl_seconds: int | None = None,
        use_redis: bool = True,
    ) -> None:
        self._llm = llm.bind_tools(get_atmosmind_tools())
        self._tools = {tool.name: tool for tool in get_atmosmind_tools()}
        self._window_k = resolve_window_k(window_k)
        self._session_ttl = resolve_session_ttl(session_ttl_seconds)
        self._use_redis = use_redis

    def _build_memory(self, session_id: str) -> Any:
        config = ChatMemoryConfig(
            session_id=session_id,
            window_k=self._window_k,
            session_ttl_seconds=self._session_ttl,
        )
        return create_windowed_memory(config, use_redis=self._use_redis)

    async def _execute_tool(self, tool_name: str, tool_args: dict[str, Any]) -> str:
        tool = self._tools.get(tool_name)
        if tool is None:
            return f'{{"error": "Unknown tool: {tool_name}"}}'
        try:
            result = await tool.ainvoke(tool_args)
            if isinstance(result, dict):
                import json

                return json.dumps(result, ensure_ascii=False)
            return str(result)
        except Exception as exc:
            logger.exception("Tool %s failed: %s", tool_name, exc)
            return f'{{"error": "Tool execution failed: {exc}"}}'

    async def _stream_final_reply(self, conversation: list) -> AsyncIterator[str]:
        """Stream only the final natural-language answer (no tool-call chunks)."""
        async for event in self._llm.astream_events(conversation, version="v2"):
            if event.get("event") != "on_chat_model_stream":
                continue
            chunk = event.get("data", {}).get("chunk")
            if chunk is None:
                continue
            if getattr(chunk, "tool_call_chunks", None):
                continue
            text = _chunk_text(chunk)
            if text:
                yield text

    async def _run_with_tools(
        self,
        messages: list,
    ) -> AIMessage:
        """Tool-calling loop (async) until the model returns a final text reply."""
        conversation = list(messages)

        for _ in range(MAX_TOOL_ROUNDS):
            response: AIMessage = await self._llm.ainvoke(conversation)
            tool_calls = getattr(response, "tool_calls", None) or []

            if not tool_calls:
                return response

            conversation.append(response)
            for call in tool_calls:
                name = call.get("name") if isinstance(call, dict) else getattr(call, "name", "")
                args = call.get("args") if isinstance(call, dict) else getattr(call, "args", {})
                call_id = call.get("id") if isinstance(call, dict) else getattr(call, "id", name)
                payload = await self._execute_tool(str(name), dict(args or {}))
                conversation.append(
                    ToolMessage(content=payload, tool_call_id=str(call_id or name), name=str(name))
                )

        return AIMessage(content="Sorry, I could not complete the weather lookup. Please try again.")

    def _prepare_turn(
        self,
        session_id: str,
        user_input: str,
        *,
        language: str,
        unit: str,
        settings: AgentPromptSettings | None,
        city_name: str | None,
        latitude: float | None,
        longitude: float | None,
    ) -> tuple[Any, str, list]:
        session_id = sanitize_session_id(session_id)
        user_input = (user_input or "").strip()
        if not user_input:
            return None, session_id, []

        prompt_settings = settings or normalize_agent_settings(language=language, unit=unit)
        memory = self._build_memory(session_id)

        prior_messages = get_windowed_history_messages(memory)
        user_message = HumanMessage(content=user_input)
        prompted = build_prompted_messages(prompt_settings, [*prior_messages, user_message])
        prompted = inject_location_context(
            prompted,
            city_name=city_name,
            latitude=latitude,
            longitude=longitude,
        )
        return memory, user_input, prompted

    async def astream(
        self,
        session_id: str,
        user_input: str,
        *,
        language: str = "en",
        unit: str = "metric",
        settings: AgentPromptSettings | None = None,
        city_name: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> AsyncIterator[str]:
        """
        Yield user-visible tokens as they are generated.

        Tool-calling rounds run synchronously (``ainvoke``); only the final
        natural-language synthesis is streamed via ``astream_events``.
        """
        memory, cleaned_input, prompted = self._prepare_turn(
            session_id,
            user_input,
            language=language,
            unit=unit,
            settings=settings,
            city_name=city_name,
            latitude=latitude,
            longitude=longitude,
        )
        if memory is None:
            yield "Please send a message to start the conversation."
            return

        conversation = list(prompted)
        reply_parts: list[str] = []

        for _ in range(MAX_TOOL_ROUNDS):
            response = await self._llm.ainvoke(conversation)
            tool_calls = getattr(response, "tool_calls", None) or []

            if tool_calls:
                conversation.append(response)
                for call in tool_calls:
                    name = call.get("name") if isinstance(call, dict) else getattr(call, "name", "")
                    args = call.get("args") if isinstance(call, dict) else getattr(call, "args", {})
                    call_id = call.get("id") if isinstance(call, dict) else getattr(call, "id", name)
                    payload = await self._execute_tool(str(name), dict(args or {}))
                    conversation.append(
                        ToolMessage(content=payload, tool_call_id=str(call_id or name), name=str(name))
                    )
                continue

            text = _message_text(response)
            if text:
                import asyncio
                # Artificial stream to provide smooth UI experience
                words = text.split(" ")
                for i, word in enumerate(words):
                    token = word + (" " if i < len(words) - 1 else "")
                    reply_parts.append(token)
                    yield token
                    await asyncio.sleep(0.03)
            break
        else:
            msg = "I'm sorry, I could not complete the request in time."
            reply_parts.append(msg)
            yield msg

        reply_text = "".join(reply_parts).strip() or "Sorry, something went wrong."
        append_exchange(memory, cleaned_input, reply_text)

    async def ainvoke(
        self,
        session_id: str,
        user_input: str,
        *,
        language: str = "en",
        unit: str = "metric",
        settings: AgentPromptSettings | None = None,
        city_name: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> str:
        """Collect the full streamed reply (used by tests and non-SSE callers)."""
        parts: list[str] = []
        async for token in self.astream(
            session_id,
            user_input,
            language=language,
            unit=unit,
            settings=settings,
            city_name=city_name,
            latitude=latitude,
            longitude=longitude,
        ):
            parts.append(token)
        return "".join(parts).strip() or "Sorry, something went wrong."


def create_atmosmind_agent(
    *,
    model: str = "gemini-2.5-flash",
    window_k: int | None = None,
    session_ttl_seconds: int | None = None,
    use_redis: bool = True,
) -> AtmosMindAgent:
    """
    Factory: build ``AtmosMindAgent`` with ``ChatGoogleGenerativeAI`` (google-genai SDK).

    Requires ``langchain-google-genai``, ``google-genai``, and ``GOOGLE_API_KEY``.
    """
    configure_langsmith_tracing()
    api_key = require_google_api_key()
    try:
        llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=0.2,
            timeout=20,
            max_retries=1,
        )
    except Exception as exc:
        log_gemini_error("ChatGoogleGenerativeAI.init", exc, model=model)
        logger.error("Failed to initialize ChatGoogleGenerativeAI: %s", exc, exc_info=True)
        raise RuntimeError(
            "ChatGoogleGenerativeAI could not be initialized. "
            "Verify GOOGLE_API_KEY and install: pip install google-genai langchain-google-genai"
        ) from exc

    return AtmosMindAgent(
        llm,
        window_k=window_k,
        session_ttl_seconds=session_ttl_seconds,
        use_redis=use_redis,
    )
