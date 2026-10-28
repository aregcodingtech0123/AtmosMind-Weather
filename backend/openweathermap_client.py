"""
OpenWeatherMap free-tier client (Current Weather + 5-day / 3-hour forecast).

Responses are normalized into Open-Meteo-shaped forecast JSON so existing parsers
(`open_meteo_client._parse_forecast_current`, `weather_detail._parse_forecast_payload`)
stay unchanged.
"""
from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import requests

from logging_config import log_outbound_api, log_upstream_status_event
from metrics import record_upstream_429_attempt, record_upstream_429_request, record_upstream_5xx_attempt

logger = logging.getLogger(__name__)

CURRENT_WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
SERVICE_WEATHER = "openweathermap-weather"
SERVICE_FORECAST = "openweathermap-forecast"

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


def _empty_open_meteo_shell(lat: float | None = None, lon: float | None = None) -> dict[str, Any]:
    return {
        "latitude": lat,
        "longitude": lon,
        "timezone": None,
        "current_weather": {},
        "current": {},
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


def normalize_current_weather_api(weather: dict[str, Any]) -> dict[str, Any]:
    """Map ``/data/2.5/weather`` JSON into Open-Meteo current blocks."""
    coord = weather.get("coord") if isinstance(weather.get("coord"), dict) else {}
    lat = coord.get("lat")
    lon = coord.get("lon")
    shell = _empty_open_meteo_shell(lat, lon)

    main = weather.get("main") if isinstance(weather.get("main"), dict) else {}
    wind = weather.get("wind") if isinstance(weather.get("wind"), dict) else {}
    owm_id = _weather_id_from_entry(weather)
    wmo = _owm_weather_id_to_wmo(owm_id)

    temp = main.get("temp")
    wind_speed = wind.get("speed")
    humidity = main.get("humidity")
    visibility = weather.get("visibility")
    feels_like = main.get("feels_like")

    shell["current_weather"] = {
        "temperature": round(float(temp), 1) if temp is not None else None,
        "weathercode": wmo,
        "windspeed": wind_speed,
        "is_day": 1,
    }
    shell["current"] = {
        "temperature_2m": temp,
        "weather_code": wmo,
        "relative_humidity_2m": humidity,
        "wind_speed_10m": wind_speed,
        "apparent_temperature": feels_like,
        "visibility": visibility,
        "dew_point_2m": None,
    }
    return shell


def _precip_mm_from_forecast_item(item: dict[str, Any]) -> float:
    rain = item.get("rain")
    if isinstance(rain, dict):
        val = rain.get("3h")
        if val is not None:
            return float(val)
    snow = item.get("snow")
    if isinstance(snow, dict):
        val = snow.get("3h")
        if val is not None:
            return float(val)
    return 0.0


def normalize_forecast_api(forecast: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    """Merge ``/data/2.5/forecast`` list into hourly + daily on an Open-Meteo shell."""
    items = forecast.get("list")
    if not isinstance(items, list):
        return base

    city = forecast.get("city") if isinstance(forecast.get("city"), dict) else {}
    if base.get("timezone") is None and city.get("timezone"):
        base["timezone"] = city.get("timezone")

    hourly = base["hourly"]
    for entry in items:
        if not isinstance(entry, dict):
            continue
        dt_txt = entry.get("dt_txt")
        if isinstance(dt_txt, str) and len(dt_txt) >= 16:
            time_label = dt_txt.replace(" ", "T")[:16]
        else:
            time_label = _iso_from_unix(entry.get("dt")) or ""
        hourly["time"].append(time_label)
        main = entry.get("main") if isinstance(entry.get("main"), dict) else {}
        hourly["temperature_2m"].append(main.get("temp"))
        hourly["weather_code"].append(_owm_weather_id_to_wmo(_weather_id_from_entry(entry)))
        hourly["relative_humidity_2m"].append(main.get("humidity"))
        wind = entry.get("wind") if isinstance(entry.get("wind"), dict) else {}
        hourly["wind_speed_10m"].append(wind.get("speed"))

    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in items:
        if not isinstance(entry, dict):
            continue
        dt_txt = entry.get("dt_txt")
        if isinstance(dt_txt, str) and len(dt_txt) >= 10:
            day = dt_txt[:10]
        else:
            day = _iso_date_from_unix(entry.get("dt")) or ""
        if day:
            by_date[day].append(entry)

    daily = base["daily"]
    for day in sorted(by_date.keys())[:7]:
        group = by_date[day]
        temps: list[float] = []
        precip_total = 0.0
        for entry in group:
            main = entry.get("main") if isinstance(entry.get("main"), dict) else {}
            t = main.get("temp")
            if t is not None:
                temps.append(float(t))
            precip_total += _precip_mm_from_forecast_item(entry)
        if not temps:
            continue
        daily["time"].append(day)
        daily["temperature_2m_max"].append(max(temps))
        daily["temperature_2m_min"].append(min(temps))
        daily["precipitation_sum"].append(round(precip_total, 1))
        daily["weather_code"].append(_owm_weather_id_to_wmo(_weather_id_from_entry(group[0])))

    return base


def normalize_standard_apis_to_open_meteo(
    current_weather: dict[str, Any],
    forecast: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Combine Current Weather + optional 5-day forecast into one Open-Meteo document."""
    base = normalize_current_weather_api(current_weather)
    if forecast is not None:
        base = normalize_forecast_api(forecast, base)
    return base


def _get_json_with_retry(
    url: str,
    *,
    params: dict[str, Any],
    service_name: str = SERVICE_WEATHER,
) -> dict[str, Any]:
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
                        service_name,
                        success=False,
                        latency_ms=latency_ms,
                        status_code=429,
                        error="rate_limited",
                        attempt=attempt + 1,
                    )
                    log_upstream_status_event(
                        "upstream_429",
                        service=service_name,
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
                        service_name,
                        success=False,
                        latency_ms=latency_ms,
                        status_code=status_code,
                        error="server_error",
                        attempt=attempt + 1,
                    )
                    log_upstream_status_event(
                        "upstream_5xx",
                        service=service_name,
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
                    service_name,
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
                    service_name,
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


def _request_params(lat: float, lon: float, api_key: str, units: str) -> dict[str, Any]:
    return {"lat": lat, "lon": lon, "appid": api_key, "units": units}


def fetch_current_weather(lat: float, lon: float, *, units: str = "metric") -> dict[str, Any]:
    """Current conditions only (batch / card bubbles). One HTTP call."""
    api_key = get_api_key()
    if not api_key:
        raise ValueError("OPENWEATHER_API_KEY is not configured")
    raw = _get_json_with_retry(
        CURRENT_WEATHER_URL,
        params=_request_params(lat, lon, api_key, units),
        service_name=SERVICE_WEATHER,
    )
    return normalize_current_weather_api(raw)


def fetch_weather_forecast(lat: float, lon: float, *, units: str = "metric") -> dict[str, Any]:
    """
    Full city-detail payload: Current Weather + 5-day / 3-hour forecast (two HTTP calls).
    """
    api_key = get_api_key()
    if not api_key:
        raise ValueError("OPENWEATHER_API_KEY is not configured")

    current_raw = _get_json_with_retry(
        CURRENT_WEATHER_URL,
        params=_request_params(lat, lon, api_key, units),
        service_name=SERVICE_WEATHER,
    )
    forecast_raw = _get_json_with_retry(
        FORECAST_URL,
        params=_request_params(lat, lon, api_key, units),
        service_name=SERVICE_FORECAST,
    )
    return normalize_standard_apis_to_open_meteo(current_raw, forecast_raw)


def fetch_onecall(lat: float, lon: float, *, units: str = "metric") -> dict[str, Any]:
    """Backward-compatible alias for ``fetch_weather_forecast``."""
    return fetch_weather_forecast(lat, lon, units=units)


def get_current_weather_by_coords(lat: float, lon: float) -> dict[str, Any]:
    """Current-weather dict aligned with ``open_meteo_client`` batch items."""
    from open_meteo_client import _parse_forecast_current

    try:
        payload = fetch_current_weather(lat, lon)
    except OpenWeatherRateLimitError:
        raise
    except Exception as exc:
        logger.warning("OpenWeatherMap fetch failed for (%s, %s): %s", lat, lon, exc)
        return {"error": str(exc)}
    return _parse_forecast_current(payload)
