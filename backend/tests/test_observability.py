"""Tests for LangSmith observability bootstrap."""
from __future__ import annotations

import os

import observability
from observability import configure_langsmith_tracing, langsmith_tracing_active


def _reset_observability_state() -> None:
    observability._TRACING_CONFIGURED = False


def test_configure_langsmith_disabled_without_env(monkeypatch):
    _reset_observability_state()
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)

    assert configure_langsmith_tracing() is False
    assert os.getenv("LANGCHAIN_PROJECT") == "atmosmind-agent"
    assert langsmith_tracing_active() is False


def test_configure_langsmith_enabled_with_env(monkeypatch):
    _reset_observability_state()
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setenv("LANGCHAIN_API_KEY", "test-key")
    monkeypatch.setenv("LANGCHAIN_PROJECT", "atmosmind-agent")

    assert configure_langsmith_tracing() is True
    assert langsmith_tracing_active() is True
