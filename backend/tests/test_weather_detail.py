"""Tests for unified weather detail service."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from lifestyle_indices import LifestyleIndicesResponse
from weather_detail import ForecastUnavailableError, fetch_weather_detail


@pytest.mark.asyncio
async def test_fetch_weather_detail_uses_redis_cache():
    cached_payload = {
        "latitude": 41.0,
        "longitude": 29.0,
        "weather": {
            "current": {
                "temperature": 20.0,
                "weather_code": 1,
                "humidity": 50.0,
                "wind_speed": 10.0,
                "feels_like": 19.0,
            },
            "hourly": {
                "time": ["2025-06-24T12:00"],
                "temperature_2m": [20.0],
                "weather_code": [1],
                "relative_humidity_2m": [50.0],
                "wind_speed_10m": [10.0],
            },
            "daily": None,
        },
        "lifestyle_indices": {
            "latitude": 41.0,
            "longitude": 29.0,
            "aqi_standard": "none",
            "aqi_category": "unknown",
            "uv_category": "unknown",
            "pollen": {"level": "unknown"},
        },
    }
    redis = MagicMock()
    with patch(
        "weather_detail.get_cached_weather_detail",
        return_value=cached_payload,
    ):
        with patch("weather_detail.get_weather_detail", new=AsyncMock()) as forecast_mock:
            result = await fetch_weather_detail(41.0, 29.0, redis_client=redis)

    forecast_mock.assert_not_called()
    assert result.weather.current is not None
    assert result.weather.current.temperature == 20.0


def _forecast_payload() -> dict:
    return {
        "current": {
            "temperature_2m": 18.5,
            "weather_code": 2,
            "relative_humidity_2m": 62,
            "wind_speed_10m": 12.0,
            "apparent_temperature": 17.0,
        },
        "hourly": {
            "time": ["2025-06-24T12:00", "2025-06-24T13:00"],
            "temperature_2m": [18.0, 19.0],
            "weather_code": [2, 3],
            "relative_humidity_2m": [60.0, 58.0],
            "wind_speed_10m": [11.0, 12.0],
        },
        "daily": {
            "time": ["2025-06-24"],
            "weather_code": [2],
            "temperature_2m_max": [22.0],
            "temperature_2m_min": [14.0],
            "precipitation_sum": [0.0],
        },
    }


@pytest.mark.asyncio
async def test_fetch_weather_detail_merges_forecast_and_lifestyle():
    lifestyle = LifestyleIndicesResponse(latitude=51.5, longitude=-0.12, aqi_value=20)

    with patch(
        "weather_detail.get_weather_detail",
        new=AsyncMock(return_value=_forecast_payload()),
    ):
        with patch(
            "weather_detail.fetch_lifestyle_indices",
            new=AsyncMock(return_value=lifestyle),
        ):
            result = await fetch_weather_detail(51.5, -0.12, language="en", unit="metric")

    assert result.weather.current is not None
    assert result.weather.current.temperature == 18.5
    assert result.weather.hourly.temperature_2m == [18.0, 19.0]
    assert result.lifestyle_indices.aqi_value == 20


@pytest.mark.asyncio
async def test_fetch_weather_detail_degrades_lifestyle_on_failure():
    with patch(
        "weather_detail.get_weather_detail",
        new=AsyncMock(return_value=_forecast_payload()),
    ):
        with patch(
            "weather_detail.fetch_lifestyle_indices",
            new=AsyncMock(side_effect=TimeoutError("aq timeout")),
        ):
            result = await fetch_weather_detail(51.5, -0.12)

    assert result.weather.current is not None
    assert result.lifestyle_indices.aqi_value is None


@pytest.mark.asyncio
async def test_fetch_weather_detail_raises_when_forecast_fails():
    with patch(
        "weather_detail.get_weather_detail",
        new=AsyncMock(side_effect=httpx.HTTPStatusError(
            "server error",
            request=httpx.Request("GET", "https://api.open-meteo.com/v1/forecast"),
            response=httpx.Response(500),
        )),
    ):
        with patch(
            "weather_detail.fetch_lifestyle_indices",
            new=AsyncMock(return_value=LifestyleIndicesResponse(latitude=1.0, longitude=2.0)),
        ):
            with pytest.raises(ForecastUnavailableError):
                await fetch_weather_detail(1.0, 2.0)


@pytest.mark.asyncio
async def test_share_forecast_calls_open_meteo_forecast_exactly_once(monkeypatch):
    call_count = 0

    async def fake_forecast(*_args, **_kwargs):
        nonlocal call_count
        call_count += 1
        return _forecast_payload()

    monkeypatch.setattr("weather_detail.is_weather_detail_share_forecast_enabled", lambda: True)
    monkeypatch.setattr("weather_detail.get_weather_detail", fake_forecast)
    monkeypatch.setattr(
        "weather_detail.fetch_air_quality_for_coords",
        AsyncMock(
            return_value={
                "timezone": "Europe/London",
                "hourly": {
                    "time": ["2025-06-24T12:00"],
                    "european_aqi": [10],
                    "us_aqi": [20],
                    "uv_index": [1.0],
                    "birch_pollen": [0.0],
                    "grass_pollen": [0.0],
                    "ragweed_pollen": [0.0],
                },
            }
        ),
    )

    await fetch_weather_detail(51.5, -0.12)
    assert call_count == 1, f"expected 1 forecast call, got {call_count}"


@pytest.mark.asyncio
async def test_fetch_weather_detail_share_forecast_parallel_no_second_forecast():
    lifestyle = LifestyleIndicesResponse(latitude=51.5, longitude=-0.12, aqi_value=15)
    aq_payload = {
        "timezone": "Europe/London",
        "hourly": {
            "time": ["2025-06-24T12:00"],
            "european_aqi": [15],
            "us_aqi": [30],
            "uv_index": [2.0],
            "birch_pollen": [0.0],
            "grass_pollen": [0.0],
            "ragweed_pollen": [0.0],
        },
    }

    with patch("weather_detail.is_weather_detail_share_forecast_enabled", return_value=True):
        with patch(
            "weather_detail.get_weather_detail",
            new=AsyncMock(return_value=_forecast_payload()),
        ):
            with patch(
                "weather_detail.fetch_air_quality_for_coords",
                new=AsyncMock(return_value=aq_payload),
            ):
                with patch(
                    "weather_detail.fetch_lifestyle_indices",
                    new=AsyncMock(),
                ) as lifestyle_mock:
                    with patch(
                        "weather_detail.log_detail_lifestyle_shared_payload",
                    ) as shared_log:
                        result = await fetch_weather_detail(51.5, -0.12)

    lifestyle_mock.assert_not_called()
    shared_log.assert_called_once()
    assert result.lifestyle_indices.aqi_value == 15


@pytest.mark.asyncio
async def test_fetch_weather_detail_share_forecast_forecast_fail_cancels_air_task():
    air_started = asyncio.Event()
    air_cancelled = asyncio.Event()

    async def slow_air_quality(*_args, **_kwargs):
        air_started.set()
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            air_cancelled.set()
            raise
        return {}

    with patch("weather_detail.is_weather_detail_share_forecast_enabled", return_value=True):
        with patch(
            "weather_detail.get_weather_detail",
            new=AsyncMock(side_effect=httpx.ReadTimeout("forecast timeout")),
        ):
            with patch(
                "weather_detail.fetch_air_quality_for_coords",
                new=AsyncMock(side_effect=slow_air_quality),
            ):
                with patch(
                    "weather_detail.lifestyle_from_forecast_and_air",
                    new=MagicMock(),
                ) as merge_mock:
                    with pytest.raises(ForecastUnavailableError):
                        await fetch_weather_detail(1.0, 2.0)

    await asyncio.wait_for(air_started.wait(), timeout=1.0)
    await asyncio.wait_for(air_cancelled.wait(), timeout=1.0)
    merge_mock.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_weather_detail_raises_when_forecast_times_out():
    with patch(
        "weather_detail.get_weather_detail",
        new=AsyncMock(side_effect=httpx.ReadTimeout("forecast read timeout")),
    ):
        with patch(
            "weather_detail.fetch_lifestyle_indices",
            new=AsyncMock(return_value=LifestyleIndicesResponse(latitude=1.0, longitude=2.0)),
        ):
            with pytest.raises(ForecastUnavailableError):
                await fetch_weather_detail(1.0, 2.0)
