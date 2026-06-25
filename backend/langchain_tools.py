"""
LangChain tools for the AtmosMind AI weather assistant.

These tools are designed for Gemini (or any LangChain-compatible chat model) via
``llm.bind_tools(get_atmosmind_tools())``. Input validation is enforced through
Pydantic schemas that mirror FastAPI request models.

Coordinate-first design:
  Favorites and search selections in AtmosMind are keyed by (latitude, longitude).
  The primary weather tools accept coordinates directly so the model can skip
  geocoding when the UI already knows the point on the map.

Usage (LangChain + Google Gemini):

    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_tools import get_atmosmind_tools

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    agent = llm.bind_tools(get_atmosmind_tools())
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Literal

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator

from weather_assistant import _weather_code_to_condition, geocode_city

logger = logging.getLogger(__name__)

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HTTP_TIMEOUT = httpx.Timeout(30.0, connect=25.0)


# ─── Pydantic input schemas (shared with tool args_schema) ───────────────────


class CoordinatesInput(BaseModel):
    """
    WGS-84 point — same identity model as AtmosMind favorites
    (lat/lon rounded to four decimals in the UI).
    """

    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="WGS-84 latitude in decimal degrees.",
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="WGS-84 longitude in decimal degrees.",
    )
    temperature_unit: Literal["celsius", "fahrenheit"] = Field(
        default="celsius",
        description="Unit for all temperature fields in the tool response.",
    )


class ForecastByCoordinatesInput(CoordinatesInput):
    """Extended coordinate input for multi-day forecast requests."""

    forecast_days: int = Field(
        default=7,
        ge=1,
        le=16,
        description="Number of forecast days to return (Open-Meteo max: 16).",
    )


class GeocodeCityInput(BaseModel):
    """Resolve a human-readable place name to coordinates (bridge tool)."""

    city_name: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description=(
            "Bare city or town name for geocoding — no grammatical suffixes "
            "(e.g. use 'Copenhagen', not \"Kopenhag'a\")."
        ),
    )
    language: str = Field(
        default="en",
        min_length=2,
        max_length=8,
        description="BCP-47 language hint for localized geocoding (e.g. en, tr).",
    )

    @field_validator("city_name")
    @classmethod
    def normalize_city_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("city_name cannot be empty.")
        return cleaned


# ─── Async Open-Meteo helpers (non-blocking for Uvicorn) ─────────────────────


async def _open_meteo_get(params: dict) -> dict:
    """Perform a single async GET against the Open-Meteo forecast API."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        response = await client.get(OPEN_METEO_FORECAST_URL, params=params)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Open-Meteo returned a non-object JSON payload.")
        return payload


def _format_local_time(iso_time: str | None) -> str | None:
    if not iso_time or not isinstance(iso_time, str):
        return None
    try:
        parsed = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        return parsed.strftime("%H:%M")
    except ValueError:
        return None


def _parse_current_block(fc_data: dict, temperature_unit: str) -> dict | None:
    current_weather = fc_data.get("current_weather") or {}
    current = fc_data.get("current") or {}
    if not current_weather:
        return None

    temperature = current_weather.get("temperature")
    if temperature is not None:
        temperature = round(float(temperature), 1)
    wind_speed = current_weather.get("windspeed")
    if wind_speed is not None:
        wind_speed = round(float(wind_speed), 1)
    weather_code = current_weather.get("weathercode")

    humidity = current.get("relative_humidity_2m")
    if humidity is not None:
        humidity = int(float(humidity))

    return {
        "temperature": temperature,
        "temperature_unit": temperature_unit,
        "condition": _weather_code_to_condition(weather_code),
        "weather_code": weather_code,
        "humidity_percent": humidity,
        "wind_kmh": wind_speed,
        "observed_at": current_weather.get("time"),
        "local_time": _format_local_time(current_weather.get("time")),
    }


def _parse_daily_block(daily: dict) -> list[dict]:
    rows: list[dict] = []
    dates = daily.get("time") or []
    for i, date_str in enumerate(dates):
        code = (daily.get("weather_code") or [None])[i]
        t_max = (daily.get("temperature_2m_max") or [None])[i]
        t_min = (daily.get("temperature_2m_min") or [None])[i]
        precip = (daily.get("precipitation_sum") or [None])[i]
        wind_max = (daily.get("wind_speed_10m_max") or [None])[i]
        rows.append(
            {
                "date": date_str,
                "temp_max": round(float(t_max), 1) if t_max is not None else None,
                "temp_min": round(float(t_min), 1) if t_min is not None else None,
                "condition": _weather_code_to_condition(code),
                "precipitation_mm": round(float(precip), 1) if precip is not None else None,
                "wind_max_kmh": round(float(wind_max), 1) if wind_max is not None else None,
            }
        )
    return rows


def _parse_hourly_block(hourly: dict, limit: int = 48) -> list[dict]:
    rows: list[dict] = []
    hourly_times = hourly.get("time") or []
    for i, time_str in enumerate(hourly_times[:limit]):
        code = (hourly.get("weather_code") or [None])[i]
        temp = (hourly.get("temperature_2m") or [None])[i]
        precip_prob = (hourly.get("precipitation_probability") or [None])[i]
        wind = (hourly.get("wind_speed_10m") or [None])[i]
        rows.append(
            {
                "time": time_str,
                "temperature": round(float(temp), 1) if temp is not None else None,
                "condition": _weather_code_to_condition(code),
                "precipitation_probability_percent": (
                    int(precip_prob) if precip_prob is not None else None
                ),
                "wind_kmh": round(float(wind), 1) if wind is not None else None,
            }
        )
    return rows


# ─── LangChain tools (async, Pydantic-validated) ─────────────────────────────


@tool(args_schema=CoordinatesInput)
async def get_current_weather_by_coordinates(
    latitude: float,
    longitude: float,
    temperature_unit: Literal["celsius", "fahrenheit"] = "celsius",
) -> dict:
    """
    Fetch live weather for an exact latitude/longitude pair.

    Prefer this tool when coordinates are already known — e.g. from AtmosMind
    favorites, autocomplete selection, or after ``resolve_city_coordinates``.
    Does not perform geocoding.
    """
    try:
        fc_data = await _open_meteo_get(
            {
                "latitude": latitude,
                "longitude": longitude,
                "temperature_unit": temperature_unit,
                "current_weather": "true",
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                "timezone": "auto",
            }
        )
    except httpx.HTTPError as exc:
        logger.warning(
            "Open-Meteo current weather failed for (%s, %s): %s",
            latitude,
            longitude,
            exc,
        )
        return {
            "error": "Unable to fetch weather data at the moment. Please try again later.",
            "latitude": latitude,
            "longitude": longitude,
        }
    except Exception as exc:
        logger.exception(
            "Unexpected error fetching current weather for (%s, %s): %s",
            latitude,
            longitude,
            exc,
        )
        return {"error": "An unexpected error occurred.", "latitude": latitude, "longitude": longitude}

    current = _parse_current_block(fc_data, temperature_unit)
    if current is None:
        return {
            "error": "Forecast API did not return current weather.",
            "latitude": latitude,
            "longitude": longitude,
        }

    return {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": fc_data.get("timezone"),
        **current,
    }


@tool(args_schema=ForecastByCoordinatesInput)
async def get_weather_forecast_by_coordinates(
    latitude: float,
    longitude: float,
    temperature_unit: Literal["celsius", "fahrenheit"] = "celsius",
    forecast_days: int = 7,
) -> dict:
    """
    Fetch current conditions plus daily and hourly forecast for a coordinate pair.

    Use for tomorrow, upcoming days, weekends, or any future time range when
    latitude and longitude are already known.
    """
    days = max(1, min(int(forecast_days or 7), 16))
    try:
        fc_data = await _open_meteo_get(
            {
                "latitude": latitude,
                "longitude": longitude,
                "temperature_unit": temperature_unit,
                "current_weather": "true",
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                "daily": (
                    "weather_code,temperature_2m_max,temperature_2m_min,"
                    "precipitation_sum,wind_speed_10m_max"
                ),
                "hourly": (
                    "temperature_2m,precipitation_probability,weather_code,wind_speed_10m"
                ),
                "forecast_days": days,
                "timezone": "auto",
            }
        )
    except httpx.HTTPError as exc:
        logger.warning(
            "Open-Meteo forecast failed for (%s, %s): %s",
            latitude,
            longitude,
            exc,
        )
        return {
            "error": "Unable to fetch forecast data at the moment. Please try again later.",
            "latitude": latitude,
            "longitude": longitude,
        }
    except Exception as exc:
        logger.exception(
            "Unexpected forecast error for (%s, %s): %s",
            latitude,
            longitude,
            exc,
        )
        return {"error": "An unexpected error occurred.", "latitude": latitude, "longitude": longitude}

    return {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": fc_data.get("timezone"),
        "temperature_unit": temperature_unit,
        "current": _parse_current_block(fc_data, temperature_unit),
        "daily": _parse_daily_block(fc_data.get("daily") or {}),
        "hourly": _parse_hourly_block(fc_data.get("hourly") or {}),
    }


@tool(args_schema=GeocodeCityInput)
async def resolve_city_coordinates(city_name: str, language: str = "en") -> dict:
    """
    Resolve a city or town name to latitude and longitude.

    Call this first when the user mentions a place by name but coordinates are
    not yet known. Then pass the returned coordinates to the coordinate-based
    weather tools.
    """
    # Existing geocode logic is synchronous (requests); offload to a thread pool
    # so the FastAPI event loop stays responsive under Uvicorn.
    coords = await asyncio.to_thread(geocode_city, city_name)
    if coords is None:
        return {
            "error": (
                f"No location found for '{city_name}'. "
                "Try the bare city name without grammar suffixes, or add the country."
            ),
            "city_name": city_name,
            "hint": "Use atlas-style spelling (e.g. Copenhagen, İstanbul, 東京).",
        }

    return {
        "city_name": city_name,
        "latitude": coords["latitude"],
        "longitude": coords["longitude"],
        "language": language.strip().casefold().split("-")[0] if language else "en",
    }


def get_atmosmind_tools() -> list:
    """
    Return the ordered tool list for LangChain agent / Gemini bind_tools.

    Recommended model flow:
      1. resolve_city_coordinates  (only when the user gives a place name)
      2. get_current_weather_by_coordinates OR get_weather_forecast_by_coordinates
    """
    return [
        get_current_weather_by_coordinates,
        get_weather_forecast_by_coordinates,
        resolve_city_coordinates,
    ]
