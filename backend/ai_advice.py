"""
City-specific weather advice using Gemini.
Input: city name + current/forecast weather summary → personalized advice.
"""
import logging

from gemini_client import generate_text

logger = logging.getLogger(__name__)


def get_city_advice(city_name: str, weather_summary: str, language: str = "en", unit: str = "metric") -> str:
    """
    Returns personalized advice (clothing, activities, warnings) for the city
    based on the provided weather summary.
    """
    prompt = f"""You are an expert AI Meteorologist and Personal Advisor on the AtmosMind weather platform.

City: {city_name}

Weather summary:
{weather_summary}

Provide concise, practical, personalized advice. Use Markdown:
- Put each section title on its own line in bold (e.g. **What to Wear**), then a blank line, then the paragraph.
- Do not place raw ** markers inline within a continuous sentence.
- You may use short bullet lists under a section.

Include what to wear/bring, activity suggestions or warnings, and a brief health/safety tip if relevant.

Keep the response friendly and under 200 words.
You MUST respond in language code '{language}' and use {'Fahrenheit (°F)' if unit == 'imperial' else 'Celsius (°C)'} for all temperature values."""

    try:
        return generate_text(prompt)
    except Exception as e:
        logger.exception("City advice generation failed: %s", e)
        return "An unexpected error occurred while processing your request. Please try again later."


def get_forecast_summary(city_name: str, weather_summary: str, language: str = "en", unit: str = "metric") -> str:
    """
    Returns a narrative weather forecast summary that interprets current and upcoming
    weather context for practical lifestyle/travel planning.
    """
    prompt = f"""You are an expert AI Meteorologist and Personal Advisor on the AtmosMind weather platform.

City: {city_name}

Weather data/context:
{weather_summary}

Produce a detailed, readable forecast summary for current and upcoming conditions.

Use Markdown with bold section headings on their own line, each followed by a blank line (e.g. **Overview**, **What to Expect**, **Planning Tips**). Do not use raw ** inline within a single continuous line.

Explain conditions in narrative form, interpret how temperature, humidity, wind, and precipitation affect comfort, and give practical implications for daily plans and travel (around 120-220 words).

You MUST respond in language code '{language}' and use {'Fahrenheit (°F)' if unit == 'imperial' else 'Celsius (°C)'} for all temperature values.
"""

    try:
        return generate_text(prompt)
    except Exception as e:
        logger.exception("Forecast summary generation failed: %s", e)
        return "An unexpected error occurred while processing your request. Please try again later."
