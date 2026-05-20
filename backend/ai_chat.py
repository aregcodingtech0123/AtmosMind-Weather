"""
Global weather chatbot with function calling: LLM can call get_current_weather or
get_weather_forecast to fetch live and future data. Conversation history is preserved;
tool calls are intercepted and executed by the backend, then results are fed back to
the LLM for the final Markdown-formatted reply.
"""
import os
import re
import warnings
import logging

warnings.filterwarnings("ignore", category=FutureWarning, message=".*google.generativeai.*")
import google.generativeai as genai

from weather_assistant import get_live_weather, get_weather_forecast
logger = logging.getLogger(__name__)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

DECLINE_MESSAGES = {
    "en": (
        "As your AtmosMind AI Assistant, I am specialized in weather and climate-related insights. "
        "I'm unable to answer questions outside of this field. However, I'd be happy to help you with "
        "the weather forecast or travel advice for any city!"
    ),
    "tr": (
        "AtmosMind AI Asistaniniz olarak hava durumu ve iklim konularinda uzmanim. "
        "Bu alanin disindaki sorulara yanit veremem. Ancak herhangi bir sehir icin "
        "hava tahmini veya seyahat tavsiyesi konusunda memnuniyetle yardimci olurum!"
    ),
    "fr": (
        "En tant qu'assistant IA AtmosMind, je suis specialise dans la meteo et le climat. "
        "Je ne peux pas repondre aux sujets en dehors de ce domaine. "
        "Je peux cependant vous aider avec les previsions meteo ou des conseils de voyage."
    ),
    "es": (
        "Como asistente de IA de AtmosMind, estoy especializado en clima y meteorologia. "
        "No puedo responder preguntas fuera de este ambito. "
        "Con gusto puedo ayudarte con el pronostico del tiempo o consejos de viaje."
    ),
    "de": (
        "Als AtmosMind KI-Assistent bin ich auf Wetter- und Klimathemen spezialisiert. "
        "Fragen ausserhalb dieses Bereichs kann ich nicht beantworten. "
        "Gern helfe ich dir aber mit Wettervorhersagen oder Reisetipps."
    ),
    "ja": (
        "AtmosMind AIアシスタントとして、私は天気・気候に関する質問に特化しています。"
        "この分野以外の質問にはお答えできません。"
        "ただし、都市ごとの天気予報や旅行アドバイスは喜んでお手伝いします。"
    ),
    "zh": (
        "作为 AtmosMind AI 助手，我专注于天气与气候相关问题。"
        "我无法回答该领域之外的问题。"
        "不过我很乐意为你提供任意城市的天气预报或出行建议。"
    ),
    "ko": (
        "AtmosMind AI 어시스턴트로서 저는 날씨 및 기후 관련 주제에 특화되어 있습니다. "
        "이 범위를 벗어난 질문에는 답변할 수 없습니다. "
        "다만 도시별 날씨 예보와 여행 조언은 기꺼이 도와드릴 수 있습니다."
    ),
    "ru": (
        "Как AI-ассистент AtmosMind, я специализируюсь на погоде и климате. "
        "Я не могу отвечать на вопросы вне этой области. "
        "Но с удовольствием помогу с прогнозом погоды и советами для поездок."
    ),
    "ar": (
        "بصفتي مساعد AtmosMind الذكي، فأنا متخصص في موضوعات الطقس والمناخ. "
        "لا يمكنني الإجابة عن الأسئلة خارج هذا النطاق. "
        "لكن يسعدني مساعدتك في توقعات الطقس أو نصائح السفر لأي مدينة."
    ),
    "it": (
        "Come assistente IA di AtmosMind, sono specializzato in meteo e clima. "
        "Non posso rispondere a domande fuori da questo ambito. "
        "Posso pero aiutarti con previsioni meteo e consigli di viaggio."
    ),
    "pt": (
        "Como assistente de IA da AtmosMind, sou especializado em clima e meteorologia. "
        "Nao posso responder perguntas fora desse escopo. "
        "Mas posso ajudar com previsoes do tempo e dicas de viagem para qualquer cidade."
    ),
}

OFFENSIVE_LANGUAGE_MESSAGE = (
    "I am programmed to be a helpful and respectful weather assistant. "
    "I cannot respond to messages containing offensive language. Please keep our "
    "conversation respectful and focused on weather or climate-related topics."
)

SYSTEM_PROMPT = """You are an expert AI Meteorologist and Personal Advisor integrated into the AtmosMind weather platform.

Role:
- Provide accurate, context-aware weather information and personalized advice for both current conditions and future forecasts.
- Maintain a helpful, professional, and friendly tone. Prioritize clarity and accessibility.

Forecasting and advisory support:
- Handle questions about current weather and any upcoming date or time range.
- For future dates (tomorrow, next Tuesday, this weekend, etc.), call get_weather_forecast before answering and cite the matching day or hours from the tool data.
- For right-now or today-only current conditions, call get_current_weather.
- Give precise forecasts: temperature, precipitation, wind, humidity, and general conditions for the requested period.
- Offer personalized, actionable advice on how to dress and what precautions to take for those specific conditions (e.g., waterproof shoes and an umbrella when rain is likely).
- If the timeframe is vague, assume the most immediate upcoming period and state that assumption briefly.

Output formatting (required for the chat UI):
- Use Markdown for structure.
- Use bold section headings on their own line, each followed by a blank line before the next paragraph. Example:

**Current Conditions**

Temperature is 18°C with light rain.

**What to Wear**

Bring a waterproof jacket and shoes.

- Never place raw ** markers mid-sentence on the same line as other text; headings must be standalone lines.
- Use short paragraphs and bullet lists where helpful.

Scope:
- Answer only weather, meteorology, climate trends, and practical lifestyle/travel recommendations based on weather.
- Interpret implicit location prompts as weather intent (e.g., "How about London?" → weather guidance for London).
- If the user asks a clearly non-weather city question, acknowledge briefly and steer to weather-based guidance.

Tool usage:
- Always fetch data with tools before stating numbers; do not invent forecasts.
- You are an entity extractor for place names: pass ONLY the bare city/placename the geocoder expects — no grammatical suffixes, no Turkish/japanese particles glued to the name, no quotes, no full sentence.
  * Example TR: from "2 gün sonra Kopenhag'a gideceğim" use city_name "Kopenhag" or "Copenhagen", never "Kopenhag'a".
  * Example DE: from "nach Berlin fahren" use "Berlin".
  * Example AR: use "Paris" / "باريس" stripped to the placename token only if the API expects Latin; prefer common English/local atlas spellings when unsure.
- If a tool returns geocode_attempts or a hint in the error payload, briefly explain and politely ask the user for the standard city name or country — do not abandon the weather topic.
- If a tool call fails, use the error and hint fields to suggest a concise retry; keep the conversation about weather and travel planning.

Off-topic policy:
- If the user asks about topics outside weather/climate/travel-by-weather, politely decline using this exact response:
As your AtmosMind AI Assistant, I am specialized in weather and climate-related insights. I'm unable to answer questions outside of this field. However, I'd be happy to help you with the weather forecast or travel advice for any city!"""

OFFENSIVE_PATTERNS = [
    # English profanity / insults / hate slurs (non-exhaustive baseline)
    r"\bfuck(?:ing|er|ed)?\b",
    r"\bshit(?:ty)?\b",
    r"\bbitch(?:es)?\b",
    r"\basshole\b",
    r"\bdick(?:head)?\b",
    r"\bcunt\b",
    r"\bmotherfucker\b",
    r"\bretard(?:ed)?\b",
    r"\bnigg(?:a|er)\b",
    r"\bfag(?:got)?\b",
    r"\bkike\b",
    r"\bchink\b",
    r"\bspic\b",
    r"\bwhore\b",
    r"\bslut\b",
    # Turkish profanity / insults / hate expressions (non-exhaustive baseline)
    r"\bamk\b",
    r"\baq\b",
    r"\bsik(?:ik|erim|tir|t(?:i|ı)r|mek)?\b",
    r"\byarrak\b",
    r"\bpiç\b",
    r"\bpic\b",
    r"\borospu(?:\s*çocu(?:ğ|g)u)?\b",
    r"\bgöt(?:veren| herif|)\b",
    r"\bibne\b",
    r"\bkahpe\b",
    r"\bpezevenk\b",
    r"\bdangalak\b",
    r"\baptal\b",
    r"\bsalak\b",
    r"\beşek\b",
    r"\besek\b",
]

def _contains_offensive_language(text: str) -> bool:
    if not text or not text.strip():
        return False
    normalized = text.strip().casefold()
    normalized = re.sub(r"[\W_]+", " ", normalized)
    return any(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in OFFENSIVE_PATTERNS)


def _normalize_language(language: str | None) -> str:
    if not language:
        return "en"
    return language.strip().casefold().split("-")[0]


def _detect_prompt_language_ai(text: str, fallback_language: str = "en") -> str:
    """
    Detect the language of the latest user message.
    Returns one of supported language codes when possible; falls back safely.
    """
    if not text or not text.strip():
        return _normalize_language(fallback_language)

    prompt = f"""Detect the language of USER_TEXT.
Return ONLY one ISO-like code from this allowed list:
en, tr, fr, es, de, ja, zh, ko, ru, ar, it, pt

If uncertain, return: {fallback_language}

USER_TEXT:
{text}
"""
    try:
        response = _moderation_model.generate_content(prompt)
        detected = _normalize_language((response.text or "").strip())
        if detected in DECLINE_MESSAGES:
            return detected
    except Exception:
        pass
    return _normalize_language(fallback_language)


def _get_decline_message(language: str | None) -> str:
    lang = _normalize_language(language)
    return DECLINE_MESSAGES.get(lang, DECLINE_MESSAGES["en"])


def _is_weather_related_any_language_ai(text: str, language: str = "en") -> bool:
    if not text or not text.strip():
        return False
    prompt = f"""You are a multilingual intent classifier for a weather assistant.
Determine whether USER_TEXT is weather-intent in ANY language.

Classify as WEATHER if the user asks about:
- weather, climate, forecast, temperature, rain/snow/wind/humidity
- city/location conditions (explicit or implicit), e.g. "How is Istanbul today?"
- clothing/packing/activity advice based on location or conditions
- travel/commute recommendations that depend on weather

Classify as OFFTOPIC only if clearly unrelated to weather/climate/location-based weather advice.

Current user language hint: {language}

Strict output:
- WEATHER
- OFFTOPIC

USER_TEXT:
{text}
"""
    try:
        response = _moderation_model.generate_content(prompt)
        verdict = (response.text or "").strip().upper()
        return "WEATHER" in verdict
    except Exception:
        # Fail open for intent checks so valid weather questions are not blocked.
        return True

TOOLS_SCHEMA = [
    {
        "name": "get_current_weather",
        "description": (
            "Get the current weather (temperature, condition, humidity, wind) for a city. "
            "Use for now, today, or immediate conditions only."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city_name": {
                    "type": "STRING",
                    "description": (
                        "Bare city or town name only, atlas-style, for geocoding. Strip grammar: "
                        "no Turkish suffixes (e.g. dative with apostrophe), no surrounding words. "
                        "Good: Copenhagen, Kopenhag, Istanbul. Bad: inflected or sentence fragments."
                    ),
                },
            },
            "required": ["city_name"],
        },
    },
    {
        "name": "get_weather_forecast",
        "description": (
            "Get current weather plus daily and hourly forecast for a city. "
            "Use when the user asks about tomorrow, upcoming days, weekends, or any future date or time range."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city_name": {
                    "type": "STRING",
                    "description": (
                        "Bare city or town name only, atlas-style, for geocoding. Strip grammar: "
                        "no Turkish suffixes (e.g. dative with apostrophe), no surrounding words. "
                        "Good: Copenhagen, Kopenhag, Istanbul. Bad: inflected or sentence fragments."
                    ),
                },
                "forecast_days": {
                    "type": "INTEGER",
                    "description": "Number of forecast days to include (1-16). Default 7.",
                },
            },
            "required": ["city_name"],
        },
    },
]

_chat_model = genai.GenerativeModel(
    "gemini-2.5-flash",
    system_instruction=SYSTEM_PROMPT,
    tools=TOOLS_SCHEMA,
)

_moderation_model = genai.GenerativeModel("gemini-2.5-flash")


def _is_offensive_any_language_ai(text: str) -> bool:
    """
    Language-agnostic moderation check using the model itself.
    Returns True when text contains profanity, insults, hate speech,
    harassment, or highly inappropriate slang in any language.
    """
    if not text or not text.strip():
        return False

    prompt = f"""You are a strict content moderation classifier.
Task: Determine whether the USER_TEXT contains offensive language in ANY language.
Flag as offensive if it includes profanity, insults, hate speech, slurs, harassment,
or highly inappropriate slang (even partially censored/obfuscated).

Output format (strict):
Return only one token:
- ALLOW  (if safe/respectful)
- BLOCK  (if offensive/inappropriate)

USER_TEXT:
{text}
"""
    try:
        response = _moderation_model.generate_content(prompt)
        verdict = (response.text or "").strip().upper()
        return "BLOCK" in verdict
    except Exception:
        # Fail closed for safety-critical moderation layer.
        return True


def chat(messages: list[dict], language: str = "en", unit: str = "metric") -> str:
    """
    messages: list of {"role": "user"|"assistant", "content": str}
    Returns the assistant's next reply. Tool calls are executed server-side;
    conversation history is preserved.
    """
    if not messages:
        return "Send a message to start the conversation."

    last = messages[-1]
    if last.get("role") != "user":
        return "Last message must be from the user."
    # Safety first: moderation has priority over every other behavior.
    user_text = last.get("content", "")
    prompt_language = _detect_prompt_language_ai(user_text, fallback_language=language)
    if _contains_offensive_language(user_text) or _is_offensive_any_language_ai(user_text):
        return OFFENSIVE_LANGUAGE_MESSAGE
    if not _is_weather_related_any_language_ai(user_text, prompt_language):
        return _get_decline_message(prompt_language)

    try:
        # Build conversation contents for the API (user/model turns only; no tool turns yet)
        contents = [{
            "role": "user",
            "parts": [
                (
                    "You are a multi-lingual assistant. You must respond in the same language currently selected by the user in the UI. "
                    "If the UI is set to 'Español', your responses must be in Spanish. If '한국어', respond in Korean. "
                    f"The active language detected for this session is '{prompt_language}'. "
                    f"Use {'Fahrenheit (°F)' if unit == 'imperial' else 'Celsius (°C)'} for temperatures by default "
                    "to stay consistent with the user's global unit setting, unless the user explicitly requests "
                    "a different unit in their latest message."
                )
            ],
        }]
        for m in messages:
            role = "user" if m.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [m.get("content", "")]})

        max_tool_rounds = 5
        response = None

        for _ in range(max_tool_rounds):
            response = _chat_model.generate_content(contents)
            if not response.candidates or not response.candidates[0].content.parts:
                break

            part = response.candidates[0].content.parts[0]

            # Check for function call
            if not hasattr(part, "function_call") or part.function_call is None:
                return (response.text or "").strip()

            fc = part.function_call
            if fc.name not in ("get_current_weather", "get_weather_forecast"):
                break

            city_name = (fc.args.get("city_name") or fc.args.get("city") or "").strip()
            if not city_name:
                tool_result = {"error": "No city name provided."}
            elif fc.name == "get_weather_forecast":
                raw_days = fc.args.get("forecast_days", 7)
                try:
                    forecast_days = int(raw_days) if raw_days is not None else 7
                except (TypeError, ValueError):
                    forecast_days = 7
                tool_result = get_weather_forecast(city_name, forecast_days=forecast_days)
            else:
                tool_result = get_live_weather(city_name)

            # Append model message (with function_call) and function response to contents
            contents.append(response.candidates[0].content)
            contents.append({
                "role": "user",
                "parts": [{"function_response": {"name": fc.name, "response": tool_result}}],
            })

        return (response.text or "").strip() if response else "Sorry, something went wrong."
    except Exception as e:
        logger.exception("Chat processing failed: %s", e)
        return "An unexpected error occurred while processing your request. Please try again later."
