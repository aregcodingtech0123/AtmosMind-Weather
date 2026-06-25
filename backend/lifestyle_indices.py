"""
Lifestyle indices — air quality, UV, pollen, visibility, and dew point.

Fetches Open-Meteo Forecast + Air Quality APIs in parallel for a coordinate pair.
Air quality responses are Redis-cached; upstream failures degrade to null fields (never HTTP 500).
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo

import httpx
from pydantic import BaseModel, Field

from redis_cache import get_cached_air_quality, set_cached_air_quality
from logging_config import log_outbound_api

logger = logging.getLogger(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
AIR_QUALITY_TIMEOUT_SECONDS = 3.0
FORECAST_TIMEOUT_SECONDS = 4.0
HTTP_TIMEOUT = httpx.Timeout(FORECAST_TIMEOUT_SECONDS, connect=2.0)

PollenLevel = Literal["low", "medium", "high", "unknown"]
AqiCategory = Literal["good", "fair", "moderate", "poor", "very_poor", "hazardous", "unknown"]
UvCategory = Literal["low", "moderate", "high", "very_high", "extreme", "unknown"]


class PollenMetrics(BaseModel):
    birch: float | None = Field(default=None, description="Birch pollen grains/m³")
    grass: float | None = Field(default=None, description="Grass pollen grains/m³")
    ragweed: float | None = Field(default=None, description="Ragweed pollen grains/m³")
    level: PollenLevel = Field(default="unknown", description="Combined pollen severity")


class LifestyleIndicesResponse(BaseModel):
    latitude: float
    longitude: float
    timezone: str | None = None
    observed_at: str | None = None
    european_aqi: int | None = None
    us_aqi: int | None = None
    aqi_value: int | None = Field(default=None, description="Primary AQI (European preferred)")
    aqi_standard: Literal["european", "us", "none"] = "none"
    aqi_category: AqiCategory = "unknown"
    uv_index: float | None = None
    uv_category: UvCategory = "unknown"
    pollen: PollenMetrics = Field(default_factory=PollenMetrics)
    visibility_meters: float | None = None
    dew_point_celsius: float | None = None


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


def _current_hour_index(times: list[str], timezone: str | None) -> int:
    if not times:
        return 0
    try:
        tz = ZoneInfo(timezone) if timezone else ZoneInfo("UTC")
    except Exception:
        tz = ZoneInfo("UTC")

    now = datetime.now(tz).replace(minute=0, second=0, microsecond=0)
    best_idx = 0
    for i, raw in enumerate(times):
        try:
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz)
        except ValueError:
            continue
        if dt <= now:
            best_idx = i
    return best_idx


def _hourly_value(hourly: dict[str, Any], key: str, index: int) -> Any:
    series = hourly.get(key) or []
    if not isinstance(series, list) or index >= len(series):
        return None
    return series[index]


def classify_european_aqi(value: int | None) -> AqiCategory:
    if value is None:
        return "unknown"
    if value <= 20:
        return "good"
    if value <= 40:
        return "fair"
    if value <= 60:
        return "moderate"
    if value <= 80:
        return "poor"
    if value <= 100:
        return "very_poor"
    return "hazardous"


def classify_us_aqi(value: int | None) -> AqiCategory:
    if value is None:
        return "unknown"
    if value <= 50:
        return "good"
    if value <= 100:
        return "moderate"
    if value <= 150:
        return "poor"
    if value <= 200:
        return "very_poor"
    return "hazardous"


def classify_uv_index(value: float | None) -> UvCategory:
    if value is None:
        return "unknown"
    if value < 3:
        return "low"
    if value < 6:
        return "moderate"
    if value < 8:
        return "high"
    if value < 11:
        return "very_high"
    return "extreme"


def classify_pollen_level(
    birch: float | None,
    grass: float | None,
    ragweed: float | None,
) -> PollenLevel:
    values = [v for v in (birch, grass, ragweed) if v is not None]
    if not values:
        return "unknown"
    peak = max(values)
    if peak < 10:
        return "low"
    if peak < 50:
        return "medium"
    return "high"


async def _open_meteo_get(
    client: httpx.AsyncClient,
    url: str,
    params: dict[str, Any],
    *,
    service: str,
    lat: float | None = None,
    lon: float | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    status_code: int | None = None
    try:
        response = await client.get(url, params=params)
        status_code = response.status_code
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError(f"{url} returned a non-object JSON payload.")
        log_outbound_api(
            service,
            success=True,
            latency_ms=(time.perf_counter() - started) * 1000,
            lat=lat,
            lon=lon,
            status_code=status_code,
        )
        return payload
    except Exception as exc:
        if status_code is None and isinstance(exc, httpx.HTTPStatusError):
            status_code = exc.response.status_code
        log_outbound_api(
            service,
            success=False,
            latency_ms=(time.perf_counter() - started) * 1000,
            lat=lat,
            lon=lon,
            status_code=status_code,
            error=str(exc),
        )
        raise


async def _fetch_forecast_slice(
    client: httpx.AsyncClient,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Forecast slice (visibility, dew point) with a hard upper-bound timeout."""
    return await asyncio.wait_for(
        _open_meteo_get(
            client,
            FORECAST_URL,
            params,
            service="open-meteo-forecast",
            lat=params.get("latitude"),
            lon=params.get("longitude"),
        ),
        timeout=FORECAST_TIMEOUT_SECONDS,
    )


async def _fetch_air_quality_slice(
    client: httpx.AsyncClient,
    redis_client: Any,
    latitude: float,
    longitude: float,
    params: dict[str, Any],
) -> dict[str, Any]:
    """
    Air quality slice with Redis cache (15 min) and a strict 3 s outbound timeout.

    Raises on timeout or upstream HTTP errors so ``gather(..., return_exceptions=True)``
    can degrade AQI / UV / pollen fields without failing the whole endpoint.
    """
    cached = get_cached_air_quality(redis_client, latitude, longitude)
    if cached is not None:
        logger.debug("Air quality cache hit for (%s, %s)", latitude, longitude)
        return cached

    payload = await asyncio.wait_for(
        _open_meteo_get(
            client,
            AIR_QUALITY_URL,
            params,
            service="open-meteo-air-quality",
            lat=latitude,
            lon=longitude,
        ),
        timeout=AIR_QUALITY_TIMEOUT_SECONDS,
    )
    set_cached_air_quality(redis_client, latitude, longitude, payload)
    return payload


def _empty_lifestyle_response(latitude: float, longitude: float) -> LifestyleIndicesResponse:
    """Graceful degraded payload when upstream APIs are unavailable."""
    return LifestyleIndicesResponse(latitude=latitude, longitude=longitude)


def _build_lifestyle_indices(
    forecast_data: dict[str, Any],
    air_data: dict[str, Any],
    latitude: float,
    longitude: float,
) -> LifestyleIndicesResponse:
    timezone = forecast_data.get("timezone") or air_data.get("timezone")
    hour_idx = _current_hour_index((air_data.get("hourly") or {}).get("time") or [], timezone)

    hourly_aq = air_data.get("hourly") or {}
    european_aqi = _safe_int(_hourly_value(hourly_aq, "european_aqi", hour_idx))
    us_aqi = _safe_int(_hourly_value(hourly_aq, "us_aqi", hour_idx))
    uv_index = _safe_float(_hourly_value(hourly_aq, "uv_index", hour_idx))
    birch = _safe_float(_hourly_value(hourly_aq, "birch_pollen", hour_idx))
    grass = _safe_float(_hourly_value(hourly_aq, "grass_pollen", hour_idx))
    ragweed = _safe_float(_hourly_value(hourly_aq, "ragweed_pollen", hour_idx))

    if european_aqi is not None:
        aqi_value = european_aqi
        aqi_standard: Literal["european", "us", "none"] = "european"
        aqi_category = classify_european_aqi(european_aqi)
    elif us_aqi is not None:
        aqi_value = us_aqi
        aqi_standard = "us"
        aqi_category = classify_us_aqi(us_aqi)
    else:
        aqi_value = None
        aqi_standard = "none"
        aqi_category = "unknown"

    current = forecast_data.get("current") or {}
    visibility_m = _safe_float(current.get("visibility"))
    dew_point_c = _safe_float(current.get("dew_point_2m"))

    if visibility_m is None:
        hourly_fc = forecast_data.get("hourly") or {}
        fc_idx = _current_hour_index(hourly_fc.get("time") or [], timezone)
        visibility_m = _safe_float(_hourly_value(hourly_fc, "visibility", fc_idx))
    if dew_point_c is None:
        hourly_fc = forecast_data.get("hourly") or {}
        fc_idx = _current_hour_index(hourly_fc.get("time") or [], timezone)
        dew_point_c = _safe_float(_hourly_value(hourly_fc, "dew_point_2m", fc_idx))

    observed_at = current.get("time")
    if not observed_at:
        aq_times = hourly_aq.get("time") or []
        if hour_idx < len(aq_times):
            observed_at = aq_times[hour_idx]

    pollen_level = classify_pollen_level(birch, grass, ragweed)

    return LifestyleIndicesResponse(
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        observed_at=observed_at,
        european_aqi=european_aqi,
        us_aqi=us_aqi,
        aqi_value=aqi_value,
        aqi_standard=aqi_standard,
        aqi_category=aqi_category,
        uv_index=round(uv_index, 1) if uv_index is not None else None,
        uv_category=classify_uv_index(uv_index),
        pollen=PollenMetrics(
            birch=round(birch, 2) if birch is not None else None,
            grass=round(grass, 2) if grass is not None else None,
            ragweed=round(ragweed, 2) if ragweed is not None else None,
            level=pollen_level,
        ),
        visibility_meters=round(visibility_m, 0) if visibility_m is not None else None,
        dew_point_celsius=round(dew_point_c, 1) if dew_point_c is not None else None,
    )


async def fetch_lifestyle_indices(
    latitude: float,
    longitude: float,
    redis_client: Any = None,
) -> LifestyleIndicesResponse:
    """
    Parallel fetch: forecast (visibility, dew point) + air quality (AQI, UV, pollen).

    Air quality is Redis-cached and capped at 3 s. Partial upstream failures always
    return HTTP 200 with null lifestyle fields — never raise to the API layer.
    """
    forecast_params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "visibility,dew_point_2m",
        "hourly": "visibility,dew_point_2m",
        "timezone": "auto",
        "forecast_days": 1,
    }
    air_quality_params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": (
            "european_aqi,us_aqi,uv_index,"
            "birch_pollen,grass_pollen,ragweed_pollen"
        ),
        "timezone": "auto",
        "forecast_days": 1,
    }

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        forecast_result, air_result = await asyncio.gather(
            _fetch_forecast_slice(client, forecast_params),
            _fetch_air_quality_slice(
                client, redis_client, latitude, longitude, air_quality_params
            ),
            return_exceptions=True,
        )

    forecast_data: dict[str, Any] = {}
    air_data: dict[str, Any] = {}

    if isinstance(forecast_result, Exception):
        logger.warning(
            "Forecast slice failed for (%s, %s): %s",
            latitude,
            longitude,
            forecast_result,
        )
    else:
        forecast_data = forecast_result

    if isinstance(air_result, Exception):
        logger.warning(
            "Air quality slice failed for (%s, %s): %s",
            latitude,
            longitude,
            air_result,
        )
    else:
        air_data = air_result

    if not forecast_data and not air_data:
        return _empty_lifestyle_response(latitude, longitude)

    return _build_lifestyle_indices(forecast_data, air_data, latitude, longitude)
