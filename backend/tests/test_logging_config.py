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
