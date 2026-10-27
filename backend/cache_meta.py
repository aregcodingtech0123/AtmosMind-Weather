"""Cache freshness classification for Phase 2 SWR."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class DataStatus(str, Enum):
    FRESH = "fresh"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


class ResponseMeta(BaseModel):
    data_status: Literal["fresh", "stale", "unavailable"]
    fetched_at: str | None = Field(
        default=None,
        description="UTC ISO8601 with Z suffix; omitted for legacy-stale or unavailable",
    )


@dataclass(frozen=True)
class CacheMeta:
    data_status: DataStatus
    fetched_at: str | None
    is_legacy_bare_dict: bool = False

    def to_response_meta(self) -> ResponseMeta:
        if self.data_status == DataStatus.UNAVAILABLE:
            return ResponseMeta(data_status="unavailable", fetched_at=None)
        if self.is_legacy_bare_dict and self.data_status == DataStatus.STALE:
            return ResponseMeta(data_status="stale", fetched_at=None)
        return ResponseMeta(
            data_status=self.data_status.value,
            fetched_at=self.fetched_at,
        )


def parse_fetched_at_utc(iso_z: str | None) -> datetime | None:
    if not iso_z:
        return None
    try:
        text = iso_z.replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def classify_fetched_at(
    fetched_at: str | None,
    *,
    soft_ttl_seconds: int,
    hard_ttl_seconds: int,
    now: datetime | None = None,
) -> DataStatus:
    if fetched_at is None:
        return DataStatus.STALE
    parsed = parse_fetched_at_utc(fetched_at)
    if parsed is None:
        return DataStatus.UNAVAILABLE
    now_utc = now or datetime.now(timezone.utc)
    age = (now_utc - parsed).total_seconds()
    if age < 0:
        return DataStatus.FRESH
    if age < soft_ttl_seconds:
        return DataStatus.FRESH
    if age < hard_ttl_seconds:
        return DataStatus.STALE
    return DataStatus.UNAVAILABLE
