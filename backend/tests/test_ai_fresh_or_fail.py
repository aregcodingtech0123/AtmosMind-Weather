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
    assert body["detail"]["error"] == "data_unavailable"
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
