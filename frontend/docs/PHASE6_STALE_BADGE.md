# Phase 6 — Frontend stale badge & unavailable UX (revised)

Backend contract: `meta: { data_status, fetched_at? }` on batch items, detail root, lifestyle root. AI: HTTP 503 `{"detail":{"error":"data_unavailable","retry_after_seconds":N}}`.

**Scope decision — Yenile (refresh): Option A.** Ship **`X-AtmosMind-Refresh: 1`** with Phase 6 **and** the Yenile button. Backend (Phase 2 branch) already bypasses soft-fresh cache on batch, detail, and lifestyle when header is set + SWR on; upstream still respects CB; success → fresh + new `fetched_at`; failure → normal stale path. Tests: `backend/tests/test_refresh_header.py`. **Do not** ship a button without this header.

---

## A. Scope

| Status | UI |
|--------|-----|
| `fresh` / no `meta` | Normal |
| `stale` | Values + `StaleBadge` (“Last updated HH:MM” local) |
| `unavailable` | Explicit copy + Yenile — not silent `—` |
| Client `loading` | Skeleton (not a backend status) |

## B. Files

| File | Change |
|------|--------|
| `frontend/src/services/api.ts` | `ResponseMeta`, batch/detail types; send `X-AtmosMind-Refresh` on Yenile; parse 503 `detail` |
| `frontend/src/utils/weatherDetailMapper.ts` | Map root `meta` only (see § Detail meta) |
| `frontend/src/types/weather.ts` | `DataStatus`, card/detail types |
| `frontend/src/App.tsx` | Cards, **localStorage migration** (§G), integration test hook |
| `frontend/src/hooks/useCityDetail.ts` | 200+stale OK; `refetch({ force: true })` sets refresh header |
| `frontend/src/components/LifestyleIndicesGrid.tsx` | Per-card mixed unavailable (§ Lifestyle) |
| `frontend/src/components/CurrentWeather.tsx` | Root detail `meta` on hero |
| `frontend/src/components/FloatingChatbot.tsx` | `detail.error === data_unavailable` |
| **New** `StaleBadge.tsx` | `dir="auto"`, logical CSS (§ RTL) |
| **New** `WeatherValueSkeleton.tsx` | Loading; Framer fade to unavailable (§ D) |
| `ErrorMessage.tsx` | Unavailable + Yenile |

## C. i18n

Keys: `weather.stale_badge`, `weather.unavailable`, `weather.retry`, `weather.ai_unavailable`.

**Authoritative:** `en`, `tr`. **Other 41 locales:** copy `en` in Phase 6 PR; i18next falls back to `en`.

**Locale count:** `frontend/public/locales/` has **42** directories today (README “45 UI languages” is stale — reconcile in a separate doc PR). Phase 6 adds strings to **en** + **tr**; the other **40** folders fall back to English via i18next until translated.

**PR / tracking debt:** “40 locales show English stale/unavailable copy until translated. Translation tracking: _[issue link]_.”

### RTL (`StaleBadge`)

- `dir="auto"` or inherit document `dir` from i18n (`ar`, `ur`, `fa`).
- Badge uses **margin-inline-start** / logical positioning so it flips with RTL (not hard-coded left/right).
- Test: `StaleBadge` with `i18n.changeLanguage('ar')` → document or badge `dir` is `rtl`; snapshot or `getByText` + layout smoke.

## D. Loading skeleton

Skeleton while fetching. On transition to `unavailable`, **Framer Motion ~200ms fade** from skeleton to unavailable panel (already in stack).

## E. AI 503

If `response.status === 503` and `body.detail?.error === "data_unavailable"` → `weather.ai_unavailable` (use `retry_after_seconds` in copy if useful). No generic toast-only path.

## F. Yenile (Option A)

User tap → same endpoint with header **`X-AtmosMind-Refresh: 1`**. Backend re-attempts upstream; updates `meta.fetched_at` on success. **When the relevant circuit breaker is open, the server ignores the refresh header** (serves fresh cache short-circuit or stale path only — no extra upstream load). UI may disable Yenile or show retry_after when CB blocks and nothing stale is available.

## G. localStorage migration

On **first mount** (once per deploy), purge legacy popular cache keys:

```tsx
useEffect(() => {
  Object.keys(localStorage)
    .filter((k) => k.startsWith('atmosmind_popular_weather_cache_'))
    .forEach((k) => localStorage.removeItem(k));
}, []);
```

Do **not** read 15‑min client cache when batch returns `meta`. Legacy path only if `meta` absent (rollback).

## H. Detail `meta` — no sub-metas (clarification 3)

**Phase 2 implementation returns a single root `meta` on `WeatherDetailResponse` only.** There is **no** `meta.forecast` / `meta.air_quality` in the API today. `PHASE2_RESILIENCE.md` is updated to match.

Phase 6: `useCityDetail` exposes one `detailMeta` for **CurrentWeather** (forecast bundle). **LifestyleIndicesGrid** on the detail page uses **field-level** rules (§ Lifestyle), not a separate AQ meta.

## I. Lifestyle grid — partial unavailable (clarification 2)

**Choice: (c) Mixed per-card.**

- AQ / UV / pollen (from AQ slice): show values when fields are non-null; card-level unavailable copy when slice failed and fields null.
- Visibility / dew (forecast slice, no Redis in Phase 2): show unavailable placeholder when null after 200 — **not** `—`.
- Root `meta.data_status` may be `unavailable` while AQ still has numbers; **do not** hide the whole grid (not option b).

Test: mock AQ present + `visibility_meters: null` → AQ value visible; visibility card shows `weather.unavailable`.

## J. Rollback

No `meta` on payload → current `—` behavior. No FE feature flag.

## K. Test plan

| Layer | Test |
|-------|------|
| Unit | `StaleBadge`, mapper, `FloatingChatbot` 503 |
| Unit | `LifestyleIndicesGrid` partial unavailable |
| Unit | `StaleBadge` RTL (`ar`) |
| **Integration** | Mock batch: **5 stale** (2h-old `fetched_at`) + **15 fresh** → render `App` → 5 badges + values, 15 values no badge |
| E2E optional | Yenile sends header → mock returns fresh `fetched_at` |

---

*Phase 6 implementation starts after this revision is accepted. Manual Phase 2 flag-on smoke remains on your side before merge.*
