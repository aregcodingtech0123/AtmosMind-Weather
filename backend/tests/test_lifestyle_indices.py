"""Tests for lifestyle indices service."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from lifestyle_indices import (
    classify_pollen_level,
    classify_uv_index,
    fetch_lifestyle_indices,
)


@pytest.mark.asyncio
async def test_fetch_lifestyle_indices_returns_degraded_when_both_upstream_fail():
    async def _fail(*_args, **_kwargs):
        raise TimeoutError("upstream timeout")

    with patch("lifestyle_indices._open_meteo_get", new=AsyncMock(side_effect=_fail)):
        result = await fetch_lifestyle_indices(40.0, 29.0)

    assert result.latitude == 40.0
    assert result.longitude == 29.0
    assert result.aqi_value is None
    assert result.visibility_meters is None


@pytest.mark.asyncio
async def test_fetch_lifestyle_indices_keeps_forecast_when_air_quality_times_out():
    forecast_payload = {
        "timezone": "Europe/Istanbul",
        "current": {"time": "2025-06-24T14:00", "visibility": 8000.0, "dew_point_2m": 14.0},
        "hourly": {"time": ["2025-06-24T14:00"], "visibility": [8000.0], "dew_point_2m": [14.0]},
    }

    async def _fake_get(_client, url, params, **_kwargs):
        if "air-quality" in url:
            await asyncio.sleep(5)
            return {}
        return forecast_payload

    with patch("lifestyle_indices._open_meteo_get", new=AsyncMock(side_effect=_fake_get)):
        result = await fetch_lifestyle_indices(41.0, 29.0)

    assert result.visibility_meters == 8000.0
    assert result.dew_point_celsius == 14.0
    assert result.aqi_value is None
    assert result.uv_index is None


@pytest.mark.asyncio
async def test_fetch_lifestyle_indices_uses_redis_air_quality_cache():
    forecast_payload = {
        "timezone": "Europe/London",
        "current": {"time": "2025-06-24T14:00", "visibility": 10000.0, "dew_point_2m": 10.0},
        "hourly": {"time": ["2025-06-24T14:00"], "visibility": [10000.0], "dew_point_2m": [10.0]},
    }
    air_payload = {
        "timezone": "Europe/London",
        "hourly": {
            "time": ["2025-06-24T14:00"],
            "european_aqi": [18],
            "us_aqi": [30],
            "uv_index": [2.0],
            "birch_pollen": [1.0],
            "grass_pollen": [2.0],
            "ragweed_pollen": [0.0],
        },
    }
    redis = MagicMock()
    mock_get = AsyncMock(side_effect=lambda _c, url, _p: forecast_payload if "forecast" in url else air_payload)

    with patch("lifestyle_indices.get_cached_air_quality", return_value=air_payload):
        with patch("lifestyle_indices._open_meteo_get", mock_get):
            result = await fetch_lifestyle_indices(51.5, -0.12, redis_client=redis)

    assert result.aqi_value == 18
    mock_get.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_lifestyle_indices_air_quality_http_error_degrades_fields():
    forecast_payload = {
        "timezone": "Europe/London",
        "current": {"time": "2025-06-24T14:00", "visibility": 9000.0, "dew_point_2m": 9.0},
        "hourly": {"time": ["2025-06-24T14:00"], "visibility": [9000.0], "dew_point_2m": [9.0]},
    }

    async def _fake_get(_client, url, params, **_kwargs):
        if "air-quality" in url:
            request = httpx.Request("GET", url)
            response = httpx.Response(429, request=request)
            raise httpx.HTTPStatusError("rate limited", request=request, response=response)
        return forecast_payload

    with patch("lifestyle_indices._open_meteo_get", new=AsyncMock(side_effect=_fake_get)):
        result = await fetch_lifestyle_indices(48.8, 2.3)

    assert result.visibility_meters == 9000.0
    assert result.european_aqi is None
    assert result.pollen.level == "unknown"


@pytest.mark.asyncio
async def test_fetch_lifestyle_indices_merges_forecast_and_air_quality():
    forecast_payload = {
        "timezone": "Europe/London",
        "current": {
            "time": "2025-06-24T14:00",
            "visibility": 12000.0,
            "dew_point_2m": 11.5,
        },
        "hourly": {"time": ["2025-06-24T14:00"], "visibility": [12000.0], "dew_point_2m": [11.5]},
    }
    air_payload = {
        "timezone": "Europe/London",
        "hourly": {
            "time": ["2025-06-24T14:00"],
            "european_aqi": [25],
            "us_aqi": [45],
            "uv_index": [5.2],
            "birch_pollen": [3.0],
            "grass_pollen": [12.0],
            "ragweed_pollen": [1.0],
        },
    }

    async def _fake_get(_client, url, params, **_kwargs):
        if "air-quality" in url:
            return air_payload
        return forecast_payload

    with patch("lifestyle_indices._open_meteo_get", new=AsyncMock(side_effect=_fake_get)):
        result = await fetch_lifestyle_indices(51.5, -0.12)

    assert result.aqi_value == 25
    assert result.aqi_standard == "european"
    assert result.uv_index == 5.2
    assert result.pollen.level == "medium"
    assert result.visibility_meters == 12000.0
    assert result.dew_point_celsius == 11.5


def test_classify_pollen_level_peak():
    assert classify_pollen_level(2.0, 3.0, 1.0) == "low"
    assert classify_pollen_level(15.0, 20.0, 5.0) == "medium"
    assert classify_pollen_level(5.0, 80.0, 10.0) == "high"


def test_classify_uv_index_bands():
    assert classify_uv_index(1.5) == "low"
    assert classify_uv_index(5.0) == "moderate"
    assert classify_uv_index(7.0) == "high"
