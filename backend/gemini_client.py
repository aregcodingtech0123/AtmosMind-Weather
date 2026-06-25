"""
Shared Google GenAI SDK (``google-genai``) + LangChain Gemini factory.

Replaces the deprecated ``google-generativeai`` package across AtmosMind.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from google import genai
from google.genai import types

from logging_config import log_gemini_error

if TYPE_CHECKING:
    from langchain_google_genai import ChatGoogleGenerativeAI

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


def require_google_api_key() -> str:
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Add it to your environment or backend/.env file."
        )
    return api_key


@lru_cache(maxsize=1)
def get_genai_client() -> genai.Client:
    """Singleton ``google.genai.Client`` for the legacy REST chat/advice paths."""
    return genai.Client(api_key=require_google_api_key())


def generate_text(
    prompt: str,
    *,
    model: str = DEFAULT_GEMINI_MODEL,
    system_instruction: str | None = None,
) -> str:
    """Single-turn text generation via the modern Google GenAI SDK."""
    config: types.GenerateContentConfig | None = None
    if system_instruction:
        config = types.GenerateContentConfig(system_instruction=system_instruction)

    try:
        response = get_genai_client().models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )
    except Exception as exc:
        log_gemini_error("generate_text", exc, model=model)
        raise
    return (response.text or "").strip()


def create_gemini_chat_model(
    *,
    model: str = DEFAULT_GEMINI_MODEL,
    temperature: float = 0.2,
) -> ChatGoogleGenerativeAI:
    """
    Build a LangChain ``ChatGoogleGenerativeAI`` backed by ``google-genai``.

    Raises ``RuntimeError`` with actionable install/config hints on failure.
    """
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError as exc:
        raise RuntimeError(
            "langchain-google-genai is not installed. "
            "Run: pip install -r backend/requirements.txt"
        ) from exc

    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=require_google_api_key(),
        temperature=temperature,
    )


def schema_dict_to_function_declaration(tool: dict[str, Any]) -> types.FunctionDeclaration:
    """Convert legacy Gemini function schemas to ``google.genai`` declarations."""
    params = tool.get("parameters") or {}
    properties: dict[str, Any] = {}
    for key, prop in (params.get("properties") or {}).items():
        properties[key] = {
            "type": str(prop.get("type", "STRING")).lower(),
            "description": prop.get("description", ""),
        }

    json_schema = {
        "type": str(params.get("type", "OBJECT")).lower(),
        "properties": properties,
        "required": params.get("required", []),
    }

    return types.FunctionDeclaration(
        name=tool["name"],
        description=tool.get("description", ""),
        parameters_json_schema=json_schema,
    )
