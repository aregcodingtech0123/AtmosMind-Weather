"""Tests for Loguru logging bootstrap."""
from __future__ import annotations

import logging

from logging_config import setup_logging


def test_setup_logging_intercepts_stdlib_logger():
    setup_logging()
    logger = logging.getLogger("test.logging_config")
    logger.warning("stdlib warning smoke test")


def test_log_outbound_api_smoke():
    from logging_config import log_outbound_api

    setup_logging()
    log_outbound_api(
        "open-meteo-forecast",
        success=False,
        latency_ms=120.5,
        lat=41.0,
        lon=29.0,
        status_code=429,
        error="rate_limited",
    )


def test_resilience_event_emitters_smoke():
    from logging_config import (
        log_cache_event,
        log_detail_lifestyle_shared_payload,
        log_upstream_status_event,
    )

    setup_logging()
    log_cache_event(
        "cache_hit", cache="weather", cache_kind="weather_current", lat=41.0, lon=29.0
    )
    log_cache_event("cache_miss", cache="aq", cache_kind="air_quality", lat=41.0, lon=29.0)
    log_upstream_status_event(
        "upstream_429",
        service="open-meteo-forecast",
        status_code=429,
        attempt=1,
        locations=10,
    )
    log_upstream_status_event(
        "upstream_5xx",
        service="open-meteo-forecast-detail",
        status_code=503,
        attempt=2,
    )
    # Placeholder emitter for Phase 0a (not wired to weather_detail yet).
    log_detail_lifestyle_shared_payload(latitude=41.0, longitude=29.0, shared=True)
