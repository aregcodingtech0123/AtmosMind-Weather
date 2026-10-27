"""X-AtmosMind-Refresh bypasses soft-fresh cache when SWR is on."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import api
from redis_cache import CACHE_ENVELOPE_VERSION


@pytest.fixture
def swr_batch_client(monkeypatch):
    monkeypatch.setenv("ENABLE_STALE_WHILE_REVALIDATE", "true")
    redis = MagicMock()
    monkeypatch.setattr(api, "_get_redis", lambda: redis)
    monkeypatch.setattr(api, "fetch_popular_for_redis", lambda *a, **k: [])
    monkeypatch.setattr(api, "init_schema", lambda c: None)
    monkeypatch.setattr(api, "get_connection", lambda: MagicMock())
    monkeypatch.setattr(api, "_resolve_coords", lambda _c: (41.0, 29.0))
    with TestClient(api.app) as client:
        yield client, redis


def test_refresh_header_bypasses_fresh_cache_short_circuit(swr_batch_client, monkeypatch):
    client, redis = swr_batch_client
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    redis.get.return_value = json.dumps(
        {
            "__atmosmind__": CACHE_ENVELOPE_VERSION,
            "fetched_at": ts,
            "data": {"temperature": 10.0, "condition": "Clear", "weather_code": 0},
        }
    ).encode()
    batch = MagicMock(
        return_value=[{"temperature": 22.0, "condition": "Rain", "weather_code": 61}]
    )
    monkeypatch.setattr(api, "get_current_weather_batch_by_coords", batch)

    with patch.object(api, "enforce_rate_limit", return_value=None):
        resp = client.post(
            "/api/weather/batch",
            json={"cities": ["Test City"]},
            headers={"X-AtmosMind-Refresh": "1"},
        )
    assert resp.status_code == 200
    item = resp.json()["results"][0]
    assert item["temperature"] == 22.0
    batch.assert_called_once()


def test_refresh_header_still_respects_cb_open(swr_batch_client, monkeypatch):
    client, redis = swr_batch_client
    monkeypatch.setenv("ENABLE_CIRCUIT_BREAKER", "true")
    monkeypatch.setenv("CB_FAILURE_THRESHOLD", "1")
    from circuit_breaker import BREAKER_FORECAST, get_sync_breaker, reset_breakers_for_tests

    reset_breakers_for_tests()
    b = get_sync_breaker(BREAKER_FORECAST)
    b.acquire_upstream_slot(permit_probe=True)
    b.record_failure(count=True)

    redis.get.return_value = None
    monkeypatch.setattr(
        api,
        "get_current_weather_batch_by_coords",
        lambda *a, **k: [{"error": "upstream_unavailable"}],
    )

    with patch.object(api, "enforce_rate_limit", return_value=None):
        resp = client.post(
            "/api/weather/batch",
            json={"cities": ["Test City"]},
            headers={"X-AtmosMind-Refresh": "1"},
        )
    item = resp.json()["results"][0]
    assert item["error"] == "upstream_unavailable"
    assert item["meta"]["data_status"] == "unavailable"
    reset_breakers_for_tests()


def test_refresh_header_ignored_when_cb_open(swr_batch_client, monkeypatch):
    """With CB open, refresh must not bypass fresh cache or call upstream."""
    client, redis = swr_batch_client
    monkeypatch.setenv("ENABLE_CIRCUIT_BREAKER", "true")
    monkeypatch.setenv("CB_FAILURE_THRESHOLD", "1")
    from datetime import datetime, timezone

    from circuit_breaker import BREAKER_FORECAST, get_sync_breaker, reset_breakers_for_tests

    reset_breakers_for_tests()
    b = get_sync_breaker(BREAKER_FORECAST)
    b.acquire_upstream_slot(permit_probe=True)
    b.record_failure(count=True)

    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    redis.get.return_value = json.dumps(
        {
            "__atmosmind__": CACHE_ENVELOPE_VERSION,
            "fetched_at": ts,
            "data": {"temperature": 11.0, "condition": "Clear", "weather_code": 0},
        }
    ).encode()
    batch = MagicMock(return_value=[{"temperature": 99.0, "condition": "X", "weather_code": 0}])
    monkeypatch.setattr(api, "get_current_weather_batch_by_coords", batch)

    with patch.object(api, "enforce_rate_limit", return_value=None):
        resp = client.post(
            "/api/weather/batch",
            json={"cities": ["Test City"]},
            headers={"X-AtmosMind-Refresh": "1"},
        )
    assert resp.status_code == 200
    assert resp.json()["results"][0]["temperature"] == 11.0
    batch.assert_not_called()
    reset_breakers_for_tests()
