"""
Process-local circuit breakers for Open-Meteo forecast and air quality.

Half-open allows a single concurrent probe (threading lock). Query APIs avoid
transition side effects where noted.
"""
from __future__ import annotations

import os
import threading
import time
from collections import deque
from typing import Any, Literal

_BREAKERS: dict[str, "CircuitBreaker"] = {}
_REGISTRY_LOCK = threading.Lock()


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _threshold() -> int:
    return _env_int("CB_FAILURE_THRESHOLD", 5)


def _window_seconds() -> float:
    return float(_env_int("CB_WINDOW_SECONDS", 60))


def _open_seconds() -> float:
    return float(_env_int("CB_OPEN_SECONDS", 60))


BREAKER_FORECAST = "open_meteo_forecast"
BREAKER_AIR_QUALITY = "open_meteo_air_quality"


class CircuitBreaker:
    def __init__(self, name: str) -> None:
        self.name = name
        self._lock = threading.Lock()
        self._probe_lock = threading.Lock()
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

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            now = time.monotonic()
            self._maybe_advance_from_open(now)
            return {
                "name": self.name,
                "state": self._state if not self._probing else "half_open_probing",
                "failures_in_window": len(self._failure_times),
                "opened_at": self._opened_at if self._state == "open" else None,
            }

    def is_open_for_background(self) -> bool:
        """Read-only: True if upstream should be skipped (open, not yet half-open)."""
        with self._lock:
            now = time.monotonic()
            self._maybe_advance_from_open(now)
            return self._state == "open"

    def retry_after_seconds(self) -> int:
        with self._lock:
            now = time.monotonic()
            if self._state != "open":
                return 0
            remaining = _open_seconds() - (now - self._opened_at)
            return max(1, int(remaining) if remaining > 0 else _env_int("CB_OPEN_SECONDS", 60))

    def acquire_upstream_slot(self, *, permit_probe: bool) -> bool:
        """
        True if caller may invoke upstream. Half-open: only one probe when permit_probe.
        """
        with self._lock:
            now = time.monotonic()
            self._prune_failures(now)
            self._maybe_advance_from_open(now)

            if self._state == "closed":
                return True

            if self._state == "open":
                return False

            # half_open
            if not permit_probe:
                return False
            if self._probing:
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
            self._state = "closed"
            self._failure_times.clear()
            self._probing = False
        self._release_probe()

    def record_failure(self, *, count: bool) -> None:
        with self._lock:
            now = time.monotonic()
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
        self._release_probe()


def get_breaker(name: str) -> CircuitBreaker:
    with _REGISTRY_LOCK:
        if name not in _BREAKERS:
            _BREAKERS[name] = CircuitBreaker(name)
        return _BREAKERS[name]


def reset_breakers_for_tests() -> None:
    with _REGISTRY_LOCK:
        _BREAKERS.clear()


def forecast_breaker_snapshot() -> dict[str, Any]:
    return get_breaker(BREAKER_FORECAST).snapshot()


def air_quality_breaker_snapshot() -> dict[str, Any]:
    return get_breaker(BREAKER_AIR_QUALITY).snapshot()
