"""
Process-local circuit breakers for Open-Meteo forecast (sync) and air quality (async).

Half-open: one probe at a time. Deferred callers return immediately (no wait for probe).

- Forecast (``open_meteo_client`` / requests): ``SyncCircuitBreaker`` + ``threading.Lock``
- Air quality (``lifestyle_indices`` / httpx async): ``AsyncCircuitBreaker`` + ``asyncio.Lock``

Concurrent requests during half-open probing get ``acquire_*`` = False immediately and
serve stale or unavailable per endpoint rules; they are not queued and are not retried
when the probe succeeds — the next request after CB closes may fetch fresh data.
"""
from __future__ import annotations

import asyncio
import os
import threading
import time
from collections import deque
from typing import Any, Literal

_SYNC_BREAKERS: dict[str, "SyncCircuitBreaker"] = {}
_ASYNC_BREAKERS: dict[str, "AsyncCircuitBreaker"] = {}
_REGISTRY_LOCK = threading.Lock()


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _threshold() -> int:
    return int(os.getenv("CB_FAILURE_THRESHOLD", "5"))


def _window_seconds() -> float:
    return float(_env_int("CB_WINDOW_SECONDS", 60))


def _open_seconds() -> float:
    return float(_env_int("CB_OPEN_SECONDS", 60))


BREAKER_FORECAST = "open_meteo_forecast"
BREAKER_AIR_QUALITY = "open_meteo_air_quality"


class _BreakerCore:
    def __init__(self, name: str) -> None:
        self.name = name
        self._state: Literal["closed", "open", "half_open"] = "closed"
        self._failure_times: deque[float] = deque()
        self._opened_at: float = 0.0
        self._probing = False

    def _prune_failures(self, now: float) -> None:
        cutoff = now - _window_seconds()
        while self._failure_times and self._failure_times[0] < cutoff:
            self._failure_times.popleft()

    def _maybe_advance_from_open(self, now: float) -> None:
        if self._state == "open" and now - self._opened_at >= _open_seconds():
            self._state = "half_open"
            self._probing = False

    def _snapshot_unlocked(self, now: float) -> dict[str, Any]:
        self._maybe_advance_from_open(now)
        return {
            "name": self.name,
            "state": self._state if not self._probing else "half_open_probing",
            "failures_in_window": len(self._failure_times),
            "opened_at": self._opened_at if self._state == "open" else None,
        }

    def _retry_after_unlocked(self, now: float) -> int:
        if self._state != "open":
            return 0
        remaining = _open_seconds() - (now - self._opened_at)
        return max(1, int(remaining) if remaining > 0 else _env_int("CB_OPEN_SECONDS", 60))

    def _record_success_unlocked(self) -> None:
        self._state = "closed"
        self._failure_times.clear()
        self._probing = False

    def _record_failure_unlocked(self, *, count: bool, now: float) -> None:
        if count:
            self._prune_failures(now)
            self._failure_times.append(now)
            if len(self._failure_times) >= _threshold():
                self._state = "open"
                self._opened_at = now
            elif self._state == "half_open":
                self._state = "open"
                self._opened_at = now
        elif self._state == "half_open":
            self._state = "open"
            self._opened_at = now
        self._probing = False


class SyncCircuitBreaker(_BreakerCore):
    """Sync upstream paths (requests in open_meteo_client)."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._lock = threading.Lock()
        self._probe_lock = threading.Lock()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self._snapshot_unlocked(time.monotonic())

    def is_open_for_background(self) -> bool:
        with self._lock:
            now = time.monotonic()
            self._maybe_advance_from_open(now)
            return self._state == "open"

    def retry_after_seconds(self) -> int:
        with self._lock:
            return self._retry_after_unlocked(time.monotonic())

    def acquire_upstream_slot(self, *, permit_probe: bool) -> bool:
        with self._lock:
            now = time.monotonic()
            self._prune_failures(now)
            self._maybe_advance_from_open(now)

            if self._state == "closed":
                return True
            if self._state == "open":
                return False
            if not permit_probe or self._probing:
                return False
            if not self._probe_lock.acquire(blocking=False):
                return False
            self._probing = True
            return True

    def _release_probe(self) -> None:
        if self._probe_lock.locked():
            self._probe_lock.release()

    def record_success(self) -> None:
        with self._lock:
            self._record_success_unlocked()
        self._release_probe()

    def record_failure(self, *, count: bool) -> None:
        with self._lock:
            self._record_failure_unlocked(count=count, now=time.monotonic())
        self._release_probe()


class AsyncCircuitBreaker(_BreakerCore):
    """Async upstream paths (httpx in lifestyle_indices) — never blocks the event loop on probe."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._lock = asyncio.Lock()

    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            return self._snapshot_unlocked(time.monotonic())

    async def is_open_for_background(self) -> bool:
        async with self._lock:
            now = time.monotonic()
            self._maybe_advance_from_open(now)
            return self._state == "open"

    async def retry_after_seconds(self) -> int:
        async with self._lock:
            return self._retry_after_unlocked(time.monotonic())

    async def acquire_upstream_slot(self, *, permit_probe: bool) -> bool:
        async with self._lock:
            now = time.monotonic()
            self._prune_failures(now)
            self._maybe_advance_from_open(now)

            if self._state == "closed":
                return True
            if self._state == "open":
                return False
            if not permit_probe or self._probing:
                return False
            self._probing = True
            return True

    async def record_success(self) -> None:
        async with self._lock:
            self._record_success_unlocked()

    async def record_failure(self, *, count: bool) -> None:
        async with self._lock:
            self._record_failure_unlocked(count=count, now=time.monotonic())


# Backward-compatible alias
CircuitBreaker = SyncCircuitBreaker


def get_sync_breaker(name: str) -> SyncCircuitBreaker:
    with _REGISTRY_LOCK:
        if name not in _SYNC_BREAKERS:
            _SYNC_BREAKERS[name] = SyncCircuitBreaker(name)
        return _SYNC_BREAKERS[name]


def get_async_breaker(name: str) -> AsyncCircuitBreaker:
    with _REGISTRY_LOCK:
        if name not in _ASYNC_BREAKERS:
            _ASYNC_BREAKERS[name] = AsyncCircuitBreaker(name)
        return _ASYNC_BREAKERS[name]


def get_breaker(name: str) -> SyncCircuitBreaker:
    """Forecast breaker (sync)."""
    return get_sync_breaker(name)


def reset_breakers_for_tests() -> None:
    with _REGISTRY_LOCK:
        _SYNC_BREAKERS.clear()
        _ASYNC_BREAKERS.clear()


def forecast_breaker_snapshot() -> dict[str, Any]:
    return get_sync_breaker(BREAKER_FORECAST).snapshot()


def air_quality_breaker_snapshot() -> dict[str, Any]:
    """Best-effort sync snapshot for ops endpoint (async breaker; no event-loop block)."""
    breaker = _ASYNC_BREAKERS.get(BREAKER_AIR_QUALITY)
    if breaker is None:
        return {"name": BREAKER_AIR_QUALITY, "state": "closed", "failures_in_window": 0}
    return {
        "name": breaker.name,
        "state": breaker._state if not breaker._probing else "half_open_probing",
        "failures_in_window": len(breaker._failure_times),
        "opened_at": breaker._opened_at if breaker._state == "open" else None,
    }
