"""Circuit breaker state machine tests."""
from __future__ import annotations

import time

import pytest

from circuit_breaker import BREAKER_FORECAST, get_breaker, reset_breakers_for_tests


@pytest.fixture(autouse=True)
def _reset():
    reset_breakers_for_tests()
    yield
    reset_breakers_for_tests()


def test_opens_after_threshold_failures(monkeypatch):
    monkeypatch.setenv("CB_FAILURE_THRESHOLD", "3")
    monkeypatch.setenv("CB_WINDOW_SECONDS", "60")
    b = get_breaker(BREAKER_FORECAST)
    for _ in range(3):
        assert b.acquire_upstream_slot(permit_probe=True)
        b.record_failure(count=True)
    assert not b.acquire_upstream_slot(permit_probe=True)


def test_half_open_single_probe(monkeypatch):
    monkeypatch.setenv("CB_FAILURE_THRESHOLD", "1")
    monkeypatch.setenv("CB_OPEN_SECONDS", "60")
    b = get_breaker(BREAKER_FORECAST)
    assert b.acquire_upstream_slot(permit_probe=True)
    b.record_failure(count=True)
    assert not b.acquire_upstream_slot(permit_probe=True)

    b._opened_at = time.monotonic() - 61  # simulate open window elapsed
    assert b.acquire_upstream_slot(permit_probe=True)
    assert not b.acquire_upstream_slot(permit_probe=True)
    b.record_success()
    assert b.acquire_upstream_slot(permit_probe=True)
