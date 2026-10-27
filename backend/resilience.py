"""SWR orchestration helpers and AI fresh-or-fail gate."""
from __future__ import annotations

from typing import Any

from cache_meta import CacheMeta, DataStatus, ResponseMeta
from circuit_breaker import BREAKER_FORECAST, get_sync_breaker
from metrics import is_circuit_breaker_enabled, is_stale_while_revalidate_enabled

UPSTREAM_UNAVAILABLE = "upstream_unavailable"


def swr_enabled() -> bool:
    return is_stale_while_revalidate_enabled()


def optional_response_meta(meta: CacheMeta | None) -> ResponseMeta | None:
    if not swr_enabled() or meta is None:
        return None
    return meta.to_response_meta()


def forecast_upstream_blocked() -> bool:
    if not is_circuit_breaker_enabled():
        return False
    return not get_sync_breaker(BREAKER_FORECAST).acquire_upstream_slot(permit_probe=True)


def forecast_retry_after_seconds() -> int:
    return get_sync_breaker(BREAKER_FORECAST).retry_after_seconds()


def ai_data_unavailable_body() -> dict[str, Any]:
    return {
        "error": "data_unavailable",
        "retry_after_seconds": forecast_retry_after_seconds()
        if is_circuit_breaker_enabled()
        else 60,
    }


def require_fresh_cache_meta(meta: CacheMeta) -> bool:
    """AI paths may use cache only when fresh."""
    return meta.data_status == DataStatus.FRESH
