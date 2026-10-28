"""AI routes: fresh-or-fail when ENABLE_STALE_WHILE_REVALIDATE=true."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import api
from cache_meta import DataStatus
from redis_cache import CACHE_ENVELOPE_VERSION


@pytest.fixture
def swr_on(monkeypatch):
    monkeypatch.setenv("ENABLE_STALE_WHILE_REVALIDATE", "true")
    monkeypatch.setenv("WEATHER_SOFT_TTL_SECONDS", "1800")
    monkeypatch.setenv("WEATHER_HARD_TTL_SECONDS", "7200")


def _stale_envelope(temp: float = 99.0) -> str:
    ts = datetime.now(timezone.utc) - timedelta(seconds=2000)
    iso = ts.isoformat().replace("+00:00", "Z")
    return json.dumps(
        {
            "__atmosmind__": CACHE_ENVELOPE_VERSION,
            "fetched_at": iso,
            "data": {"temperature": temp, "condition": "Fake", "weather_code": 0},
        }
    )


@pytest.fixture
def client_with_redis(monkeypatch, swr_on):
    redis = MagicMock()
    monkeypatch.setattr(api, "_get_redis", lambda: redis)
    monkeypatch.setattr(api, "fetch_popular_for_redis", lambda conn, limit=1000: [])
    monkeypatch.setattr(api, "init_schema", lambda conn: None)
    monkeypatch.setattr(api, "get_connection", lambda: MagicMock())
    monkeypatch.setattr(api, "get_city_advice", lambda *a, **k: "advice text")
    monkeypatch.setattr(api, "get_forecast_summary", lambda *a, **k: "summary text")
    monkeypatch.setattr(api, "hava_durumu_asistani", lambda q: "ai text")
    with TestClient(api.app) as c:
        yield c, redis


def test_stale_cache_upstream_fail_returns_503_no_temperature(client_with_redis, monkeypatch):
    client, redis = client_with_redis
    redis.get.return_value = _stale_envelope(99.0).encode()
    monkeypatch.setattr(api, "_resolve_coords", lambda _c: (41.0, 29.0))
    monkeypatch.setattr(
        "ai_fresh_context.get_current_weather_by_coords",
        lambda *a, **k: {"error": "upstream_unavailable"},
    )

    resp = client.post(
        "/api/get-city-advice",
        json={
            "city": "Istanbul, Turkey",
            "weather_summary": "stale client summary 99C",
            "language": "en",
            "unit": "metric",
        },
    )
    assert resp.status_code == 503
    body = resp.json()
    detail = body["detail"]
    assert detail["error"] == "data_unavailable"
    assert isinstance(detail["retry_after_seconds"], int)
    assert "temperature" not in detail
    assert "condition" not in detail
    assert "temp_c" not in detail
    assert "99" not in json.dumps(body)


def test_fresh_cache_no_upstream_call(client_with_redis, monkeypatch):
    client, redis = client_with_redis
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    redis.get.return_value = json.dumps(
        {
            "__atmosmind__": CACHE_ENVELOPE_VERSION,
            "fetched_at": ts,
            "data": {"temperature": 12.0, "condition": "Clear", "weather_code": 0},
        }
    ).encode()
    monkeypatch.setattr(api, "_resolve_coords", lambda _c: (41.0, 29.0))
    fetch = MagicMock()
    monkeypatch.setattr("ai_fresh_context.get_current_weather_by_coords", fetch)

    resp = client.post(
        "/api/get-city-advice",
        json={
            "city": "Istanbul, Turkey",
            "weather_summary": "ignored",
            "language": "en",
            "unit": "metric",
        },
    )
    assert resp.status_code == 200
    fetch.assert_not_called()


def test_stale_cache_upstream_success_returns_200(client_with_redis, monkeypatch):
    client, redis = client_with_redis
    redis.get.return_value = _stale_envelope(99.0).encode()
    monkeypatch.setattr(api, "_resolve_coords", lambda _c: (41.0, 29.0))
    monkeypatch.setattr(
        "ai_fresh_context.get_current_weather_by_coords",
        lambda *a, **k: {"temperature": 15.0, "condition": "Rain", "weather_code": 61},
    )

    resp = client.post(
        "/api/ai-weather",
        json={"city": "Istanbul", "language": "en", "unit": "metric"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["temperature"] == 15.0


def test_cb_open_no_cache_503_retry_after(client_with_redis, monkeypatch):
    client, redis = client_with_redis
    monkeypatch.setenv("ENABLE_CIRCUIT_BREAKER", "true")
    monkeypatch.setenv("CB_FAILURE_THRESHOLD", "1")
    from circuit_breaker import BREAKER_FORECAST, reset_breakers_for_tests, get_sync_breaker

    reset_breakers_for_tests()
    b = get_sync_breaker(BREAKER_FORECAST)
    assert b.acquire_upstream_slot(permit_probe=True)
    b.record_failure(count=True)

    redis.get.return_value = None
    monkeypatch.setattr(api, "_resolve_coords", lambda _c: (41.0, 29.0))
    monkeypatch.setattr(
        "ai_fresh_context.get_current_weather_by_coords",
        lambda *a, **k: {"error": "upstream_unavailable"},
    )

    resp = client.post(
        "/api/get-forecast-summary",
        json={
            "city": "Istanbul",
            "weather_summary": "x",
            "language": "en",
            "unit": "metric",
        },
    )
    assert resp.status_code == 503
    assert resp.json()["detail"]["retry_after_seconds"] >= 1
    reset_breakers_for_tests()


def test_stale_cache_cb_open_returns_503_not_stale_numbers(client_with_redis, monkeypatch):
    """Stale cache + CB open: AI must not accept stale; upstream blocked → 503."""
    client, redis = client_with_redis
    monkeypatch.setenv("ENABLE_CIRCUIT_BREAKER", "true")
    monkeypatch.setenv("CB_FAILURE_THRESHOLD", "1")
    from circuit_breaker import BREAKER_FORECAST, get_sync_breaker, reset_breakers_for_tests

    reset_breakers_for_tests()
    b = get_sync_breaker(BREAKER_FORECAST)
    b.acquire_upstream_slot(permit_probe=True)
    b.record_failure(count=True)

    redis.get.return_value = _stale_envelope(88.0).encode()
    monkeypatch.setattr(api, "_resolve_coords", lambda _c: (41.0, 29.0))
    monkeypatch.setattr(
        "ai_fresh_context.get_current_weather_by_coords",
        lambda *a, **k: {"error": "upstream_unavailable"},
    )

    resp = client.post(
        "/api/chat",
        json={
            "messages": [{"role": "user", "content": "hello"}],
            "language": "en",
            "unit": "metric",
            "city_name": "Istanbul",
            "latitude": 41.0,
            "longitude": 29.0,
        },
    )
    assert resp.status_code == 503
    detail = resp.json()["detail"]
    assert detail["error"] == "data_unavailable"
    assert "temperature" not in detail
    assert "88" not in json.dumps(resp.json())
    reset_breakers_for_tests()


@pytest.fixture
def advice_client_no_swr(monkeypatch):
    monkeypatch.setenv("ENABLE_STALE_WHILE_REVALIDATE", "false")
    redis = MagicMock()
    monkeypatch.setattr(api, "_get_redis", lambda: redis)
    monkeypatch.setattr(api, "fetch_popular_for_redis", lambda conn, limit=1000: [])
    monkeypatch.setattr(api, "init_schema", lambda conn: None)
    monkeypatch.setattr(api, "get_connection", lambda: MagicMock())
    with TestClient(api.app) as c:
        yield c


def test_malformed_owm_normalize_and_ai_advice_returns_graceful_fallback(
    advice_client_no_swr, monkeypatch
):
    """Malformed OWM JSON must not crash normalization; AI failures return 200 fallback copy."""
    from open_meteo_client import _parse_forecast_current
    from openweathermap_client import normalize_current_weather_api, normalize_standard_apis_to_open_meteo
    from ai_fresh_context import weather_context_to_summary

    shell = normalize_current_weather_api({"coord": {"lat": 41.0, "lon": 29.0}, "main": {"temp": 18.0}})
    normalize_standard_apis_to_open_meteo(
        {"coord": {"lat": 41.0, "lon": 29.0}},
        {"list": []},
    )
    parsed = _parse_forecast_current(shell)
    assert "error" not in parsed
    assert parsed.get("dew_point_celsius") is None
    summary = weather_context_to_summary(parsed)
    assert "18" in summary
    assert "None" not in summary

    def _fail_gemini(*_a, **_k):
        raise RuntimeError("gemini unavailable")

    monkeypatch.setattr("ai_advice.generate_text", _fail_gemini)

    resp = advice_client_no_swr.post(
        "/api/get-city-advice",
        json={
            "city": "Istanbul",
            "weather_summary": summary,
            "language": "en",
            "unit": "metric",
        },
    )
    assert resp.status_code == 200
    assert "unable to generate personalized advice" in resp.json()["advice"].casefold()


def test_get_city_advice_succeeds_with_owm_missing_dew_point(advice_client_no_swr, monkeypatch):
    from open_meteo_client import _parse_forecast_current
    from openweathermap_client import normalize_current_weather_api
    from ai_fresh_context import weather_context_to_summary

    shell = normalize_current_weather_api(
        {
            "coord": {"lat": 41.0, "lon": 29.0},
            "main": {"temp": 20.0, "humidity": 40},
            "wind": {"speed": 2.0},
        }
    )
    parsed = _parse_forecast_current(shell)
    summary = weather_context_to_summary(parsed)

    monkeypatch.setattr(
        "ai_advice.generate_text",
        lambda *_a, **_k: "**What to Wear**\n\nLight layers are fine today.",
    )

    resp = advice_client_no_swr.post(
        "/api/get-city-advice",
        json={
            "city": "Istanbul",
            "weather_summary": summary,
            "language": "en",
            "unit": "metric",
        },
    )
    assert resp.status_code == 200
    assert "What to Wear" in resp.json()["advice"]
