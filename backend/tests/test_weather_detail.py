"""Tests for unified weather detail service."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from lifestyle_indices import LifestyleIndicesResponse
from weather_detail import ForecastUnavailableError, fetch_weather_detail


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
        "weather_detail._fetch_forecast_json",
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
        "weather_detail._fetch_forecast_json",
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
        "weather_detail._fetch_forecast_json",
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
async def test_fetch_weather_detail_raises_when_forecast_times_out():
    async def _slow_forecast(*_args, **_kwargs):
        await asyncio.sleep(10)
        return _forecast_payload()

    with patch("weather_detail.FORECAST_TIMEOUT_SECONDS", 0.1):
        with patch("weather_detail._fetch_forecast_json", new=AsyncMock(side_effect=_slow_forecast)):
            with patch(
                "weather_detail.fetch_lifestyle_indices",
                new=AsyncMock(return_value=LifestyleIndicesResponse(latitude=1.0, longitude=2.0)),
            ):
                with pytest.raises(ForecastUnavailableError):
                    await fetch_weather_detail(1.0, 2.0)
