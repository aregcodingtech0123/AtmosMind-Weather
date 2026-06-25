"""Tests for LangChain async weather tools (offline — mocked Open-Meteo / geocoding)."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from langchain_tools import (
    CoordinatesInput,
    get_current_weather_by_coordinates,
    resolve_city_coordinates,
)


@pytest.fixture
def open_meteo_forecast_payload() -> dict:
    return {
        "timezone": "Europe/Berlin",
        "current_weather": {
            "temperature": 18.2,
            "windspeed": 12.0,
            "weathercode": 61,
            "time": "2026-06-24T14:00",
        },
        "current": {"relative_humidity_2m": 72},
    }


@pytest.mark.asyncio
@patch("langchain_tools._open_meteo_get", new_callable=AsyncMock)
async def test_get_current_weather_by_coordinates_success(mock_fetch, open_meteo_forecast_payload):
    mock_fetch.return_value = open_meteo_forecast_payload

    result = await get_current_weather_by_coordinates.ainvoke(
        {
            "latitude": 52.52,
            "longitude": 13.41,
            "temperature_unit": "celsius",
        }
    )

    assert result["latitude"] == 52.52
    assert result["longitude"] == 13.41
    assert result["temperature"] == 18.2
    assert result["temperature_unit"] == "celsius"
    assert "condition" in result
    mock_fetch.assert_awaited_once()


@pytest.mark.asyncio
@patch("langchain_tools._open_meteo_get", new_callable=AsyncMock)
async def test_get_current_weather_by_coordinates_http_error(mock_fetch):
    import httpx

    mock_fetch.side_effect = httpx.HTTPError("upstream unavailable")

    result = await get_current_weather_by_coordinates.ainvoke(
        {"latitude": 52.52, "longitude": 13.41, "temperature_unit": "celsius"}
    )

    assert "error" in result
    assert result["latitude"] == 52.52


def test_coordinates_input_rejects_invalid_latitude():
    with pytest.raises(ValidationError):
        CoordinatesInput(latitude=999.0, longitude=13.41)


@pytest.mark.asyncio
@patch("langchain_tools.asyncio.to_thread", new_callable=AsyncMock)
async def test_resolve_city_coordinates_success(mock_thread):
    mock_thread.return_value = {"latitude": 48.8534, "longitude": 2.3488}

    result = await resolve_city_coordinates.ainvoke(
        {"city_name": "Paris", "language": "en"}
    )

    assert result["city_name"] == "Paris"
    assert result["latitude"] == 48.8534
    assert result["longitude"] == 2.3488
    mock_thread.assert_awaited_once()


@pytest.mark.asyncio
@patch("langchain_tools.asyncio.to_thread", new_callable=AsyncMock)
async def test_resolve_city_coordinates_not_found(mock_thread):
    mock_thread.return_value = None

    result = await resolve_city_coordinates.ainvoke(
        {"city_name": "Zzyzxville", "language": "en"}
    )

    assert "error" in result
    assert result["city_name"] == "Zzyzxville"
