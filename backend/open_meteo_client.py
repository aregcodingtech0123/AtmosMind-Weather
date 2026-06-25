"""
Throttled Open-Meteo forecast client.

Uses multi-location batch requests and retry/backoff to avoid 429 rate limits.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import requests

from logging_config import log_outbound_api

logger = logging.getLogger(__name__)

GENERIC_ERROR = "An unexpected error occurred while processing your request. Please try again later."

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
CURRENT_PARAMS = (
    "current_weather=true"
    "&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,visibility,dew_point_2m"
)

BATCH_CHUNK_SIZE = max(1, int(os.getenv("OPEN_METEO_BATCH_CHUNK_SIZE", "40")))
CHUNK_PAUSE_SECONDS = max(0.0, float(os.getenv("OPEN_METEO_CHUNK_PAUSE_SECONDS", "1.5")))
MAX_RETRIES = max(1, int(os.getenv("OPEN_METEO_MAX_RETRIES", "3")))
RETRY_BASE_DELAY_SECONDS = max(0.1, float(os.getenv("OPEN_METEO_RETRY_BASE_DELAY_SECONDS", "1.0")))

_RATE_LIMIT_ERROR = "Unable to fetch weather data at the moment. Please try again later."


def _parse_forecast_current(fc_data: dict[str, Any]) -> dict[str, Any]:
    from weather_assistant import _weather_code_to_condition

    current_weather = fc_data.get("current_weather")
    if not current_weather:
        return {"error": "No current weather"}

    current_block = fc_data.get("current") or {}
    try:
        temperature = current_weather.get("temperature")
        if temperature is not None:
            temperature = round(float(temperature), 1)
        weather_code = current_weather.get("weathercode")
        condition = _weather_code_to_condition(weather_code)
        visibility = current_block.get("visibility")
        dew_point = current_block.get("dew_point_2m")
        payload: dict[str, Any] = {
            "temperature": temperature,
            "condition": condition,
            "weather_code": weather_code,
        }
        if visibility is not None:
            payload["visibility_meters"] = round(float(visibility), 0)
        if dew_point is not None:
            payload["dew_point_celsius"] = round(float(dew_point), 1)
        return payload
    except (TypeError, ValueError):
        return {"error": "Failed to parse forecast"}


def _build_batch_forecast_url(lats: list[float], lons: list[float]) -> str:
    lat_str = ",".join(str(lat) for lat in lats)
    lon_str = ",".join(str(lon) for lon in lons)
    return f"{FORECAST_URL}?latitude={lat_str}&longitude={lon_str}&{CURRENT_PARAMS}"


def _get_json_with_retry(url: str, *, locations: int | None = None) -> Any:
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        started = time.perf_counter()
        status_code: int | None = None
        try:
            response = requests.get(url, timeout=15)
            status_code = response.status_code
            if response.status_code == 429:
                latency_ms = (time.perf_counter() - started) * 1000
                log_outbound_api(
                    "open-meteo-forecast",
                    success=False,
                    latency_ms=latency_ms,
                    status_code=429,
                    locations=locations,
                    error="rate_limited",
                    attempt=attempt + 1,
                )
                delay = RETRY_BASE_DELAY_SECONDS * (2**attempt)
                time.sleep(delay)
                last_error = requests.HTTPError("429 Too Many Requests", response=response)
                continue
            response.raise_for_status()
            latency_ms = (time.perf_counter() - started) * 1000
            log_outbound_api(
                "open-meteo-forecast",
                success=True,
                latency_ms=latency_ms,
                status_code=status_code,
                locations=locations,
            )
            return response.json()
        except requests.RequestException as exc:
            last_error = exc
            latency_ms = (time.perf_counter() - started) * 1000
            if status_code is None and getattr(exc, "response", None) is not None:
                status_code = exc.response.status_code
            log_outbound_api(
                "open-meteo-forecast",
                success=False,
                latency_ms=latency_ms,
                status_code=status_code,
                locations=locations,
                error=str(exc),
                attempt=attempt + 1,
            )
            if attempt + 1 >= MAX_RETRIES:
                break
            delay = RETRY_BASE_DELAY_SECONDS * (2**attempt)
            time.sleep(delay)
    assert last_error is not None
    raise last_error


def _normalize_batch_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


def get_current_weather_batch_by_coords(
    coords: list[tuple[float, float]],
) -> list[dict[str, Any]]:
    """
    Fetch current weather for many coordinates using chunked Open-Meteo batch API.

    Return list is index-aligned with ``coords`` (one dict per input pair).
    """
    if not coords:
        return []

    results: list[dict[str, Any]] = [{"error": _RATE_LIMIT_ERROR} for _ in coords]

    for chunk_start in range(0, len(coords), BATCH_CHUNK_SIZE):
        if chunk_start > 0 and CHUNK_PAUSE_SECONDS > 0:
            time.sleep(CHUNK_PAUSE_SECONDS)

        chunk = coords[chunk_start : chunk_start + BATCH_CHUNK_SIZE]
        lats = [lat for lat, _lon in chunk]
        lons = [lon for _lat, lon in chunk]
        url = _build_batch_forecast_url(lats, lons)

        try:
            payload = _get_json_with_retry(url, locations=len(chunk))
        except requests.RequestException as exc:
            logger.warning(
                "Batch forecast failed for %d coordinates (chunk starting %d): %s",
                len(chunk),
                chunk_start,
                exc,
            )
            for offset in range(len(chunk)):
                results[chunk_start + offset] = {"error": _RATE_LIMIT_ERROR}
            continue

        items = _normalize_batch_payload(payload)
        for offset, item in enumerate(items):
            if offset >= len(chunk):
                break
            parsed = _parse_forecast_current(item)
            results[chunk_start + offset] = parsed

        for offset in range(len(items), len(chunk)):
            results[chunk_start + offset] = {"error": "No current weather"}

    return results


def get_current_weather_by_coords(lat: float, lon: float) -> dict[str, Any]:
    """Fetch current weather for a single coordinate pair (batch API under the hood)."""
    try:
        return get_current_weather_batch_by_coords([(lat, lon)])[0]
    except Exception as exc:
        logger.exception("Unexpected forecast error for coords (%s, %s): %s", lat, lon, exc)
        return {"error": GENERIC_ERROR}
