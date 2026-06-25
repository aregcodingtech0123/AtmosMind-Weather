"""
City detail weather — full Open-Meteo forecast + lifestyle indices via the backend.

Forecast and lifestyle slices are fetched concurrently. Forecast failure surfaces as HTTP 503;
lifestyle failures degrade to null fields inside a 200 response.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from lifestyle_indices import (
    LifestyleIndicesResponse,
    _empty_lifestyle_response,
    fetch_lifestyle_indices,
)

logger = logging.getLogger(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_TIMEOUT_SECONDS = 8.0
HTTP_TIMEOUT = httpx.Timeout(FORECAST_TIMEOUT_SECONDS, connect=3.0)


class WeatherDetailCurrent(BaseModel):
    temperature: float
    weather_code: int
    humidity: float | None = None
    wind_speed: float | None = None
    feels_like: float | None = None


class WeatherDetailHourly(BaseModel):
    time: list[str] = Field(default_factory=list)
    temperature_2m: list[float] = Field(default_factory=list)
    weather_code: list[int] = Field(default_factory=list)
    relative_humidity_2m: list[float] = Field(default_factory=list)
    wind_speed_10m: list[float] = Field(default_factory=list)


class WeatherDetailDaily(BaseModel):
    time: list[str] = Field(default_factory=list)
    weather_code: list[int] = Field(default_factory=list)
    temperature_2m_max: list[float] = Field(default_factory=list)
    temperature_2m_min: list[float] = Field(default_factory=list)
    precipitation_sum: list[float] = Field(default_factory=list)


class WeatherDetailWeather(BaseModel):
    current: WeatherDetailCurrent | None = None
    hourly: WeatherDetailHourly = Field(default_factory=WeatherDetailHourly)
    daily: WeatherDetailDaily | None = None


class WeatherDetailResponse(BaseModel):
    latitude: float
    longitude: float
    weather: WeatherDetailWeather
    lifestyle_indices: LifestyleIndicesResponse


class ForecastUnavailableError(Exception):
    """Raised when the Open-Meteo forecast slice cannot be retrieved."""


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _float_list(values: Any) -> list[float]:
    if not isinstance(values, list):
        return []
    out: list[float] = []
    for item in values:
        parsed = _safe_float(item)
        if parsed is not None:
            out.append(parsed)
        else:
            out.append(0.0)
    return out


def _int_list(values: Any) -> list[int]:
    if not isinstance(values, list):
        return []
    out: list[int] = []
    for item in values:
        parsed = _safe_int(item)
        if parsed is not None:
            out.append(parsed)
        else:
            out.append(0)
    return out


def _string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(v) for v in values]


async def _fetch_forecast_json(
    client: httpx.AsyncClient,
    params: dict[str, Any],
) -> dict[str, Any]:
    response = await client.get(FORECAST_URL, params=params)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Forecast API returned a non-object JSON payload.")
    return payload


def _parse_forecast_payload(payload: dict[str, Any]) -> WeatherDetailWeather:
    current_raw = payload.get("current") or {}
    hourly_raw = payload.get("hourly") or {}
    daily_raw = payload.get("daily") or {}

    current: WeatherDetailCurrent | None = None
    if current_raw:
        temperature = _safe_float(current_raw.get("temperature_2m"))
        weather_code = _safe_int(current_raw.get("weather_code"))
        if temperature is not None and weather_code is not None:
            current = WeatherDetailCurrent(
                temperature=temperature,
                weather_code=weather_code,
                humidity=_safe_float(current_raw.get("relative_humidity_2m")),
                wind_speed=_safe_float(current_raw.get("wind_speed_10m")),
                feels_like=_safe_float(current_raw.get("apparent_temperature")),
            )

    hourly = WeatherDetailHourly(
        time=_string_list(hourly_raw.get("time")),
        temperature_2m=_float_list(hourly_raw.get("temperature_2m")),
        weather_code=_int_list(hourly_raw.get("weather_code")),
        relative_humidity_2m=_float_list(hourly_raw.get("relative_humidity_2m")),
        wind_speed_10m=_float_list(hourly_raw.get("wind_speed_10m")),
    )

    daily: WeatherDetailDaily | None = None
    if daily_raw:
        daily = WeatherDetailDaily(
            time=_string_list(daily_raw.get("time")),
            weather_code=_int_list(daily_raw.get("weather_code")),
            temperature_2m_max=_float_list(daily_raw.get("temperature_2m_max")),
            temperature_2m_min=_float_list(daily_raw.get("temperature_2m_min")),
            precipitation_sum=_float_list(daily_raw.get("precipitation_sum")),
        )

    if current is None and not hourly.time:
        raise ForecastUnavailableError("Forecast payload contained no usable weather data.")

    return WeatherDetailWeather(current=current, hourly=hourly, daily=daily)


async def fetch_weather_detail(
    latitude: float,
    longitude: float,
    language: str = "en",
    unit: Literal["metric", "imperial"] = "metric",
    redis_client: Any = None,
) -> WeatherDetailResponse:
    """
    Concurrent city-detail fetch: full forecast JSON + lifestyle indices.

    Raises ``ForecastUnavailableError`` when the forecast slice fails completely.
    Lifestyle failures return null lifestyle fields without raising.
    """
    lang = (language or "en").split("-")[0][:8]
    forecast_params = {
        "latitude": latitude,
        "longitude": longitude,
        "temperature_unit": "fahrenheit" if unit == "imperial" else "celsius",
        "current": (
            "temperature_2m,weather_code,relative_humidity_2m,"
            "wind_speed_10m,apparent_temperature"
        ),
        "hourly": "temperature_2m,weather_code,relative_humidity_2m,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "auto",
        "language": lang,
        "forecast_days": 7,
    }

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        forecast_result, lifestyle_result = await asyncio.gather(
            asyncio.wait_for(
                _fetch_forecast_json(client, forecast_params),
                timeout=FORECAST_TIMEOUT_SECONDS,
            ),
            fetch_lifestyle_indices(latitude, longitude, redis_client=redis_client),
            return_exceptions=True,
        )

    if isinstance(forecast_result, Exception):
        logger.warning(
            "Forecast detail failed for (%s, %s): %s",
            latitude,
            longitude,
            forecast_result,
        )
        raise ForecastUnavailableError(str(forecast_result)) from forecast_result

    if isinstance(lifestyle_result, Exception):
        logger.warning(
            "Lifestyle slice failed inside weather detail for (%s, %s): %s",
            latitude,
            longitude,
            lifestyle_result,
        )
        lifestyle_indices = _empty_lifestyle_response(latitude, longitude)
    else:
        lifestyle_indices = lifestyle_result

    weather = _parse_forecast_payload(forecast_result)
    return WeatherDetailResponse(
        latitude=latitude,
        longitude=longitude,
        weather=weather,
        lifestyle_indices=lifestyle_indices,
    )
