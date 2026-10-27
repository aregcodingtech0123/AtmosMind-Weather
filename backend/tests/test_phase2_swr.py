"""Phase 2 SWR classification and batch behavior (flags on)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from cache_meta import DataStatus
from redis_cache import (
    CACHE_ENVELOPE_VERSION,
    get_cached_weather_with_meta,
    set_cached_weather,
    utc_fetched_at_now,
    _wrap_cache_envelope,
)


@pytest.fixture
def swr_on(monkeypatch):
    monkeypatch.setenv("ENABLE_STALE_WHILE_REVALIDATE", "true")
    monkeypatch.setenv("WEATHER_SOFT_TTL_SECONDS", "1800")
    monkeypatch.setenv("WEATHER_HARD_TTL_SECONDS", "7200")


def _envelope_with_age(seconds_ago: float, inner: dict) -> dict:
    ts = datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)
    iso = ts.isoformat().replace("+00:00", "Z")
    return {
        "__atmosmind__": CACHE_ENVELOPE_VERSION,
        "fetched_at": iso,
        "data": inner,
    }


def test_stale_envelope_classified(swr_on):
    inner = {"temperature": 10.0, "condition": "Cloudy", "weather_code": 3}
    raw = json.dumps(_envelope_with_age(2000, inner))
    client = MagicMock()
    client.get.return_value = raw
    payload, meta = get_cached_weather_with_meta(client, 41.0, 29.0)
    assert payload == inner
    assert meta.data_status == DataStatus.STALE


def test_past_hard_ttl_unavailable(swr_on):
    inner = {"temperature": 10.0}
    raw = json.dumps(_envelope_with_age(8000, inner))
    client = MagicMock()
    client.get.return_value = raw
    payload, meta = get_cached_weather_with_meta(client, 41.0, 29.0)
    assert payload is None
    assert meta.data_status == DataStatus.UNAVAILABLE


def test_legacy_bare_dict_is_stale(swr_on):
    inner = {"temperature": 5.0, "condition": "Clear", "weather_code": 0}
    client = MagicMock()
    client.get.return_value = json.dumps(inner)
    payload, meta = get_cached_weather_with_meta(client, 41.0, 29.0)
    assert payload == inner
    assert meta.data_status == DataStatus.STALE
    assert meta.is_legacy_bare_dict


def test_batch_upstream_unavailable_item(swr_on):
    from api import _batch_item_unavailable

    item = _batch_item_unavailable("London, UK")
    assert item.temperature is None
    assert item.error == "upstream_unavailable"
    assert item.meta is not None
    assert item.meta.data_status == "unavailable"
