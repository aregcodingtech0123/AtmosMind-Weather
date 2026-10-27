"""Unit tests for weather provider failover."""
from __future__ import annotations

from unittest.mock import patch

import pytest
import requests

from openweathermap_client import OpenWeatherRateLimitError
from weather_provider import (
    get_current_weather_batch_by_coords,
    get_primary_provider,
    get_weather_data,
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
