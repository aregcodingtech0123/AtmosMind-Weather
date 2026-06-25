"""Tests for AtmosMind LangChain prompt template."""
from langchain_core.messages import HumanMessage

from langchain_prompts import (
    ATMOSMIND_AGENT_PROMPT,
    build_prompted_messages,
    normalize_agent_settings,
    preview_system_message,
)


def test_prompt_template_exposes_dynamic_variables():
    partial = ATMOSMIND_AGENT_PROMPT.partial(language="tr", unit_preference="Metric test")
    assert "language" in ATMOSMIND_AGENT_PROMPT.input_variables
    assert "unit_preference" in ATMOSMIND_AGENT_PROMPT.input_variables
    assert "messages" in ATMOSMIND_AGENT_PROMPT.input_variables
    assert partial is not None


def test_build_prompted_messages_injects_language_and_unit():
    settings = normalize_agent_settings(language="tr", unit="imperial")
    messages = build_prompted_messages(
        settings,
        chat_history=[HumanMessage(content="Berlin'de hava nasıl?")],
    )
    system_text = str(messages[0].content)
    assert "`tr`" in system_text or "tr" in system_text
    assert "Fahrenheit" in system_text
    assert messages[-1].content == "Berlin'de hava nasıl?"


def test_preview_system_message_metric_celsius():
    text = preview_system_message(language="en", unit="metric")
    assert "AtmosMind" in text
    assert "Celsius" in text
    assert "weather" in text.casefold()


def test_decline_template_localized_for_turkish():
    """PR-04: Turkish UI locale embeds a Turkish off-topic decline template."""
    from langchain_prompts import decline_template_for_language

    decline = decline_template_for_language("tr")
    text = preview_system_message(language="tr", unit="metric")

    assert "hava" in decline.casefold()
    assert decline in text
