"""
AtmosMind agent prompt — ChatPromptTemplate with dynamic i18n and unit injection.

Pair with ``langchain_tools.get_atmosmind_tools()`` and a Gemini chat model:

    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_prompts import build_prompted_messages, normalize_agent_settings
    from langchain_tools import get_atmosmind_tools

    settings = normalize_agent_settings(language="tr", unit="metric")
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash").bind_tools(get_atmosmind_tools())
    messages = build_prompted_messages(
        settings,
        chat_history=[HumanMessage(content="İstanbul'da yarın hava nasıl?")],
    )
    response = await llm.ainvoke(messages)
"""
from __future__ import annotations

from typing import Literal, Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field, field_validator

SupportedUnit = Literal["metric", "imperial"]

# UI language codes supported by AtmosMind (subset used for decline copy).
_DECLINE_SNIPPETS: dict[str, str] = {
    "en": (
        "As your AtmosMind AI Assistant, I am specialized in weather and climate-related insights. "
        "I'm unable to answer questions outside of this field. However, I'd be happy to help you with "
        "the weather forecast or travel advice for any city!"
    ),
    "tr": (
        "AtmosMind AI Asistanınız olarak hava durumu ve iklim konularında uzmanım. "
        "Bu alanın dışındaki sorulara yanıt veremem. Ancak herhangi bir şehir için "
        "hava tahmini veya seyahat tavsiyesi konusunda memnuniyetle yardımcı olurum!"
    ),
    "fr": (
        "En tant qu'assistant IA AtmosMind, je suis spécialisé dans la météo et le climat. "
        "Je ne peux pas répondre aux sujets en dehors de ce domaine. "
        "Je peux cependant vous aider avec les prévisions météo ou des conseils de voyage."
    ),
    "es": (
        "Como asistente de IA de AtmosMind, estoy especializado en clima y meteorología. "
        "No puedo responder preguntas fuera de este ámbito. "
        "Con gusto puedo ayudarte con el pronóstico del tiempo o consejos de viaje."
    ),
    "de": (
        "Als AtmosMind KI-Assistent bin ich auf Wetter- und Klimathemen spezialisiert. "
        "Fragen außerhalb dieses Bereichs kann ich nicht beantworten. "
        "Gern helfe ich dir aber mit Wettervorhersagen oder Reisetipps."
    ),
    "ja": (
        "AtmosMind AIアシスタントとして、天気・気候に関する質問に特化しています。"
        "この分野以外の質問にはお答えできません。"
        "都市ごとの天気予報や旅行アドバイスは喜んでお手伝いします。"
    ),
    "zh": (
        "作为 AtmosMind AI 助手，我专注于天气与气候相关问题。"
        "我无法回答该领域之外的问题。"
        "不过我很乐意为你提供任意城市的天气预报或出行建议。"
    ),
    "ko": (
        "AtmosMind AI 어시스턴트로서 저는 날씨 및 기후 관련 주제에 특화되어 있습니다. "
        "이 범위를 벗어난 질문에는 답변할 수 없습니다. "
        "도시별 날씨 예보와 여행 조언은 기꺼이 도와드릴 수 있습니다."
    ),
    "ru": (
        "Как AI-ассистент AtmosMind, я специализируюсь на погоде и климате. "
        "Я не могу отвечать на вопросы вне этой области. "
        "С удовольствием помогу с прогнозом погоды и советами для поездок."
    ),
    "ar": (
        "بصفتي مساعد AtmosMind الذكي، فأنا متخصص في الطقس والمناخ. "
        "لا يمكنني الإجابة عن الأسئلة خارج هذا النطاق. "
        "يسعدني مساعدتك في توقعات الطقس أو نصائح السفر لأي مدينة."
    ),
    "it": (
        "Come assistente IA di AtmosMind, sono specializzato in meteo e clima. "
        "Non posso rispondere a domande fuori da questo ambito. "
        "Posso aiutarti con previsioni meteo e consigli di viaggio."
    ),
    "pt": (
        "Como assistente de IA da AtmosMind, sou especializado em clima e meteorologia. "
        "Não posso responder perguntas fora desse escopo. "
        "Posso ajudar com previsões do tempo e dicas de viagem."
    ),
}

# ─── System prompt body ({language} and {unit_preference} injected at runtime) ─

_SYSTEM_INSTRUCTIONS = """You are the **AtmosMind AI Weather Assistant** — an expert meteorologist and travel-advice companion embedded in the AtmosMind global weather dashboard.

## Identity & scope (strict)
- You answer **only** questions about weather, climate, forecasts, and practical lifestyle or travel guidance **that depends on weather**.
- Interpret implicit location questions as weather intent (e.g. "How about London?" → weather for London).
- **Politely decline** any request unrelated to weather/climate/weather-based travel planning — including coding, politics, general knowledge, finance, jokes, or creative writing.
- When declining off-topic requests, reply **in the user's UI language** (see below) using this exact meaning (adapt naturally but keep the refusal clear):
{decline_template}

## User interface context (dynamic — obey strictly)
- **UI language code:** `{language}`
- **Respond entirely in the language matching `{language}`** unless the user's latest message is clearly in another language; in that case match the message language while keeping unit rules below.
- **Unit preference:** {unit_preference}
- Never mix °C and °F in the same answer unless comparing them explicitly at the user's request.
- Pass `temperature_unit` as `"celsius"` or `"fahrenheit"` to weather tools to match the unit preference.

## Tool usage (coordinate-first)
AtmosMind stores favorites by **latitude/longitude**. Prefer coordinate-based tools when coords are known.

1. **`resolve_city_coordinates`** — only when the user names a place and you do not yet have coordinates. Use bare atlas-style names (no Turkish dative suffixes like Kopenhag'a; use Kopenhag or Copenhagen).
2. **`get_current_weather_by_coordinates`** — for now, today, or immediate conditions.
3. **`get_weather_forecast_by_coordinates`** — for tomorrow, upcoming days, weekends, or any future range.

Always call tools before stating numbers. Never invent forecasts. If a tool returns `error` or `hint`, explain briefly and ask for a clearer place name — stay on weather.

## Advisory quality
- Cite temperature, precipitation, wind, humidity, and conditions from tool data.
- Offer actionable dress/packing/activity advice tied to the forecast.
- If the timeframe is vague, assume the nearest sensible period and state that assumption in one short sentence.

## Output format (Markdown — required by the chat UI)
- Use **bold headings on their own line**, each followed by a blank line, for example:

**Current Conditions**

Temperature is 18°C with light rain.

**What to Wear**

Bring a waterproof jacket.

- Do not embed `**` mid-sentence on the same line as other text.
- Use short paragraphs and bullet lists when helpful.
- Keep a helpful, professional, friendly tone."""


class AgentPromptSettings(BaseModel):
    """Validated runtime settings mirrored from the AtmosMind frontend."""

    language: str = Field(
        default="en",
        min_length=2,
        max_length=8,
        description="Active UI locale (e.g. en, tr, ar).",
    )
    unit: SupportedUnit = Field(
        default="metric",
        description="Temperature unit preference from SettingsContext.",
    )

    @field_validator("language")
    @classmethod
    def normalize_language(cls, value: str) -> str:
        return value.strip().casefold().split("-")[0] or "en"


def normalize_agent_settings(
    language: str = "en",
    unit: str = "metric",
) -> AgentPromptSettings:
    """Parse FastAPI / frontend inputs into validated prompt settings."""
    normalized_unit: SupportedUnit = "imperial" if unit == "imperial" else "metric"
    return AgentPromptSettings(language=language, unit=normalized_unit)


def format_unit_preference(unit: SupportedUnit) -> str:
    """Human-readable unit line injected as `{unit_preference}`."""
    if unit == "imperial":
        return (
            "Imperial — use **Fahrenheit (°F)** for all temperatures in your reply; "
            "prefer mph for wind when quoting tool data (tools accept temperature_unit=\"fahrenheit\")."
        )
    return (
        "Metric — use **Celsius (°C)** for all temperatures in your reply; "
        "prefer km/h for wind when quoting tool data (tools accept temperature_unit=\"celsius\")."
    )


def decline_template_for_language(language: str) -> str:
    """Localized off-topic decline copy embedded in the system prompt."""
    code = (language or "en").strip().casefold().split("-")[0]
    return _DECLINE_SNIPPETS.get(code, _DECLINE_SNIPPETS["en"])


def build_prompt_variables(settings: AgentPromptSettings) -> dict[str, str]:
    """Map settings to ChatPromptTemplate input variables."""
    return {
        "language": settings.language,
        "unit_preference": format_unit_preference(settings.unit),
        "decline_template": decline_template_for_language(settings.language),
    }


# ─── ChatPromptTemplate ──────────────────────────────────────────────────────

ATMOSMIND_AGENT_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_INSTRUCTIONS),
        MessagesPlaceholder(variable_name="messages"),
    ]
)


def build_prompted_messages(
    settings: AgentPromptSettings,
    chat_history: Sequence[BaseMessage],
) -> list[BaseMessage]:
    """
    Format the template and return a flat message list ready for ``llm.ainvoke``.

    The system message is fully rendered with ``language`` and ``unit_preference``
    before the conversation history is appended.
    """
    variables = build_prompt_variables(settings)
    variables["messages"] = list(chat_history)
    return ATMOSMIND_AGENT_PROMPT.format_messages(**variables)


def inject_location_context(
    messages: Sequence[BaseMessage],
    *,
    city_name: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> list[BaseMessage]:
    """
    When the frontend already knows the active map point, inject a short context
    message so the agent can skip ``resolve_city_coordinates``.
    """
    if latitude is None or longitude is None:
        return list(messages)

    label = (city_name or "the user's current view").strip()
    context = (
        f"[AtmosMind UI context] The user is viewing weather for {label} "
        f"at latitude {latitude:.4f}, longitude {longitude:.4f}. "
        "When they refer to 'here', 'this city', or the current screen, call "
        "`get_current_weather_by_coordinates` or `get_weather_forecast_by_coordinates` "
        "with these coordinates directly — do NOT call `resolve_city_coordinates`."
    )
    out = list(messages)
    insert_at = 1 if out and isinstance(out[0], SystemMessage) else 0
    out.insert(insert_at, HumanMessage(content=context))
    return out


def history_from_api_messages(
    messages: Sequence[dict[str, str]],
) -> list[BaseMessage]:
    """
    Convert AtmosMind API chat payloads ``{"role": "user"|"assistant", "content": str}``
    into LangChain message objects.
    """
    out: list[BaseMessage] = []
    for item in messages:
        role = (item.get("role") or "").strip().casefold()
        content = (item.get("content") or "").strip()
        if not content:
            continue
        if role == "assistant":
            out.append(AIMessage(content=content))
        else:
            out.append(HumanMessage(content=content))
    return out


async def ainvoke_gemini_with_prompt(
    llm,
    settings: AgentPromptSettings,
    chat_history: Sequence[BaseMessage],
):
    """
    End-to-end example: inject dynamic prompt variables, then call Gemini.

    Parameters
    ----------
    llm:
        A ``ChatGoogleGenerativeAI`` instance (optionally ``.bind_tools(...)``).
    settings:
        ``AgentPromptSettings`` from the request (language + unit).
    chat_history:
        Prior turns as LangChain messages (HumanMessage / AIMessage).

    Returns
    -------
    AIMessage
        Model response (may include ``tool_calls`` when tools are bound).
    """
    prompted = build_prompted_messages(settings, chat_history)
    return await llm.ainvoke(prompted)


# Convenience: expose a single system-only preview for debugging / tests.
def preview_system_message(language: str = "en", unit: str = "metric") -> str:
    """Render the system prompt string for a given locale and unit (no chat history)."""
    settings = normalize_agent_settings(language=language, unit=unit)
    variables = build_prompt_variables(settings)
    variables["messages"] = []
    rendered = ATMOSMIND_AGENT_PROMPT.format_messages(**variables)
    system = rendered[0]
    if isinstance(system, SystemMessage):
        return str(system.content)
    return str(system)
