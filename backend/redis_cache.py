"""
Redis cache for fast city prefix search (popular cities only)
and current weather by coordinates.

Phase 1: cache entries are stored as versioned envelopes with ``fetched_at`` metadata.
Redis still uses SETEX with the configured soft TTL (900s default); payloads are
hard-deleted at expiry. Phase 2 will use longer hard TTL + ``fetched_at`` for SWR.
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from logging_config import log_cache_event, log_cache_unavailable
from metrics import record_cache_hit, record_cache_miss, record_cache_unavailable

logger = logging.getLogger(__name__)


def _emit_cache_hit(
    cache: str,
    cache_kind: str,
    lat: float | None = None,
    lon: float | None = None,
) -> None:
    try:
        log_cache_event("cache_hit", cache=cache, cache_kind=cache_kind, lat=lat, lon=lon)
        record_cache_hit()
    except Exception:
        pass


def _emit_cache_miss(
    cache: str,
    cache_kind: str,
    lat: float | None = None,
    lon: float | None = None,
) -> None:
    try:
        log_cache_event("cache_miss", cache=cache, cache_kind=cache_kind, lat=lat, lon=lon)
        record_cache_miss()
    except Exception:
        pass


def _emit_cache_unavailable(
    cache: str,
    cache_kind: str,
    lat: float | None = None,
    lon: float | None = None,
) -> None:
    try:
        log_cache_unavailable(cache=cache, cache_kind=cache_kind, lat=lat, lon=lon)
        record_cache_unavailable()
    except Exception:
        pass

REDIS_KEY_LEX = "autocomplete:cities_lex"
SEPARATOR = "|"
MAX_CACHE_RESULTS = 10


def _member_encode(name: str, country: str, lat: float, lon: float) -> str:
    """Encode city for Redis: name_lower|name|country|lat|lon (no SEPARATOR in values)."""
    name_lower = name.casefold().replace(SEPARATOR, " ")
    name_safe = name.replace(SEPARATOR, " ")
    country_safe = (country or "").replace(SEPARATOR, " ")
    return f"{name_lower}{SEPARATOR}{name_safe}{SEPARATOR}{country_safe}{SEPARATOR}{lat}{SEPARATOR}{lon}"


def _member_decode(member: str) -> Optional[tuple[str, str, float, float]]:
    """Decode member to (name, country, lat, lon). Returns None if invalid."""
    try:
        parts = member.split(SEPARATOR, 4)
        if len(parts) < 5:
            return None
        _name_lower, name, country, lat_s, lon_s = parts
        return (name, country, float(lat_s), float(lon_s))
    except (ValueError, IndexError):
        return None


def load_popular_cities_into_redis(redis_client, popular_cities: list[dict]) -> None:
    """
    Load popular cities from SQLite result list into Redis Sorted Set.
    Each member is name_lower|name|country|lat|lon; score 0 for lex order.
    """
    if not redis_client or not popular_cities:
        return
    try:
        key = REDIS_KEY_LEX
        redis_client.delete(key)
        pipe = redis_client.pipeline()
        for c in popular_cities:
            name = c.get("name") or ""
            country = c.get("country") or ""
            try:
                lat = float(c.get("latitude", 0))
                lon = float(c.get("longitude", 0))
            except (TypeError, ValueError):
                continue
            member = _member_encode(name, country, lat, lon)
            pipe.zadd(key, {member: 0})
        pipe.execute()
        logger.info("Loaded %d popular cities into Redis key %s", len(popular_cities), key)
    except Exception as e:
        logger.exception("Failed to load popular cities into Redis: %s", e)


def search_redis(redis_client, prefix: str, limit: int = MAX_CACHE_RESULTS) -> list[dict]:
    """
    Prefix search in Redis. Returns list of dicts: {"name": "City, Country", "lat": float, "lon": float}.
    Empty list on error or no client.
    """
    if not redis_client:
        return []
    prefix_clean = prefix.strip().casefold()
    if not prefix_clean or limit <= 0:
        return []
    try:
        # Lex range: >= prefix and < prefix_plus_one (e.g. "ist" <= x < "isu")
        start = f"[{prefix_clean}"
        # Exclusive end: increment last char so we get all prefix* (e.g. "ist" -> "isu")
        end_chars = list(prefix_clean)
        if end_chars:
            end_chars[-1] = chr(ord(end_chars[-1]) + 1)
            end = "(" + "".join(end_chars)
        else:
            end = "+"
        members = redis_client.zrangebylex(REDIS_KEY_LEX, start, end, start=0, num=limit)
        out = []
        for m in members:
            decoded = _member_decode(m.decode() if isinstance(m, bytes) else m)
            if decoded:
                name, country, _lat, _lon = decoded
                out.append({"name": f"{name}, {country}", "lat": _lat, "lon": _lon})
        return out
    except Exception as e:
        logger.exception("Redis search failed for prefix %r: %s", prefix, e)
        return []


# ─── Cache TTL (env-driven; default 900s = legacy 15 min) ─────────────────────


def get_weather_ttl() -> int:
    return int(os.getenv("WEATHER_TTL_SECONDS", "900"))


def get_weather_detail_ttl() -> int:
    return int(os.getenv("WEATHER_DETAIL_TTL_SECONDS", "900"))


def get_air_quality_ttl() -> int:
    return int(os.getenv("AIR_QUALITY_TTL_SECONDS", "900"))


CACHE_ENVELOPE_SENTINEL = "__atmosmind__"
CACHE_ENVELOPE_VERSION = 1


def utc_fetched_at_now() -> str:
    """UTC ISO8601 timestamp with millisecond precision, always ending in Z."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _wrap_cache_envelope(data: dict[str, Any]) -> dict[str, Any]:
    return {
        CACHE_ENVELOPE_SENTINEL: CACHE_ENVELOPE_VERSION,
        "fetched_at": utc_fetched_at_now(),
        "data": data,
    }


def _decode_raw_cache_bytes(raw: Any) -> Any | None:
    try:
        return json.loads(raw.decode() if isinstance(raw, bytes) else raw)
    except Exception:
        return None


def _unwrap_stored_cache_payload(
    parsed: Any,
    *,
    cache: str,
    cache_kind: str,
    lat: float | None = None,
    lon: float | None = None,
) -> Optional[dict[str, Any]]:
    if not isinstance(parsed, dict):
        _emit_cache_miss(cache, cache_kind, lat=lat, lon=lon)
        return None

    if parsed.get(CACHE_ENVELOPE_SENTINEL) == CACHE_ENVELOPE_VERSION:
        data = parsed.get("data")
        if not isinstance(data, dict):
            _emit_cache_miss(cache, cache_kind, lat=lat, lon=lon)
            return None
        _emit_cache_hit(cache, cache_kind, lat=lat, lon=lon)
        return data

    # Legacy bare dict (pre-envelope rollout). Removable after Phase 2 SWR is stable.
    _emit_cache_hit(cache, cache_kind, lat=lat, lon=lon)
    return parsed


def _read_cached_payload(
    redis_client,
    key: str,
    *,
    cache: str,
    cache_kind: str,
    lat: float | None = None,
    lon: float | None = None,
) -> Optional[dict[str, Any]]:
    try:
        raw = redis_client.get(key)
    except Exception as e:
        _emit_cache_unavailable(cache, cache_kind, lat=lat, lon=lon)
        logger.debug("%s failed: %s", cache_kind, e)
        return None

    if raw is None:
        _emit_cache_miss(cache, cache_kind, lat=lat, lon=lon)
        return None

    parsed = _decode_raw_cache_bytes(raw)
    if parsed is None:
        _emit_cache_miss(cache, cache_kind, lat=lat, lon=lon)
        return None

    return _unwrap_stored_cache_payload(
        parsed, cache=cache, cache_kind=cache_kind, lat=lat, lon=lon
    )


def _write_cached_payload(
    redis_client,
    key: str,
    data: dict[str, Any],
    ttl: int,
    log_label: str,
) -> None:
    try:
        envelope = _wrap_cache_envelope(data)
        redis_client.setex(key, ttl, json.dumps(envelope))
    except Exception as e:
        logger.debug("%s failed: %s", log_label, e)


# ─── Current weather cache (lat/lon → {temperature, condition, weather_code}) ───
WEATHER_KEY_PREFIX = "weather:current"
WEATHER_CITY_PREFIX = "weather:city"


def _weather_cache_key(lat: float, lon: float) -> str:
    # Round to 2 decimals to avoid cache fragmentation
    return f"{WEATHER_KEY_PREFIX}:{round(lat, 2)}:{round(lon, 2)}"


def get_cached_weather(redis_client, lat: float, lon: float) -> Optional[dict[str, Any]]:
    """Return cached current weather for (lat, lon) or None."""
    if not redis_client:
        return None
    key = _weather_cache_key(lat, lon)
    return _read_cached_payload(
        redis_client,
        key,
        cache="weather",
        cache_kind="weather_current",
        lat=lat,
        lon=lon,
    )


def set_cached_weather(
    redis_client,
    lat: float,
    lon: float,
    data: dict[str, Any],
    ttl: int | None = None,
) -> None:
    """Store current weather for (lat, lon)."""
    if not redis_client:
        return
    key = _weather_cache_key(lat, lon)
    _write_cached_payload(
        redis_client, key, data, ttl if ttl is not None else get_weather_ttl(), "set_cached_weather"
    )


def _city_cache_key(city_display: str) -> str:
    """Normalize city name for cache key (lowercase, strip)."""
    return f"{WEATHER_CITY_PREFIX}:{city_display.strip().casefold()}"


def get_cached_weather_by_city(redis_client, city_display: str) -> Optional[dict[str, Any]]:
    """Return cached current weather for city name or None."""
    if not redis_client:
        return None
    key = _city_cache_key(city_display)
    return _read_cached_payload(redis_client, key, cache="weather", cache_kind="weather_city")


def set_cached_weather_by_city(
    redis_client,
    city_display: str,
    data: dict[str, Any],
    ttl: int | None = None,
) -> None:
    """Store current weather by city name."""
    if not redis_client:
        return
    key = _city_cache_key(city_display)
    _write_cached_payload(
        redis_client,
        key,
        data,
        ttl if ttl is not None else get_weather_ttl(),
        "set_cached_weather_by_city",
    )


# ─── City detail cache (lat/lon + language + unit → WeatherDetailResponse JSON) ───
WEATHER_DETAIL_KEY_PREFIX = "weather:detail"


def _weather_detail_cache_key(lat: float, lon: float, language: str, unit: str) -> str:
    lang = (language or "en").split("-")[0].casefold()[:8]
    unit_key = (unit or "metric").casefold()
    return f"{WEATHER_DETAIL_KEY_PREFIX}:{round(lat, 2)}:{round(lon, 2)}:{lang}:{unit_key}"


def get_cached_weather_detail(
    redis_client,
    lat: float,
    lon: float,
    language: str,
    unit: str,
) -> Optional[dict[str, Any]]:
    """Return cached city-detail payload dict or None."""
    if not redis_client:
        return None
    key = _weather_detail_cache_key(lat, lon, language, unit)
    return _read_cached_payload(
        redis_client,
        key,
        cache="weather",
        cache_kind="weather_detail",
        lat=lat,
        lon=lon,
    )


def set_cached_weather_detail(
    redis_client,
    lat: float,
    lon: float,
    language: str,
    unit: str,
    data: dict[str, Any],
    ttl: int | None = None,
) -> None:
    """Store city-detail payload for (lat, lon, language, unit)."""
    if not redis_client:
        return
    key = _weather_detail_cache_key(lat, lon, language, unit)
    _write_cached_payload(
        redis_client,
        key,
        data,
        ttl if ttl is not None else get_weather_detail_ttl(),
        "set_cached_weather_detail",
    )


# ─── Air quality cache (lat/lon → Open-Meteo air-quality JSON) ───
AIR_QUALITY_KEY_PREFIX = "air_quality:current"


def _air_quality_cache_key(lat: float, lon: float) -> str:
    return f"{AIR_QUALITY_KEY_PREFIX}:{round(lat, 2)}:{round(lon, 2)}"


def get_cached_air_quality(redis_client, lat: float, lon: float) -> Optional[dict[str, Any]]:
    """Return cached Open-Meteo air-quality JSON for (lat, lon) or None."""
    if not redis_client:
        return None
    key = _air_quality_cache_key(lat, lon)
    return _read_cached_payload(
        redis_client,
        key,
        cache="aq",
        cache_kind="air_quality",
        lat=lat,
        lon=lon,
    )


def set_cached_air_quality(
    redis_client,
    lat: float,
    lon: float,
    data: dict[str, Any],
    ttl: int | None = None,
) -> None:
    """Store Open-Meteo air-quality JSON for (lat, lon)."""
    if not redis_client:
        return
    key = _air_quality_cache_key(lat, lon)
    _write_cached_payload(
        redis_client,
        key,
        data,
        ttl if ttl is not None else get_air_quality_ttl(),
        "set_cached_air_quality",
    )
