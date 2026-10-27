# Phase 2 — SWR + circuit breaker (design, approved)

## TTL env (SOFT / HARD only when SWR on)

| Kind | Soft (freshness) | Hard (Redis SETEX) |
|------|------------------|-------------------|
| Weather | `WEATHER_SOFT_TTL_SECONDS=1800` | `WEATHER_HARD_TTL_SECONDS=7200` |
| Detail | `WEATHER_DETAIL_SOFT_TTL_SECONDS=1800` | `WEATHER_DETAIL_HARD_TTL_SECONDS=7200` |
| Air quality | `AIR_QUALITY_SOFT_TTL_SECONDS=3600` | `AIR_QUALITY_HARD_TTL_SECONDS=21600` |

Phase 1 vars `WEATHER_TTL_SECONDS`, `WEATHER_DETAIL_TTL_SECONDS`, `AIR_QUALITY_TTL_SECONDS` are used when `ENABLE_STALE_WHILE_REVALIDATE=false`. When SWR is on they are **ignored**; startup logs **WARNING** if both old and new vars are set.

## Legacy bare dict + SWR on

Bare dict (no envelope): treat as **stale**, `fetched_at=null`. Try upstream; on success write envelope. On failure serve bare dict with `data_status=stale`, omit `fetched_at` in meta. Removable after one HARD_TTL window of envelope writes.

## Prewarm + CB

- Prewarm failures **do not** count toward CB threshold.
- If forecast CB is **open**, prewarm **skips** upstream and exits early.
- Prewarm **never** takes half-open probes (`permit_probe=False`).

## Half-open concurrency

Single probe via `threading.Lock`. First request probes; concurrent requests **defer** upstream (serve stale if present, else unavailable). Probe success → closed; failure → open.

## CB open + empty cache

| Route | Behavior |
|-------|----------|
| `POST /api/weather/batch` | HTTP 200, per-item `temperature: null`, `error: upstream_unavailable`, `meta.data_status=unavailable` |
| `POST /api/weather/detail` | HTTP 503 |
| `GET /api/lifestyle-indices` | HTTP 200, null AQ fields, `meta.data_status=unavailable` |
| AI routes | HTTP 503 `{"error":"data_unavailable","retry_after_seconds":N}` |

## `/api/lifestyle-indices` SWR

AQ portion only (AQ Redis cache). Forecast slice (visibility/dew) has no cache — fresh-or-fail; forecast fail → AQ-only with forecast fields null (today’s degradation).

## Flags

`ENABLE_STALE_WHILE_REVALIDATE`, `ENABLE_CIRCUIT_BREAKER` (default false). Off → Phase 1 behavior.

## Non-goals

Provider failover (4), retry/backoff (3), frontend (6), background refresh (3).
