"""Unit tests for weather provider failover."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest
import requests

from openweathermap_client import OpenWeatherRateLimitError
from weather_detail import ForecastUnavailableError
from weather_provider import (
    get_current_weather_batch_by_coords,
    get_primary_provider,
    get_weather_data,
    get_weather_detail,
)


@pytest.fixture(autouse=True)
def _clear_provider_env(monkeypatch):
    monkeypatch.delenv("WEATHER_PROVIDER_PRIMARY", raising=False)
    monkeypatch.setenv("OPENWEATHER_API_KEY", "test-key")


def test_primary_defaults_to_openweathermap():
    assert get_primary_provider() == "openweathermap"


def test_primary_open_meteo_env(monkeypatch):
    monkeypatch.setenv("WEATHER_PROVIDER_PRIMARY", "open-meteo")
    assert get_primary_provider() == "open-meteo"


@patch("weather_provider.meteo_current")
@patch("weather_provider.owm_current")
def test_openweather_success_no_fallback(mock_owm, mock_meteo, monkeypatch):
    mock_owm.return_value = {"temperature": 21.0, "condition": "Clear", "weather_code": 0}
    result = get_weather_data(41.0, 29.0)
    assert result["temperature"] == 21.0
    mock_owm.assert_called_once()
    mock_meteo.assert_not_called()


@patch("weather_provider.meteo_current")
@patch("weather_provider.owm_current")
def test_openweather_error_falls_back_to_meteo(mock_owm, mock_meteo, monkeypatch):
    mock_owm.return_value = {"error": "upstream failed"}
    mock_meteo.return_value = {"temperature": 18.0, "condition": "Cloudy", "weather_code": 3}
    result = get_weather_data(41.0, 29.0)
    assert result["temperature"] == 18.0
    mock_meteo.assert_called_once()


@patch("weather_provider.meteo_current")
@patch("weather_provider.owm_current")
def test_openweather_429_does_not_fallback(mock_owm, mock_meteo):
    mock_owm.side_effect = OpenWeatherRateLimitError()
    result = get_weather_data(41.0, 29.0)
    assert "error" in result
    mock_meteo.assert_not_called()


@patch("weather_provider.meteo_current")
@patch("weather_provider.owm_current")
def test_openweather_5xx_exception_falls_back(mock_owm, mock_meteo, monkeypatch):
    mock_owm.side_effect = requests.HTTPError(response=type("R", (), {"status_code": 503})())
    mock_meteo.return_value = {"temperature": 10.0, "condition": "Rainy", "weather_code": 61}
    result = get_weather_data(40.0, 29.0)
    assert result["temperature"] == 10.0
    mock_meteo.assert_called_once()


@patch("weather_provider.meteo_batch")
@patch("weather_provider.get_weather_data")
def test_batch_uses_per_coord_provider(mock_get, mock_batch, monkeypatch):
    mock_get.return_value = {"temperature": 5.0, "condition": "Clear", "weather_code": 0}
    results = get_current_weather_batch_by_coords([(1.0, 2.0), (3.0, 4.0)])
    assert len(results) == 2
    assert mock_get.call_count == 2
    mock_batch.assert_not_called()


@patch("weather_provider.meteo_batch")
def test_batch_open_meteo_primary_uses_meteo_batch(mock_batch, monkeypatch):
    monkeypatch.setenv("WEATHER_PROVIDER_PRIMARY", "open-meteo")
    mock_batch.return_value = [{"temperature": 1.0}]
    results = get_current_weather_batch_by_coords([(41.0, 29.0)])
    assert results == [{"temperature": 1.0}]
    mock_batch.assert_called_once()


def _detail_forecast_payload() -> dict:
    return {
        "current": {
            "temperature_2m": 20.0,
            "weather_code": 1,
            "relative_humidity_2m": 55.0,
            "wind_speed_10m": 8.0,
            "apparent_temperature": 19.0,
            "visibility": 10000.0,
            "dew_point_2m": 11.0,
        },
        "hourly": {
            "time": ["2025-06-24T12:00"],
            "temperature_2m": [20.0],
            "weather_code": [1],
            "relative_humidity_2m": [55.0],
            "wind_speed_10m": [8.0],
        },
        "daily": {
            "time": ["2025-06-24"],
            "weather_code": [1],
            "temperature_2m_max": [24.0],
            "temperature_2m_min": [15.0],
            "precipitation_sum": [0.0],
        },
    }


@pytest.mark.asyncio
async def test_detail_openweather_success(monkeypatch):
    from openweathermap_client import normalize_standard_apis_to_open_meteo

    current = {
        "coord": {"lon": 29.0, "lat": 41.0},
        "weather": [{"id": 800}],
        "main": {"temp": 22.5, "feels_like": 21.0, "humidity": 55},
        "visibility": 10000,
        "wind": {"speed": 3.2},
    }
    forecast = {
        "list": [
            {
                "dt_txt": "2024-06-24 12:00:00",
                "main": {"temp": 22.0, "humidity": 50},
                "weather": [{"id": 800}],
                "wind": {"speed": 3.0},
            }
        ],
    }
    owm_payload = normalize_standard_apis_to_open_meteo(current, forecast)

    captured: dict = {}

    async def _fake_to_thread(func, *_args, **_kwargs):
        captured["func"] = func.__name__
        return owm_payload

    monkeypatch.setattr("weather_provider.asyncio.to_thread", _fake_to_thread)

    async with httpx.AsyncClient() as client:
        result = await get_weather_detail(41.0, 29.0, "en", "metric", client=client)

    assert captured.get("func") == "fetch_weather_forecast"
    assert result["current"]["temperature_2m"] == 22.5
    assert result["current"]["visibility"] == 10000
    assert len(result["hourly"]["time"]) == 1


@pytest.mark.asyncio
async def test_detail_openweather_failover_to_meteo(monkeypatch):
    meteo_payload = _detail_forecast_payload()
    meteo_payload["current"]["temperature_2m"] = 17.0

    async def _failing_to_thread(_func, *_args, **_kwargs):
        raise requests.ConnectionError("owm unreachable")

    monkeypatch.setattr("weather_provider.asyncio.to_thread", _failing_to_thread)

    with patch(
        "weather_detail._fetch_forecast_json",
        new=AsyncMock(return_value=meteo_payload),
    ):
        async with httpx.AsyncClient() as client:
            result = await get_weather_detail(41.0, 29.0, "en", "metric", client=client)

    assert result["current"]["temperature_2m"] == 17.0


@pytest.mark.asyncio
async def test_detail_openweather_429_no_meteo_fallback(monkeypatch):
    async def _rate_limited_to_thread(_func, *_args, **_kwargs):
        raise OpenWeatherRateLimitError()

    monkeypatch.setattr("weather_provider.asyncio.to_thread", _rate_limited_to_thread)

    with patch("weather_detail._fetch_forecast_json", new=AsyncMock()) as meteo_mock:
        async with httpx.AsyncClient() as client:
            with pytest.raises(ForecastUnavailableError):
                await get_weather_detail(41.0, 29.0, "en", "metric", client=client)
        meteo_mock.assert_not_called()
