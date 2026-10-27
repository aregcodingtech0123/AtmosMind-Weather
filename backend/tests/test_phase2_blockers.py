"""Phase 2 blocker coverage: CB FSM, concurrency, TTL, endpoints, prewarm."""
from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import api
from circuit_breaker import BREAKER_FORECAST, get_sync_breaker, reset_breakers_for_tests
from redis_cache import CACHE_ENVELOPE_VERSION, set_cached_weather


@pytest.fixture(autouse=True)
def _reset_cb():
    reset_breakers_for_tests()
    yield
    reset_breakers_for_tests()


# ─── CB state transitions ─────────────────────────────────────────────────────


def test_cb_closed_to_open_at_threshold(monkeypatch):
    monkeypatch.setenv("CB_FAILURE_THRESHOLD", "3")
    b = get_sync_breaker(BREAKER_FORECAST)
    for _ in range(3):
        assert b.acquire_upstream_slot(permit_probe=True)
        b.record_failure(count=True)
    assert not b.acquire_upstream_slot(permit_probe=True)


def test_cb_open_to_half_open_after_open_seconds(monkeypatch):
    monkeypatch.setenv("CB_FAILURE_THRESHOLD", "1")
    monkeypatch.setenv("CB_OPEN_SECONDS", "60")
    b = get_sync_breaker(BREAKER_FORECAST)
    b.acquire_upstream_slot(permit_probe=True)
    b.record_failure(count=True)
    assert not b.acquire_upstream_slot(permit_probe=True)
    b._opened_at = time.monotonic() - 61
    assert b.acquire_upstream_slot(permit_probe=True)


def test_cb_half_open_to_closed_on_probe_success(monkeypatch):
    monkeypatch.setenv("CB_FAILURE_THRESHOLD", "1")
    b = get_sync_breaker(BREAKER_FORECAST)
    b.acquire_upstream_slot(permit_probe=True)
    b.record_failure(count=True)
    b._opened_at = time.monotonic() - 61
    assert b.acquire_upstream_slot(permit_probe=True)
    b.record_success()
    assert b.acquire_upstream_slot(permit_probe=True)


def test_cb_half_open_to_open_on_probe_failure(monkeypatch):
    monkeypatch.setenv("CB_FAILURE_THRESHOLD", "1")
    b = get_sync_breaker(BREAKER_FORECAST)
    b.acquire_upstream_slot(permit_probe=True)
    b.record_failure(count=True)
    b._opened_at = time.monotonic() - 61
    assert b.acquire_upstream_slot(permit_probe=True)
    b.record_failure(count=True)
    assert not b.acquire_upstream_slot(permit_probe=True)


def test_half_open_concurrent_deferred_return_immediately(monkeypatch):
    monkeypatch.setenv("CB_FAILURE_THRESHOLD", "1")
    monkeypatch.setenv("CB_OPEN_SECONDS", "60")
    b = get_sync_breaker(BREAKER_FORECAST)
    b.acquire_upstream_slot(permit_probe=True)
    b.record_failure(count=True)
    b._opened_at = time.monotonic() - 61
    assert b.acquire_upstream_slot(permit_probe=True)

    barrier = threading.Event()

    def slow_probe():
        time.sleep(0.3)
        b.record_success()
        barrier.set()

    threading.Thread(target=slow_probe).start()

    def try_acquire():
        t0 = time.perf_counter()
        ok = b.acquire_upstream_slot(permit_probe=True)
        return ok, time.perf_counter() - t0

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(try_acquire) for _ in range(10)]
        results = [f.result() for f in as_completed(futures)]

    deferred = [elapsed for ok, elapsed in results if not ok]
    assert len(deferred) >= 8
    assert max(deferred) < 0.05
    barrier.wait(timeout=1)


# ─── TTL setex ────────────────────────────────────────────────────────────────


def test_swr_on_setex_uses_hard_ttl(monkeypatch):
    monkeypatch.setenv("ENABLE_STALE_WHILE_REVALIDATE", "true")
    monkeypatch.setenv("WEATHER_HARD_TTL_SECONDS", "100")
    client = MagicMock()
    set_cached_weather(client, 1.0, 2.0, {"temperature": 1})
    assert client.setex.call_args[0][1] == 100


def test_swr_off_setex_uses_phase1_ttl(monkeypatch):
    monkeypatch.delenv("ENABLE_STALE_WHILE_REVALIDATE", raising=False)
    monkeypatch.setenv("WEATHER_TTL_SECONDS", "200")
    client = MagicMock()
    set_cached_weather(client, 1.0, 2.0, {"temperature": 1})
    assert client.setex.call_args[0][1] == 200


# ─── Legacy bare dict → envelope on upstream success (batch path) ─────────────


def test_legacy_bare_dict_upstream_success_writes_envelope(monkeypatch):
    monkeypatch.setenv("ENABLE_STALE_WHILE_REVALIDATE", "true")
    redis = MagicMock()
    inner = {"temperature": 7.0, "condition": "Clear", "weather_code": 0}
    redis.get.return_value = json.dumps(inner).encode()
    monkeypatch.setattr(api, "_get_redis", lambda: redis)
    monkeypatch.setattr(api, "_resolve_coords", lambda _c: (41.0, 29.0))
    monkeypatch.setattr(
        api,
        "get_current_weather_batch_by_coords",
        lambda coords, **kw: [
            {"temperature": 8.0, "condition": "Rain", "weather_code": 61},
        ],
    )

    client = TestClient(api.app)
    monkeypatch.setattr(api, "fetch_popular_for_redis", lambda *a, **k: [])
    monkeypatch.setattr(api, "init_schema", lambda c: None)
    monkeypatch.setattr(api, "get_connection", lambda: MagicMock())

    with patch.object(api, "enforce_rate_limit", return_value=None):
        resp = client.post("/api/weather/batch", json={"cities": ["Test City"]})
    assert resp.status_code == 200
    stored = json.loads(redis.setex.call_args[0][2])
    assert stored.get("__atmosmind__") == CACHE_ENVELOPE_VERSION


# ─── Prewarm + CB ─────────────────────────────────────────────────────────────


def test_prewarm_skips_upstream_when_cb_open(monkeypatch):
    monkeypatch.setenv("ENABLE_CIRCUIT_BREAKER", "true")
    monkeypatch.setenv("CB_FAILURE_THRESHOLD", "1")
    b = get_sync_breaker(BREAKER_FORECAST)
    b.acquire_upstream_slot(permit_probe=True)
    b.record_failure(count=True)

    redis = MagicMock()
    redis.get.return_value = None
    monkeypatch.setattr(api, "_get_redis", lambda: redis)
    batch = MagicMock()
    monkeypatch.setattr(api, "get_current_weather_batch_by_coords", batch)

    api._prewarm_weather_cache(
        [{"name": "A", "latitude": 1.0, "longitude": 2.0, "country": "X"}]
    )
    batch.assert_not_called()


# ─── Per-endpoint CB open + empty cache ───────────────────────────────────────


@pytest.fixture
def ep_client(monkeypatch):
    monkeypatch.setenv("ENABLE_STALE_WHILE_REVALIDATE", "true")
    monkeypatch.setenv("ENABLE_CIRCUIT_BREAKER", "true")
    redis = MagicMock()
    redis.get.return_value = None
    monkeypatch.setattr(api, "_get_redis", lambda: redis)
    monkeypatch.setattr(api, "fetch_popular_for_redis", lambda *a, **k: [])
    monkeypatch.setattr(api, "init_schema", lambda c: None)
    monkeypatch.setattr(api, "get_connection", lambda: MagicMock())
    monkeypatch.setattr(api, "_resolve_coords", lambda _c: (41.0, 29.0))
    monkeypatch.setattr(api, "get_city_advice", lambda *a, **k: "advice")
    b = get_sync_breaker(BREAKER_FORECAST)
    b.acquire_upstream_slot(permit_probe=True)
    b.record_failure(count=True)
    with TestClient(api.app) as c:
        yield c


def test_batch_cb_open_empty_cache_item(ep_client, monkeypatch):
    monkeypatch.setattr(
        api,
        "get_current_weather_batch_by_coords",
        lambda *a, **k: [{"error": "upstream_unavailable"}],
    )
    with patch.object(api, "enforce_rate_limit", return_value=None):
        resp = ep_client.post("/api/weather/batch", json={"cities": ["City, X"]})
    item = resp.json()["results"][0]
    assert resp.status_code == 200
    assert item["temperature"] is None
    assert item["error"] == "upstream_unavailable"
    assert item["meta"]["data_status"] == "unavailable"


def test_detail_cb_open_empty_cache_503(ep_client, monkeypatch):
    monkeypatch.setattr(
        api,
        "fetch_weather_detail",
        MagicMock(side_effect=__import__("weather_detail", fromlist=["ForecastUnavailableError"]).ForecastUnavailableError("x")),
    )
    with patch.object(api, "enforce_rate_limit", return_value=None):
        resp = ep_client.post(
            "/api/weather/detail",
            json={"latitude": 41.0, "longitude": 29.0, "language": "en", "unit": "metric"},
        )
    assert resp.status_code == 503


def test_lifestyle_cb_open_empty_meta_unavailable(ep_client, monkeypatch):
    async def _fake_fetch(*a, **k):
        from lifestyle_indices import LifestyleIndicesResponse

        return LifestyleIndicesResponse(
            latitude=41.0,
            longitude=29.0,
            meta=__import__("cache_meta", fromlist=["ResponseMeta"]).ResponseMeta(
                data_status="unavailable"
            ),
        )

    monkeypatch.setattr(api, "fetch_lifestyle_indices", _fake_fetch)
    with patch.object(api, "enforce_rate_limit", return_value=None):
        resp = ep_client.get("/api/lifestyle-indices?latitude=41&longitude=29")
    assert resp.status_code == 200
    assert resp.json()["meta"]["data_status"] == "unavailable"


def test_ai_cb_open_503(ep_client, monkeypatch):
    monkeypatch.setattr(
        "ai_fresh_context.get_current_weather_by_coords",
        lambda *a, **k: {"error": "upstream_unavailable"},
    )
    with patch.object(api, "enforce_rate_limit", return_value=None):
        resp = ep_client.post(
            "/api/get-city-advice",
            json={
                "city": "Istanbul",
                "weather_summary": "x",
                "language": "en",
                "unit": "metric",
            },
        )
    assert resp.status_code == 503
    assert resp.json()["detail"]["error"] == "data_unavailable"
