"""
In-process resilience counters (stdlib only). Used by /api/_health/resilience when enabled.
"""
from __future__ import annotations

import os
import threading
import time
from typing import Any

_START_MONOTONIC = time.monotonic()
_LOCK = threading.Lock()

_CACHE_HIT_TOTAL = 0
_CACHE_MISS_TOTAL = 0
_CACHE_UNAVAILABLE_TOTAL = 0
_UPSTREAM_429_TOTAL = 0
_UPSTREAM_429_REQUESTS_TOTAL = 0
_UPSTREAM_5XX_TOTAL = 0


def _is_truthy_env(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def is_resilience_endpoint_enabled() -> bool:
    return _is_truthy_env("ENABLE_RESILIENCE_ENDPOINT", "false")


def is_weather_detail_share_forecast_enabled() -> bool:
    return _is_truthy_env("WEATHER_DETAIL_SHARE_FORECAST", "false")


def _safe_increment(counter_name: str) -> None:
    """Counters must never break cache getters or upstream fetches."""
    try:
        global _CACHE_HIT_TOTAL, _CACHE_MISS_TOTAL, _CACHE_UNAVAILABLE_TOTAL
        global _UPSTREAM_429_TOTAL, _UPSTREAM_429_REQUESTS_TOTAL, _UPSTREAM_5XX_TOTAL
        with _LOCK:
            if counter_name == "cache_hit":
                _CACHE_HIT_TOTAL += 1
            elif counter_name == "cache_miss":
                _CACHE_MISS_TOTAL += 1
            elif counter_name == "cache_unavailable":
                _CACHE_UNAVAILABLE_TOTAL += 1
            elif counter_name == "upstream_429":
                _UPSTREAM_429_TOTAL += 1
            elif counter_name == "upstream_429_request":
                _UPSTREAM_429_REQUESTS_TOTAL += 1
            elif counter_name == "upstream_5xx":
                _UPSTREAM_5XX_TOTAL += 1
    except Exception:
        pass


def record_cache_hit() -> None:
    _safe_increment("cache_hit")


def record_cache_miss() -> None:
    _safe_increment("cache_miss")


def record_cache_unavailable() -> None:
    _safe_increment("cache_unavailable")


def record_upstream_429_attempt() -> None:
    """Per HTTP attempt that received 429 (includes retries)."""
    _safe_increment("upstream_429")


def record_upstream_429_request() -> None:
    """Per logical outbound request that saw at least one 429 before finish."""
    _safe_increment("upstream_429_request")


def record_upstream_5xx_attempt() -> None:
    _safe_increment("upstream_5xx")


def reset_counters_for_tests() -> None:
    """Test helper: zero all counters."""
    global _CACHE_HIT_TOTAL, _CACHE_MISS_TOTAL, _CACHE_UNAVAILABLE_TOTAL
    global _UPSTREAM_429_TOTAL, _UPSTREAM_429_REQUESTS_TOTAL, _UPSTREAM_5XX_TOTAL
    with _LOCK:
        _CACHE_HIT_TOTAL = 0
        _CACHE_MISS_TOTAL = 0
        _CACHE_UNAVAILABLE_TOTAL = 0
        _UPSTREAM_429_TOTAL = 0
        _UPSTREAM_429_REQUESTS_TOTAL = 0
        _UPSTREAM_5XX_TOTAL = 0


def snapshot() -> dict[str, Any]:
    with _LOCK:
        hits = _CACHE_HIT_TOTAL
        misses = _CACHE_MISS_TOTAL
        unavailable = _CACHE_UNAVAILABLE_TOTAL
        upstream_429 = _UPSTREAM_429_TOTAL
        upstream_429_requests = _UPSTREAM_429_REQUESTS_TOTAL
        upstream_5xx = _UPSTREAM_5XX_TOTAL

    total_lookups = hits + misses
    hit_rate = round(hits / total_lookups, 4) if total_lookups > 0 else 0.0

    return {
        "scope": "process",
        "uptime_seconds": int(time.monotonic() - _START_MONOTONIC),
        "cache": {
            "hits": hits,
            "misses": misses,
            "hit_rate": hit_rate,
            "unavailable": unavailable,
            "buckets": ["weather", "aq"],
            "excludes": ["autocomplete"],
        },
        "upstream": {
            "429_total": upstream_429,
            "429_requests_total": upstream_429_requests,
            "5xx_total": upstream_5xx,
        },
        "detail_dual_call_eliminated": is_weather_detail_share_forecast_enabled(),
        "flags": {
            "ENABLE_RESILIENCE_ENDPOINT": is_resilience_endpoint_enabled(),
            "WEATHER_DETAIL_SHARE_FORECAST": is_weather_detail_share_forecast_enabled(),
        },
    }
