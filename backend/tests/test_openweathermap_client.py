"""Tests for OpenWeatherMap 2.5 API normalization."""
from __future__ import annotations

from unittest.mock import patch

from openweathermap_client import (
    fetch_weather_forecast,
    normalize_current_weather_api,
    normalize_standard_apis_to_open_meteo,
)


def _sample_current_weather() -> dict:
    return {
        "coord": {"lon": 29.0, "lat": 41.0},
        "weather": [{"id": 800, "main": "Clear", "description": "clear sky"}],
        "main": {
            "temp": 22.5,
            "feels_like": 21.0,
            "humidity": 55,
        },
        "visibility": 10000,
        "wind": {"speed": 3.2},
        "dt": 1719230400,
    }


def _sample_forecast() -> dict:
    return {
        "city": {"timezone": 10800, "name": "Istanbul"},
        "list": [
            {
                "dt": 1719230400,
                "dt_txt": "2024-06-24 12:00:00",
                "main": {"temp": 22.0, "humidity": 50},
                "weather": [{"id": 800}],
                "wind": {"speed": 3.0},
                "pop": 0.1,
            },
            {
                "dt": 1719241200,
                "dt_txt": "2024-06-24 15:00:00",
                "main": {"temp": 24.0, "humidity": 48},
                "weather": [{"id": 801}],
                "wind": {"speed": 4.0},
                "rain": {"3h": 0.5},
            },
            {
                "dt": 1719316800,
                "dt_txt": "2024-06-25 12:00:00",
                "main": {"temp": 20.0, "humidity": 60},
                "weather": [{"id": 500}],
                "wind": {"speed": 2.5},
            },
        ],
    }


def test_normalize_current_weather_api_maps_fields():
    out = normalize_current_weather_api(_sample_current_weather())
    assert out["current"]["temperature_2m"] == 22.5
    assert out["current"]["weather_code"] == 0
    assert out["current"]["visibility"] == 10000
    assert out["current_weather"]["weathercode"] == 0


def test_normalize_standard_apis_builds_hourly_and_daily():
    out = normalize_standard_apis_to_open_meteo(_sample_current_weather(), _sample_forecast())
    assert len(out["hourly"]["time"]) == 3
    assert out["hourly"]["temperature_2m"][0] == 22.0
    assert len(out["daily"]["time"]) == 2
    assert out["daily"]["temperature_2m_max"][0] == 24.0
    assert out["daily"]["temperature_2m_min"][0] == 22.0
    assert out["daily"]["precipitation_sum"][0] == 0.5


def test_normalize_current_weather_api_missing_weather_and_main():
    out = normalize_current_weather_api({"coord": {"lat": 41.0, "lon": 29.0}})
    assert out["latitude"] == 41.0
    assert out["current_weather"]["temperature"] is None
    assert out["current_weather"]["weathercode"] == 3


def test_normalize_forecast_api_empty_list():
    base = normalize_current_weather_api(_sample_current_weather())
    out = normalize_standard_apis_to_open_meteo(_sample_current_weather(), {"list": []})
    assert out["hourly"]["time"] == []
    assert out["daily"]["time"] == []
    assert out["current"]["temperature_2m"] == base["current"]["temperature_2m"]


@patch("openweathermap_client.get_api_key", return_value="test-key")
@patch("openweathermap_client._get_json_with_retry")
def test_fetch_weather_forecast_calls_both_endpoints(mock_get, _mock_key):
    mock_get.side_effect = [_sample_current_weather(), _sample_forecast()]
    result = fetch_weather_forecast(41.0, 29.0)
    assert mock_get.call_count == 2
    assert result["current"]["temperature_2m"] == 22.5
    assert len(result["hourly"]["time"]) == 3
