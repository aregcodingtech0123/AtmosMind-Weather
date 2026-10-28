"""Fresh-or-fail weather/AQ context for AI routes (never serve stale to LLMs)."""
from __future__ import annotations

from typing import Any

from cache_meta import DataStatus
from circuit_breaker import BREAKER_FORECAST, get_sync_breaker
from weather_provider import get_weather_data as get_current_weather_by_coords
from redis_cache import (
    get_cached_air_quality_with_meta,
    get_cached_weather_with_meta,
    set_cached_air_quality,
    set_cached_weather,
)
from resilience import UPSTREAM_UNAVAILABLE, swr_enabled


class DataUnavailableForAI(Exception):
    def __init__(self, retry_after_seconds: int = 60) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("data_unavailable")


def _retry_after_from_forecast() -> int:
    if not swr_enabled():
        return 60
    from metrics import is_circuit_breaker_enabled

    if is_circuit_breaker_enabled():
        return get_sync_breaker(BREAKER_FORECAST).retry_after_seconds() or 60
    return 60


def _normalize_weather_payload(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "temperature": data.get("temperature"),
        "condition": data.get("condition"),
        "weather_code": data.get("weather_code"),
    }


def require_fresh_weather_context(
    lat: float,
    lon: float,
    redis_client: Any,
) -> dict[str, Any]:
    """
    Return fresh current-weather fields for AI context.

    When SWR is enabled: only cache hits with age < soft TTL; stale cache is ignored.
    On upstream failure or CB block: raises DataUnavailableForAI (never stale numbers).
    When SWR is disabled: upstream fetch (Phase 1 behavior).
    """
    if swr_enabled() and redis_client is not None:
        cached, meta = get_cached_weather_with_meta(redis_client, lat, lon)
        if meta.data_status == DataStatus.FRESH and cached is not None:
            return dict(cached)

    result = get_current_weather_by_coords(lat, lon)
    if not isinstance(result, dict) or "error" in result:
        retry = _retry_after_from_forecast()
        if isinstance(result, dict) and result.get("error") == UPSTREAM_UNAVAILABLE:
            retry = get_sync_breaker(BREAKER_FORECAST).retry_after_seconds() or retry
        raise DataUnavailableForAI(retry_after_seconds=retry)

    payload = _normalize_weather_payload(result)
    if redis_client is not None:
        set_cached_weather(redis_client, lat, lon, payload)
    return payload


async def require_fresh_aq_context(
    lat: float,
    lon: float,
    redis_client: Any,
    client: Any,
) -> dict[str, Any]:
    """Fresh AQ JSON for AI — never serves stale cache when SWR is on."""
    from circuit_breaker import BREAKER_AIR_QUALITY, get_async_breaker
    from lifestyle_indices import _air_quality_params, _open_meteo_get, AIR_QUALITY_URL
    from metrics import is_circuit_breaker_enabled
    import asyncio

    if swr_enabled() and redis_client is not None:
        cached, meta = get_cached_air_quality_with_meta(redis_client, lat, lon)
        if meta.data_status == DataStatus.FRESH and cached is not None:
            return cached

    breaker = get_async_breaker(BREAKER_AIR_QUALITY)
    if is_circuit_breaker_enabled() and not await breaker.acquire_upstream_slot(permit_probe=True):
        retry = await breaker.retry_after_seconds() or 60
        raise DataUnavailableForAI(retry_after_seconds=retry)

    params = _air_quality_params(lat, lon)
    try:
        payload = await asyncio.wait_for(
            _open_meteo_get(
                client,
                AIR_QUALITY_URL,
                params,
                service="open-meteo-air-quality",
                lat=lat,
                lon=lon,
            ),
            timeout=3.0,
        )
    except Exception:
        if is_circuit_breaker_enabled():
            await breaker.record_failure(count=True)
        raise DataUnavailableForAI(retry_after_seconds=await breaker.retry_after_seconds() or 60)
    if is_circuit_breaker_enabled():
        await breaker.record_success()
    set_cached_air_quality(redis_client, lat, lon, payload)
    return payload


def weather_context_to_summary(payload: dict[str, Any], unit: str = "metric") -> str:
    temp = payload.get("temperature")
    condition = payload.get("condition") or "Unknown"
    unit_label = "°F" if unit == "imperial" else "°C"
    temp_text = f"{temp}{unit_label}" if temp is not None else "N/A"
    parts = [f"Current temperature: {temp_text}, conditions: {condition}."]
    code = payload.get("weather_code")
    if code is not None:
        parts.append(f"WMO weather code: {code}.")
    dew = payload.get("dew_point_celsius")
    if dew is not None:
        parts.append(f"Dew point: {dew}{unit_label}.")
    visibility = payload.get("visibility_meters")
    if visibility is not None:
        parts.append(f"Visibility: {visibility} m.")
    return " ".join(parts)


def data_unavailable_detail(exc: DataUnavailableForAI) -> dict[str, Any]:
    return {
        "error": "data_unavailable",
        "retry_after_seconds": exc.retry_after_seconds,
    }
