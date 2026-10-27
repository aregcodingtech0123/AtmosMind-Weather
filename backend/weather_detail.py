"""
City detail weather — full Open-Meteo forecast + lifestyle indices via the backend.

Forecast and lifestyle slices are fetched concurrently. Forecast failure surfaces as HTTP 503;
lifestyle failures degrade to null fields inside a 200 response.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import time
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from lifestyle_indices import (
    LifestyleIndicesResponse,
    _empty_lifestyle_response,
    fetch_air_quality_for_coords,
    fetch_lifestyle_indices,
    lifestyle_from_forecast_and_air,
)
from logging_config import (
    log_detail_lifestyle_shared_payload,
    log_outbound_api,
    log_upstream_status_event,
)
from metrics import (
    is_weather_detail_share_forecast_enabled,
    record_upstream_429_attempt,
    record_upstream_429_request,
    record_upstream_5xx_attempt,
)
from redis_cache import get_cached_weather_detail, set_cached_weather_detail

logger = logging.getLogger(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_READ_TIMEOUT_SECONDS = max(
    10.0, float(os.getenv("WEATHER_DETAIL_READ_TIMEOUT_SECONDS", "35"))
)
FORECAST_CONNECT_TIMEOUT_SECONDS = max(
    2.0, float(os.getenv("WEATHER_DETAIL_CONNECT_TIMEOUT_SECONDS", "8"))
)
MAX_RETRIES = max(1, int(os.getenv("WEATHER_DETAIL_MAX_RETRIES", "4")))
RETRY_BASE_DELAY_SECONDS = max(0.5, float(os.getenv("WEATHER_DETAIL_RETRY_BASE_DELAY_SECONDS", "1.5")))
HTTP_TIMEOUT = httpx.Timeout(
    FORECAST_READ_TIMEOUT_SECONDS,
    connect=FORECAST_CONNECT_TIMEOUT_SECONDS,
)


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
    """Fetch Open-Meteo forecast with retry/backoff (429 + transient network errors)."""
    last_exc: Exception | None = None
    saw_429 = False

    try:
        for attempt in range(MAX_RETRIES):
            started = time.perf_counter()
            status_code: int | None = None
            try:
                response = await client.get(FORECAST_URL, params=params)
                status_code = response.status_code
                if response.status_code == 429:
                    saw_429 = True
                    latency_ms = (time.perf_counter() - started) * 1000
                    log_outbound_api(
                        "open-meteo-forecast-detail",
                        success=False,
                        latency_ms=latency_ms,
                        status_code=429,
                        error="rate_limited",
                        attempt=attempt + 1,
                    )
                    log_upstream_status_event(
                        "upstream_429",
                        service="open-meteo-forecast-detail",
                        status_code=429,
                        attempt=attempt + 1,
                    )
                    record_upstream_429_attempt()
                    delay = RETRY_BASE_DELAY_SECONDS * (2**attempt)
                    logger.warning(
                        "Forecast detail rate limited (429), retry in %.1fs (attempt %d/%d)",
                        delay,
                        attempt + 1,
                        MAX_RETRIES,
                    )
                    await asyncio.sleep(delay)
                    last_exc = httpx.HTTPStatusError(
                        "429 Too Many Requests",
                        request=response.request,
                        response=response,
                    )
                    continue
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError("Forecast API returned a non-object JSON payload.")
                latency_ms = (time.perf_counter() - started) * 1000
                log_outbound_api(
                    "open-meteo-forecast-detail",
                    success=True,
                    latency_ms=latency_ms,
                    status_code=status_code,
                )
                return payload
            except httpx.HTTPStatusError as exc:
                # 429 is handled above (before raise_for_status); this path is 4xx/5xx only.
                last_exc = exc
                latency_ms = (time.perf_counter() - started) * 1000
                err_status = exc.response.status_code if exc.response else status_code
                log_outbound_api(
                    "open-meteo-forecast-detail",
                    success=False,
                    latency_ms=latency_ms,
                    status_code=err_status,
                    error=str(exc),
                    attempt=attempt + 1,
                )
                if err_status is not None and 500 <= err_status < 600:
                    log_upstream_status_event(
                        "upstream_5xx",
                        service="open-meteo-forecast-detail",
                        status_code=err_status,
                        attempt=attempt + 1,
                    )
                    record_upstream_5xx_attempt()
                raise
            except (httpx.RequestError, ValueError) as exc:
                last_exc = exc
                latency_ms = (time.perf_counter() - started) * 1000
                log_outbound_api(
                    "open-meteo-forecast-detail",
                    success=False,
                    latency_ms=latency_ms,
                    status_code=status_code,
                    error=str(exc),
                    attempt=attempt + 1,
                )
                if attempt + 1 >= MAX_RETRIES:
                    break
                delay = RETRY_BASE_DELAY_SECONDS * (2**attempt)
                logger.warning(
                    "Forecast detail request failed (%s), retry in %.1fs (attempt %d/%d)",
                    exc,
                    delay,
                    attempt + 1,
                    MAX_RETRIES,
                )
                await asyncio.sleep(delay)
    finally:
        if saw_429:
            record_upstream_429_request()

    if last_exc is not None:
        raise last_exc
    raise ForecastUnavailableError("Forecast request failed after retries.")


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

    # Fallback: legacy current_weather block when "current=" params are omitted upstream.
    if current is None:
        legacy = payload.get("current_weather") or {}
        temperature = _safe_float(legacy.get("temperature"))
        weather_code = _safe_int(legacy.get("weathercode"))
        if temperature is not None and weather_code is not None:
            current = WeatherDetailCurrent(
                temperature=temperature,
                weather_code=weather_code,
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


def _response_from_cache(cached: dict[str, Any]) -> WeatherDetailResponse:
    return WeatherDetailResponse.model_validate(cached)


def _detail_forecast_params(
    latitude: float,
    longitude: float,
    lang: str,
    unit: Literal["metric", "imperial"],
) -> dict[str, Any]:
    """Open-Meteo forecast params for city detail (visibility/dew only when share flag is on)."""
    share_forecast = is_weather_detail_share_forecast_enabled()
    current_fields = (
        "temperature_2m,weather_code,relative_humidity_2m,"
        "wind_speed_10m,apparent_temperature"
    )
    hourly_fields = "temperature_2m,weather_code,relative_humidity_2m,wind_speed_10m"
    if share_forecast:
        current_fields += ",visibility,dew_point_2m"
        hourly_fields += ",visibility,dew_point_2m"

    return {
        "latitude": latitude,
        "longitude": longitude,
        "temperature_unit": "fahrenheit" if unit == "imperial" else "celsius",
        "current": current_fields,
        "hourly": hourly_fields,
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "auto",
        "language": lang,
        "forecast_days": 7,
    }


async def _fetch_forecast_and_lifestyle_shared(
    client: httpx.AsyncClient,
    forecast_params: dict[str, Any],
    latitude: float,
    longitude: float,
    redis_client: Any,
) -> tuple[dict[str, Any], LifestyleIndicesResponse]:
    """
    One forecast HTTP call + parallel air quality (no second forecast call).

    If forecast fails, the air-quality task is cancelled (forecast failure short-circuits
    lifestyle assembly for the detail page).
    """
    forecast_task = asyncio.create_task(_fetch_forecast_json(client, forecast_params))
    aq_task = asyncio.create_task(
        fetch_air_quality_for_coords(client, redis_client, latitude, longitude)
    )
    try:
        forecast_result = await forecast_task
    except Exception:
        aq_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await aq_task
        raise

    air_result: Any
    try:
        air_result = await aq_task
    except Exception as exc:
        air_result = exc

    log_detail_lifestyle_shared_payload(
        latitude=latitude,
        longitude=longitude,
        shared=True,
    )
    lifestyle_indices = lifestyle_from_forecast_and_air(
        forecast_result, air_result, latitude, longitude
    )
    return forecast_result, lifestyle_indices


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

    if redis_client is not None:
        cached = get_cached_weather_detail(redis_client, latitude, longitude, lang, unit)
        if cached is not None:
            try:
                return _response_from_cache(cached)
            except Exception as exc:
                logger.debug("Invalid weather detail cache entry, refetching: %s", exc)

    forecast_params = _detail_forecast_params(latitude, longitude, lang, unit)
    share_forecast = is_weather_detail_share_forecast_enabled()

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        if share_forecast:
            try:
                forecast_result, lifestyle_indices = await _fetch_forecast_and_lifestyle_shared(
                    client,
                    forecast_params,
                    latitude,
                    longitude,
                    redis_client,
                )
            except Exception as exc:
                logger.warning(
                    "Forecast detail failed for (%s, %s): %s",
                    latitude,
                    longitude,
                    exc,
                )
                if redis_client is not None:
                    stale = get_cached_weather_detail(
                        redis_client, latitude, longitude, lang, unit
                    )
                    if stale is not None:
                        try:
                            logger.info(
                                "Serving stale cached weather detail for (%s, %s)",
                                latitude,
                                longitude,
                            )
                            return _response_from_cache(stale)
                        except Exception:
                            pass
                raise ForecastUnavailableError(str(exc)) from exc
        else:
            forecast_result, lifestyle_result = await asyncio.gather(
                _fetch_forecast_json(client, forecast_params),
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
                if redis_client is not None:
                    stale = get_cached_weather_detail(
                        redis_client, latitude, longitude, lang, unit
                    )
                    if stale is not None:
                        try:
                            logger.info(
                                "Serving stale cached weather detail for (%s, %s)",
                                latitude,
                                longitude,
                            )
                            return _response_from_cache(stale)
                        except Exception:
                            pass
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
    response = WeatherDetailResponse(
        latitude=latitude,
        longitude=longitude,
        weather=weather,
        lifestyle_indices=lifestyle_indices,
    )

    if redis_client is not None:
        try:
            set_cached_weather_detail(
                redis_client,
                latitude,
                longitude,
                lang,
                unit,
                response.model_dump(),
            )
        except Exception as exc:
            logger.debug("Failed to cache weather detail: %s", exc)

    return response
