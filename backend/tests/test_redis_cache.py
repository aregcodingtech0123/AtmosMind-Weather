"""Tests for Redis weather/AQ cache getters and Phase 0b instrumentation."""
from __future__ import annotations

import json
import re
from unittest.mock import MagicMock

import pytest

from metrics import reset_counters_for_tests
from redis_cache import (
    CACHE_ENVELOPE_VERSION,
    get_air_quality_ttl,
    get_cached_air_quality,
    get_cached_weather,
    get_cached_weather_by_city,
    get_cached_weather_detail,
    get_weather_detail_ttl,
    get_weather_ttl,
    set_cached_air_quality,
    set_cached_weather,
    set_cached_weather_detail,
    utc_fetched_at_now,
)


@pytest.fixture
def cache_events(monkeypatch):
    reset_counters_for_tests()
    events: list[tuple] = []

    def _spy(event, *, cache, cache_kind, lat=None, lon=None, **extra):
        events.append(
            {
                "event": event,
                "cache": cache,
                "cache_kind": cache_kind,
                "lat": lat,
                "lon": lon,
                **extra,
            }
        )

    def _unavailable(**kwargs):
        events.append({"event": "cache_unavailable", **kwargs})

    monkeypatch.setattr("redis_cache.log_cache_event", _spy)
    monkeypatch.setattr("redis_cache.log_cache_unavailable", _unavailable)
    return events


def _redis_with_raw(raw):
    client = MagicMock()
    client.get.return_value = raw
    return client


# ─── get_cached_weather ───────────────────────────────────────────────────────


def test_get_cached_weather_miss_when_raw_none(cache_events):
    result = get_cached_weather(_redis_with_raw(None), 41.0, 29.0)
    assert result is None
    assert len(cache_events) == 1
    assert cache_events[0]["event"] == "cache_miss"
    assert cache_events[0]["cache"] == "weather"
    assert cache_events[0]["cache_kind"] == "weather_current"


def test_get_cached_weather_hit_on_valid_json_dict(cache_events):
    payload = {"temperature": 18.5, "condition": "Clear", "weather_code": 0}
    result = get_cached_weather(_redis_with_raw(json.dumps(payload)), 41.0, 29.0)
    assert result == payload
    assert len(cache_events) == 1
    assert cache_events[0]["event"] == "cache_hit"
    assert cache_events[0]["cache"] == "weather"
    assert cache_events[0]["cache_kind"] == "weather_current"


def test_get_cached_weather_malformed_json_is_miss_not_raise(cache_events):
    result = get_cached_weather(_redis_with_raw("not-json{{{"), 41.0, 29.0)
    assert result is None
    assert len(cache_events) == 1
    assert cache_events[0]["event"] == "cache_miss"


def test_get_cached_weather_redis_raise_returns_none_cache_unavailable(cache_events):
    client = MagicMock()
    client.get.side_effect = ConnectionError("redis down")
    result = get_cached_weather(client, 41.0, 29.0)
    assert result is None
    assert len(cache_events) == 1
    assert cache_events[0]["event"] == "cache_unavailable"
    assert cache_events[0]["cache_kind"] == "weather_current"


# ─── get_cached_weather_detail ────────────────────────────────────────────────


def test_get_cached_weather_detail_miss_when_raw_none(cache_events):
    result = get_cached_weather_detail(_redis_with_raw(None), 41.0, 29.0, "en", "metric")
    assert result is None
    assert len(cache_events) == 1
    assert cache_events[0]["event"] == "cache_miss"
    assert cache_events[0]["cache_kind"] == "weather_detail"


def test_get_cached_weather_detail_hit_on_valid_json_dict(cache_events):
    payload = {"latitude": 41.0, "longitude": 29.0, "weather": {}, "lifestyle_indices": {}}
    result = get_cached_weather_detail(
        _redis_with_raw(json.dumps(payload)), 41.0, 29.0, "en", "metric"
    )
    assert result == payload
    assert cache_events[0]["event"] == "cache_hit"
    assert cache_events[0]["cache"] == "weather"
    assert cache_events[0]["cache_kind"] == "weather_detail"


def test_get_cached_weather_detail_malformed_json_is_miss_not_raise(cache_events):
    result = get_cached_weather_detail(
        _redis_with_raw(b"{bad"), 41.0, 29.0, "en", "metric"
    )
    assert result is None
    assert cache_events[0]["event"] == "cache_miss"


def test_get_cached_weather_detail_redis_raise_returns_none_cache_unavailable(cache_events):
    client = MagicMock()
    client.get.side_effect = TimeoutError("redis timeout")
    result = get_cached_weather_detail(client, 41.0, 29.0, "en", "metric")
    assert result is None
    assert cache_events[0]["event"] == "cache_unavailable"


# ─── get_cached_weather_by_city ─────────────────────────────────────────────────


def test_get_cached_weather_by_city_miss_when_raw_none(cache_events):
    result = get_cached_weather_by_city(_redis_with_raw(None), "London, United Kingdom")
    assert result is None
    assert cache_events[0]["event"] == "cache_miss"
    assert cache_events[0]["cache_kind"] == "weather_city"


def test_get_cached_weather_by_city_hit_on_valid_json_dict(cache_events):
    payload = {"temperature": 12.0, "condition": "Rain", "weather_code": 61}
    result = get_cached_weather_by_city(
        _redis_with_raw(json.dumps(payload)), "London, United Kingdom"
    )
    assert result == payload
    assert cache_events[0]["event"] == "cache_hit"


def test_get_cached_weather_by_city_malformed_json_is_miss_not_raise(cache_events):
    result = get_cached_weather_by_city(_redis_with_raw("{"), "London, United Kingdom")
    assert result is None
    assert cache_events[0]["event"] == "cache_miss"


def test_get_cached_weather_by_city_redis_raise_returns_none_cache_unavailable(cache_events):
    client = MagicMock()
    client.get.side_effect = ConnectionError("redis down")
    result = get_cached_weather_by_city(client, "London, United Kingdom")
    assert result is None
    assert cache_events[0]["event"] == "cache_unavailable"


# ─── get_cached_air_quality ───────────────────────────────────────────────────


def test_get_cached_air_quality_miss_when_raw_none(cache_events):
    result = get_cached_air_quality(_redis_with_raw(None), 41.0, 29.0)
    assert result is None
    assert cache_events[0]["event"] == "cache_miss"
    assert cache_events[0]["cache"] == "aq"
    assert cache_events[0]["cache_kind"] == "air_quality"


def test_get_cached_air_quality_hit_on_valid_json_dict(cache_events):
    payload = {"hourly": {"european_aqi": [20]}}
    result = get_cached_air_quality(_redis_with_raw(json.dumps(payload)), 41.0, 29.0)
    assert result == payload
    assert cache_events[0]["event"] == "cache_hit"
    assert cache_events[0]["cache"] == "aq"


def test_get_cached_air_quality_malformed_json_is_miss_not_raise(cache_events):
    result = get_cached_air_quality(_redis_with_raw("["), 41.0, 29.0)
    assert result is None
    assert cache_events[0]["event"] == "cache_miss"


def test_get_cached_air_quality_redis_raise_returns_none_cache_unavailable(cache_events):
    client = MagicMock()
    client.get.side_effect = OSError("broken pipe")
    result = get_cached_air_quality(client, 41.0, 29.0)
    assert result is None
    assert cache_events[0]["event"] == "cache_unavailable"


# ─── Phase 1: TTL getters, envelope write/read ───────────────────────────────


def test_get_weather_ttl_reads_env(monkeypatch):
    monkeypatch.setenv("WEATHER_TTL_SECONDS", "1800")
    assert get_weather_ttl() == 1800


def test_get_weather_ttl_defaults_to_900_when_env_unset(monkeypatch):
    monkeypatch.delenv("WEATHER_TTL_SECONDS", raising=False)
    assert get_weather_ttl() == 900


def test_get_weather_detail_and_air_quality_ttl(monkeypatch):
    monkeypatch.setenv("WEATHER_DETAIL_TTL_SECONDS", "1800")
    monkeypatch.setenv("AIR_QUALITY_TTL_SECONDS", "3600")
    assert get_weather_detail_ttl() == 1800
    assert get_air_quality_ttl() == 3600


def test_utc_fetched_at_now_ends_with_z_and_has_millisecond_precision():
    ts = utc_fetched_at_now()
    assert ts.endswith("Z")
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z$", ts)


def test_set_cached_weather_setex_ttl_from_env(monkeypatch):
    monkeypatch.setenv("WEATHER_TTL_SECONDS", "1800")
    client = MagicMock()
    set_cached_weather(client, 41.0, 29.0, {"temperature": 1})
    client.setex.assert_called_once()
    assert client.setex.call_args[0][1] == 1800


def test_set_cached_weather_setex_ttl_900_when_env_unset(monkeypatch):
    monkeypatch.delenv("WEATHER_TTL_SECONDS", raising=False)
    client = MagicMock()
    set_cached_weather(client, 41.0, 29.0, {"temperature": 1})
    assert client.setex.call_args[0][1] == 900


def test_set_cached_weather_writes_envelope(monkeypatch):
    monkeypatch.setattr(
        "redis_cache.utc_fetched_at_now", lambda: "2026-10-28T12:34:56.789012Z"
    )
    client = MagicMock()
    inner = {"temperature": 18.5, "condition": "Clear", "weather_code": 0}
    set_cached_weather(client, 41.0, 29.0, inner)
    stored = json.loads(client.setex.call_args[0][2])
    assert stored["__atmosmind__"] == CACHE_ENVELOPE_VERSION
    assert stored["fetched_at"] == "2026-10-28T12:34:56.789012Z"
    assert stored["data"] == inner


def test_get_cached_weather_hit_on_envelope(cache_events):
    inner = {"temperature": 18.5, "condition": "Clear", "weather_code": 0}
    wrapped = {
        "__atmosmind__": CACHE_ENVELOPE_VERSION,
        "fetched_at": "2026-10-28T12:34:56.789012Z",
        "data": inner,
    }
    result = get_cached_weather(_redis_with_raw(json.dumps(wrapped)), 41.0, 29.0)
    assert result == inner
    assert cache_events[0]["event"] == "cache_hit"


def test_get_cached_weather_envelope_non_dict_data_is_miss(cache_events):
    wrapped = {
        "__atmosmind__": CACHE_ENVELOPE_VERSION,
        "fetched_at": "2026-10-28T12:34:56.789012Z",
        "data": ["not", "a", "dict"],
    }
    result = get_cached_weather(_redis_with_raw(json.dumps(wrapped)), 41.0, 29.0)
    assert result is None
    assert cache_events[0]["event"] == "cache_miss"
    assert cache_events[0]["cache_kind"] == "weather_current"


def test_set_cached_weather_detail_and_air_quality_use_respective_ttl(monkeypatch):
    monkeypatch.setenv("WEATHER_DETAIL_TTL_SECONDS", "1800")
    monkeypatch.setenv("AIR_QUALITY_TTL_SECONDS", "3600")
    detail_client = MagicMock()
    aq_client = MagicMock()
    set_cached_weather_detail(detail_client, 1.0, 2.0, "en", "metric", {"x": 1})
    set_cached_air_quality(aq_client, 1.0, 2.0, {"hourly": {}})
    assert detail_client.setex.call_args[0][1] == 1800
    assert aq_client.setex.call_args[0][1] == 3600
