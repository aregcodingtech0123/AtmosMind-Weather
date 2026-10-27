"""Tests for in-process resilience counters."""
from __future__ import annotations

from metrics import (
    record_cache_hit,
    record_cache_miss,
    record_cache_unavailable,
    record_upstream_429_attempt,
    record_upstream_429_request,
    record_upstream_5xx_attempt,
    reset_counters_for_tests,
    snapshot,
)


def test_snapshot_hit_rate_and_schema():
    reset_counters_for_tests()
    record_cache_hit()
    record_cache_hit()
    record_cache_miss()
    record_cache_unavailable()
    record_upstream_429_attempt()
    record_upstream_429_attempt()
    record_upstream_429_request()
    record_upstream_5xx_attempt()

    body = snapshot()
    assert body["scope"] == "process"
    assert body["cache"]["hits"] == 2
    assert body["cache"]["misses"] == 1
    assert body["cache"]["hit_rate"] == round(2 / 3, 4)
    assert body["cache"]["unavailable"] == 1
    assert body["cache"]["buckets"] == ["weather", "aq"]
    assert body["cache"]["excludes"] == ["autocomplete"]
    assert body["upstream"]["429_total"] == 2
    assert body["upstream"]["429_requests_total"] == 1
    assert body["upstream"]["5xx_total"] == 1
    assert "uptime_seconds" in body
    assert "detail_dual_call_eliminated" in body
    assert "flags" in body
