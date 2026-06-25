"""Tests for throttled Open-Meteo batch client."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from open_meteo_client import get_current_weather_batch_by_coords, _parse_forecast_current


def test_parse_forecast_current_extracts_fields():
    payload = {
        "current_weather": {"temperature": 21.2, "weathercode": 2},
        "current": {"visibility": 10000, "dew_point_2m": 12.3},
    }
    result = _parse_forecast_current(payload)
    assert result["temperature"] == 21.2
    assert result["weather_code"] == 2
    assert result["visibility_meters"] == 10000


@patch("open_meteo_client._get_json_with_retry")
def test_batch_fetch_aligns_results_with_input_coords(mock_get):
    mock_get.return_value = [
        {
            "current_weather": {"temperature": 10.0, "weathercode": 0},
            "current": {},
        },
        {
            "current_weather": {"temperature": 20.0, "weathercode": 3},
            "current": {},
        },
    ]

    coords = [(51.5, -0.12), (48.8, 2.3)]
    results = get_current_weather_batch_by_coords(coords)

    assert len(results) == 2
    assert results[0]["temperature"] == 10.0
    assert results[1]["temperature"] == 20.0
    mock_get.assert_called_once()


@patch("open_meteo_client._get_json_with_retry")
def test_batch_fetch_retries_chunk_on_rate_limit(mock_get):
    response = MagicMock()
    response.status_code = 429
    http_error = __import__("requests").HTTPError("429", response=response)
    mock_get.side_effect = http_error

    results = get_current_weather_batch_by_coords([(40.0, 29.0)])
    assert len(results) == 1
    assert "error" in results[0]
