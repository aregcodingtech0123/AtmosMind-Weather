"""
City-specific weather advice using Gemini.
Input: city name + current/forecast weather summary → personalized advice.
"""
import os
import logging
import google.generativeai as genai

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)
logger = logging.getLogger(__name__)

_advice_model = genai.GenerativeModel("gemini-2.5-flash")


def get_city_advice(city_name: str, weather_summary: str, language: str = "en", unit: str = "metric") -> str:
    """
    Returns personalized advice (clothing, activities, warnings) for the city
    based on the provided weather summary.
    """
    prompt = f"""You are a helpful meteorological assistant. Given the following city and weather information, provide concise, practical advice in plain text (no markdown bullets needed, but you may use short paragraphs).

City: {city_name}

Weather summary:
{weather_summary}

Include:
- What to wear / bring (e.g. umbrella, layers)
- Activity suggestions or warnings (e.g. avoid prolonged outdoor exposure, good for a walk)
- Any short health or safety tip if relevant (e.g. hydration, UV)

Keep the response friendly and to the point (under 200 words).
You MUST respond in language code '{language}' and use {'Fahrenheit (°F)' if unit == 'imperial' else 'Celsius (°C)'} for all temperature values."""

    try:
        response = _advice_model.generate_content(prompt)
        return (response.text or "").strip()
    except Exception as e:
        logger.exception("City advice generation failed: %s", e)
        return "An unexpected error occurred while processing your request. Please try again later."


def get_forecast_summary(city_name: str, weather_summary: str, language: str = "en", unit: str = "metric") -> str:
    """
    Returns a narrative weather forecast summary that interprets current and upcoming
    weather context for practical lifestyle/travel planning.
    """
    prompt = f"""You are AtmosMind AI Assistant, a weather and climate intelligence expert.
Given the city and weather data below, produce a detailed but readable English forecast summary.

City: {city_name}

Weather data/context:
{weather_summary}

Instructions:
- Explain expected weather conditions in narrative form (not a raw list of numbers).
- Interpret why the weather may feel that way based on temperature, humidity, wind, and precipitation-related data.
- Include practical implications for daily plans, travel comfort, and outdoor activities.
- Keep it concise and clear (around 120-220 words), plain text, no markdown headings.
You MUST respond in language code '{language}' and use {'Fahrenheit (°F)' if unit == 'imperial' else 'Celsius (°C)'} for all temperature values.
"""

    try:
        response = _advice_model.generate_content(prompt)
        return (response.text or "").strip()
    except Exception as e:
        logger.exception("Forecast summary generation failed: %s", e)
        return "An unexpected error occurred while processing your request. Please try again later."
