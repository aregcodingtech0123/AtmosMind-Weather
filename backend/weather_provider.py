"""
Weather provider failover: OpenWeatherMap (primary) with Open-Meteo fallback.

OpenWeather 429 responses do not trigger Open-Meteo fallback (key quota limits);
the existing forecast circuit breaker handles sustained upstream failure.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import requests

from open_meteo_client import (
    UpstreamBlockedError,
    get_current_weather_batch_by_coords as meteo_batch,
    get_current_weather_by_coords as meteo_current,
)
from openweathermap_client import (
    OpenWeatherRateLimitError,
    get_api_key,
    get_current_weather_by_coords as owm_current,
)

logger = logging.getLogger(__name__)

_PRIMARY_OPENWEATHER = "openweathermap"
_PRIMARY_OPEN_METEO = "open-meteo"


def get_primary_provider() -> str:
    raw = os.getenv("WEATHER_PROVIDER_PRIMARY", _PRIMARY_OPENWEATHER).strip().lower()
    if raw in (_PRIMARY_OPENWEATHER, "owm", "openweather"):
        return _PRIMARY_OPENWEATHER
    if raw in (_PRIMARY_OPEN_METEO, "open_meteo", "meteo"):
        return _PRIMARY_OPEN_METEO
    logger.warning("Unknown WEATHER_PROVIDER_PRIMARY=%r; using openweathermap", raw)
    return _PRIMARY_OPENWEATHER


def _current_from_openweather(
    lat: float,
    lon: float,
    *,
    count_cb_failures: bool = True,
    permit_cb_probe: bool = True,
) -> dict[str, Any]:
    return owm_current(lat, lon)


def _current_from_open_meteo(
    lat: float,
    lon: float,
    *,
    count_cb_failures: bool = True,
    permit_cb_probe: bool = True,
) -> dict[str, Any]:
    return meteo_current(
        lat,
        lon,
        count_cb_failures=count_cb_failures,
        permit_cb_probe=permit_cb_probe,
    )


def _is_failover_eligible(exc: Exception) -> bool:
    if isinstance(exc, OpenWeatherRateLimitError):
        return False
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        if exc.response.status_code == 429:
            return False
    return True


def get_weather_data(
    lat: float,
    lon: float,
    *,
    count_cb_failures: bool = True,
    permit_cb_probe: bool = True,
) -> dict[str, Any]:
    """
    Current weather for a coordinate pair (temperature, condition, weather_code, …).

    Selects primary provider from ``WEATHER_PROVIDER_PRIMARY`` and falls back to
    Open-Meteo on network/5xx failures only.
    """
    if get_primary_provider() == _PRIMARY_OPEN_METEO or not get_api_key():
        return _current_from_open_meteo(
            lat,
            lon,
            count_cb_failures=count_cb_failures,
            permit_cb_probe=permit_cb_probe,
        )

    try:
        result = _current_from_openweather(lat, lon)
        if "error" not in result:
            return result
        logger.info(
            "OpenWeatherMap returned error for (%s, %s); trying Open-Meteo fallback",
            lat,
            lon,
        )
    except OpenWeatherRateLimitError:
        logger.warning(
            "OpenWeatherMap rate limited for (%s, %s); not falling back to Open-Meteo",
            lat,
            lon,
        )
        return {
            "error": "Unable to fetch weather data at the moment. Please try again later.",
        }
    except Exception as exc:
        if not _is_failover_eligible(exc):
            raise
        logger.warning(
            "OpenWeatherMap failed for (%s, %s): %s; trying Open-Meteo fallback",
            lat,
            lon,
            exc,
        )

    return _current_from_open_meteo(
        lat,
        lon,
        count_cb_failures=count_cb_failures,
        permit_cb_probe=permit_cb_probe,
    )


def get_current_weather_by_coords(
    lat: float,
    lon: float,
    *,
    count_cb_failures: bool = True,
    permit_cb_probe: bool = True,
) -> dict[str, Any]:
    return get_weather_data(
        lat,
        lon,
        count_cb_failures=count_cb_failures,
        permit_cb_probe=permit_cb_probe,
    )


def get_current_weather_batch_by_coords(
    coords: list[tuple[float, float]],
    *,
    count_cb_failures: bool = True,
    permit_cb_probe: bool = True,
) -> list[dict[str, Any]]:
    if not coords:
        return []

    if get_primary_provider() == _PRIMARY_OPEN_METEO or not get_api_key():
        return meteo_batch(
            coords,
            count_cb_failures=count_cb_failures,
            permit_cb_probe=permit_cb_probe,
        )

    results: list[dict[str, Any]] = []
    fallback_coords: list[tuple[int, float, float]] = []

    for index, (lat, lon) in enumerate(coords):
        try:
            item = get_weather_data(
                lat,
                lon,
                count_cb_failures=count_cb_failures,
                permit_cb_probe=permit_cb_probe,
            )
        except UpstreamBlockedError:
            item = {"error": "upstream_unavailable"}
        except OpenWeatherRateLimitError:
            item = {
                "error": "Unable to fetch weather data at the moment. Please try again later.",
            }
        if "error" in item:
            fallback_coords.append((index, lat, lon))
            results.append(item)
        else:
            results.append(item)

    if not fallback_coords:
        return results

    meteo_subset = [(lat, lon) for _idx, lat, lon in fallback_coords]
    try:
        meteo_results = meteo_batch(
            meteo_subset,
            count_cb_failures=count_cb_failures,
            permit_cb_probe=permit_cb_probe,
        )
    except Exception:
        return results

    for (original_index, _lat, _lon), meteo_item in zip(fallback_coords, meteo_results):
        if "error" not in meteo_item:
            results[original_index] = meteo_item

    return results
