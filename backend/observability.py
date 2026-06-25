"""
LangSmith / LangChain observability bootstrap.

Tracing is enabled automatically when standard LangChain environment variables are set.
No secrets are hardcoded — only defaults for optional project name.
"""
from __future__ import annotations

import os

from loguru import logger

DEFAULT_LANGCHAIN_PROJECT = "atmosmind-agent"
_TRACING_CONFIGURED = False


def _is_truthy(value: str) -> bool:
    return value.strip().casefold() in {"true", "1", "yes", "on"}


def configure_langsmith_tracing() -> bool:
    """
    Prepare LangSmith tracing for LangChain agent runs.

    LangChain reads these environment variables at runtime:
      - LANGCHAIN_TRACING_V2=true
      - LANGCHAIN_API_KEY=<your-key>
      - LANGCHAIN_PROJECT=atmosmind-agent (default applied if unset)

    Returns True when tracing is expected to be active.
    """
    global _TRACING_CONFIGURED

    if not os.getenv("LANGCHAIN_PROJECT", "").strip():
        os.environ["LANGCHAIN_PROJECT"] = DEFAULT_LANGCHAIN_PROJECT

    tracing_enabled = _is_truthy(os.getenv("LANGCHAIN_TRACING_V2", ""))
    api_key_present = bool(os.getenv("LANGCHAIN_API_KEY", "").strip())
    project = os.getenv("LANGCHAIN_PROJECT", DEFAULT_LANGCHAIN_PROJECT).strip()

    if tracing_enabled and api_key_present:
        if not _TRACING_CONFIGURED:
            logger.bind(
                event="langsmith",
                project=project,
                tracing_v2=True,
            ).info("LangSmith tracing enabled for LangChain agent runs")
            _TRACING_CONFIGURED = True
        return True

    if not _TRACING_CONFIGURED:
        logger.bind(
            event="langsmith",
            tracing_v2=tracing_enabled,
            api_key_present=api_key_present,
        ).info(
            "LangSmith tracing disabled — set LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY to enable"
        )
        _TRACING_CONFIGURED = True
    return False


def langsmith_tracing_active() -> bool:
    """Return whether LangSmith tracing should be active for the current process."""
    return _is_truthy(os.getenv("LANGCHAIN_TRACING_V2", "")) and bool(
        os.getenv("LANGCHAIN_API_KEY", "").strip()
    )
