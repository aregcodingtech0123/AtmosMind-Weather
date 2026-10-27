"""
OpenWeatherMap One Call API 3.0 client.

Responses are normalized into Open-Meteo-shaped forecast JSON so existing parsers
(`open_meteo_client._parse_forecast_current`, `weather_detail._parse_forecast_payload`)
can stay unchanged.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import requests

from logging_config import log_outbound_api, log_upstream_status_event
from metrics import record_upstream_429_attempt, record_upstream_429_request, record_upstream_5xx_attempt

logger = logging.getLogger(__name__)

ONECALL_URL = "https://api.openweathermap.org/data/3.0/onecall"
SERVICE_NAME = "openweathermap-onecall"

MAX_RETRIES = max(1, int(os.getenv("OPENWEATHER_MAX_RETRIES", "3")))
RETRY_BASE_DELAY_SECONDS = max(0.1, float(os.getenv("OPENWEATHER_RETRY_BASE_DELAY_SECONDS", "1.0")))


class OpenWeatherRateLimitError(Exception):
    """OpenWeatherMap returned 429 after retries — do not fail over to Open-Meteo."""

    def __init__(self, message: str = "OpenWeatherMap rate limit exceeded") -> None:
        super().__init__(message)


def get_api_key() -> str | None:
    key = os.getenv("OPENWEATHER_API_KEY", "").strip()
    return key or None


def _owm_weather_id_to_wmo(owm_id: int | None) -> int:
    """Approximate WMO weather code from OpenWeather condition id."""
    if owm_id is None:
        return 3
    if 200 <= owm_id < 300:
        return 95
    if 300 <= owm_id < 400:
        return 51
    if 500 <= owm_id < 600:
        return 61
    if 600 <= owm_id < 700:
        return 71
    if 700 <= owm_id < 800:
        return 45
    if owm_id == 800:
        return 0
    if owm_id == 801:
        return 1
    if owm_id == 802:
        return 2
    if owm_id in (803, 804):
        return 3
    return 3


def _iso_from_unix(ts: Any) -> str | None:
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M")
    except (TypeError, ValueError, OSError):
        return None


def _iso_date_from_unix(ts: Any) -> str | None:
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return None


def _weather_id_from_entry(entry: dict[str, Any]) -> int | None:
    weather = entry.get("weather")
    if not isinstance(weather, list) or not weather:
        return None
    first = weather[0]
    if not isinstance(first, dict):
        return None
    try:
        return int(first.get("id"))
    except (TypeError, ValueError):
        return None


def normalize_onecall_to_open_meteo(payload: dict[str, Any]) -> dict[str, Any]:
    """Map One Call 3.0 JSON to Open-Meteo forecast document shape."""
    current = payload.get("current") or {}
    owm_id = _weather_id_from_entry(current if isinstance(current, dict) else {})
    wmo = _owm_weather_id_to_wmo(owm_id)

    temp = current.get("temp")
    wind = current.get("wind_speed")
    humidity = current.get("humidity")
    visibility = current.get("visibility")
    dew = current.get("dew_point")

    normalized: dict[str, Any] = {
        "latitude": payload.get("lat"),
        "longitude": payload.get("lon"),
        "timezone": payload.get("timezone"),
        "current_weather": {
            "temperature": round(float(temp), 1) if temp is not None else None,
            "weathercode": wmo,
            "windspeed": wind,
            "is_day": 1 if current.get("dt") else 1,
        },
        "current": {
            "temperature_2m": temp,
            "weather_code": wmo,
            "relative_humidity_2m": humidity,
            "wind_speed_10m": wind,
            "apparent_temperature": current.get("feels_like"),
            "visibility": visibility,
            "dew_point_2m": dew,
        },
        "hourly": {
            "time": [],
            "temperature_2m": [],
            "weather_code": [],
            "relative_humidity_2m": [],
            "wind_speed_10m": [],
        },
        "daily": {
            "time": [],
            "weather_code": [],
            "temperature_2m_max": [],
            "temperature_2m_min": [],
            "precipitation_sum": [],
        },
    }

    hourly = payload.get("hourly")
    if isinstance(hourly, list):
        for entry in hourly:
            if not isinstance(entry, dict):
                continue
            normalized["hourly"]["time"].append(_iso_from_unix(entry.get("dt")) or "")
            normalized["hourly"]["temperature_2m"].append(entry.get("temp"))
            normalized["hourly"]["weather_code"].append(
                _owm_weather_id_to_wmo(_weather_id_from_entry(entry))
            )
            normalized["hourly"]["relative_humidity_2m"].append(entry.get("humidity"))
            normalized["hourly"]["wind_speed_10m"].append(entry.get("wind_speed"))

    daily = payload.get("daily")
    if isinstance(daily, list):
        for entry in daily:
            if not isinstance(entry, dict):
                continue
            normalized["daily"]["time"].append(_iso_date_from_unix(entry.get("dt")) or "")
            temp_block = entry.get("temp")
            if isinstance(temp_block, dict):
                normalized["daily"]["temperature_2m_max"].append(temp_block.get("max"))
                normalized["daily"]["temperature_2m_min"].append(temp_block.get("min"))
            else:
                normalized["daily"]["temperature_2m_max"].append(entry.get("temp_max"))
                normalized["daily"]["temperature_2m_min"].append(entry.get("temp_min"))
            pop = entry.get("pop")
            normalized["daily"]["precipitation_sum"].append(
                round(float(pop) * 100, 1) if pop is not None else 0.0
            )
            normalized["daily"]["weather_code"].append(
                _owm_weather_id_to_wmo(_weather_id_from_entry(entry))
            )

    return normalized


def _get_json_with_retry(url: str, *, params: dict[str, Any]) -> dict[str, Any]:
    last_error: Exception | None = None
    saw_429 = False

    try:
        for attempt in range(MAX_RETRIES):
            started = time.perf_counter()
            status_code: int | None = None
            try:
                response = requests.get(url, params=params, timeout=15)
                status_code = response.status_code
                if response.status_code == 429:
                    saw_429 = True
                    latency_ms = (time.perf_counter() - started) * 1000
                    log_outbound_api(
                        SERVICE_NAME,
                        success=False,
                        latency_ms=latency_ms,
                        status_code=429,
                        error="rate_limited",
                        attempt=attempt + 1,
                    )
                    log_upstream_status_event(
                        "upstream_429",
                        service=SERVICE_NAME,
                        status_code=429,
                        attempt=attempt + 1,
                    )
                    record_upstream_429_attempt()
                    delay = RETRY_BASE_DELAY_SECONDS * (2**attempt)
                    time.sleep(delay)
                    last_error = OpenWeatherRateLimitError("429 Too Many Requests")
                    continue
                if 500 <= response.status_code < 600:
                    latency_ms = (time.perf_counter() - started) * 1000
                    log_outbound_api(
                        SERVICE_NAME,
                        success=False,
                        latency_ms=latency_ms,
                        status_code=status_code,
                        error="server_error",
                        attempt=attempt + 1,
                    )
                    log_upstream_status_event(
                        "upstream_5xx",
                        service=SERVICE_NAME,
                        status_code=status_code,
                        attempt=attempt + 1,
                    )
                    record_upstream_5xx_attempt()
                    delay = RETRY_BASE_DELAY_SECONDS * (2**attempt)
                    time.sleep(delay)
                    last_error = requests.HTTPError(
                        f"{response.status_code} Server Error", response=response
                    )
                    continue
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    raise ValueError("OpenWeatherMap returned non-object JSON")
                latency_ms = (time.perf_counter() - started) * 1000
                log_outbound_api(
                    SERVICE_NAME,
                    success=True,
                    latency_ms=latency_ms,
                    status_code=status_code,
                )
                return data
            except requests.RequestException as exc:
                last_error = exc
                latency_ms = (time.perf_counter() - started) * 1000
                if status_code is None and getattr(exc, "response", None) is not None:
                    status_code = exc.response.status_code
                log_outbound_api(
                    SERVICE_NAME,
                    success=False,
                    latency_ms=latency_ms,
                    status_code=status_code,
                    error=str(exc),
                    attempt=attempt + 1,
                )
                if attempt + 1 >= MAX_RETRIES:
                    break
                delay = RETRY_BASE_DELAY_SECONDS * (2**attempt)
                time.sleep(delay)
    finally:
        if saw_429:
            record_upstream_429_request()

    if isinstance(last_error, OpenWeatherRateLimitError):
        raise last_error
    if last_error is not None:
        raise last_error
    raise requests.RequestException("OpenWeatherMap request failed after retries")


def fetch_onecall(lat: float, lon: float, *, units: str = "metric") -> dict[str, Any]:
    api_key = get_api_key()
    if not api_key:
        raise ValueError("OPENWEATHER_API_KEY is not configured")

    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": units,
        "exclude": "minutely,alerts",
    }
    raw = _get_json_with_retry(ONECALL_URL, params=params)
    return normalize_onecall_to_open_meteo(raw)


def get_current_weather_by_coords(lat: float, lon: float) -> dict[str, Any]:
    """Current-weather dict aligned with ``open_meteo_client`` batch items."""
    from open_meteo_client import _parse_forecast_current

    try:
        payload = fetch_onecall(lat, lon)
    except OpenWeatherRateLimitError:
        raise
    except Exception as exc:
        logger.warning("OpenWeatherMap fetch failed for (%s, %s): %s", lat, lon, exc)
        return {"error": str(exc)}
    return _parse_forecast_current(payload)
