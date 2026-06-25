"""
Redis cache for fast city prefix search (popular cities only)
and current weather by coordinates.
"""
import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

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


# ─── Current weather cache (lat/lon → {temperature, condition, weather_code}) ───
WEATHER_KEY_PREFIX = "weather:current"
WEATHER_CITY_PREFIX = "weather:city"
WEATHER_TTL_SECONDS = 900  # 15 minutes


def _weather_cache_key(lat: float, lon: float) -> str:
    # Round to 2 decimals to avoid cache fragmentation
    return f"{WEATHER_KEY_PREFIX}:{round(lat, 2)}:{round(lon, 2)}"


def get_cached_weather(redis_client, lat: float, lon: float) -> Optional[dict[str, Any]]:
    """Return cached current weather for (lat, lon) or None."""
    if not redis_client:
        return None
    try:
        key = _weather_cache_key(lat, lon)
        raw = redis_client.get(key)
        if raw is None:
            return None
        data = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
        return data if isinstance(data, dict) else None
    except Exception as e:
        logger.debug("get_cached_weather failed: %s", e)
        return None


def set_cached_weather(
    redis_client, lat: float, lon: float, data: dict[str, Any], ttl: int = WEATHER_TTL_SECONDS
) -> None:
    """Store current weather for (lat, lon)."""
    if not redis_client:
        return
    try:
        key = _weather_cache_key(lat, lon)
        payload = json.dumps(data)
        redis_client.setex(key, ttl, payload)
    except Exception as e:
        logger.debug("set_cached_weather failed: %s", e)


def _city_cache_key(city_display: str) -> str:
    """Normalize city name for cache key (lowercase, strip)."""
    return f"{WEATHER_CITY_PREFIX}:{city_display.strip().casefold()}"


def get_cached_weather_by_city(redis_client, city_display: str) -> Optional[dict[str, Any]]:
    """Return cached current weather for city name or None."""
    if not redis_client:
        return None
    try:
        key = _city_cache_key(city_display)
        raw = redis_client.get(key)
        if raw is None:
            return None
        data = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
        return data if isinstance(data, dict) else None
    except Exception as e:
        logger.debug("get_cached_weather_by_city failed: %s", e)
        return None


def set_cached_weather_by_city(
    redis_client, city_display: str, data: dict[str, Any], ttl: int = WEATHER_TTL_SECONDS
) -> None:
    """Store current weather by city name."""
    if not redis_client:
        return
    try:
        key = _city_cache_key(city_display)
        payload = json.dumps(data)
        redis_client.setex(key, ttl, payload)
    except Exception as e:
        logger.debug("set_cached_weather_by_city failed: %s", e)


# ─── Air quality cache (lat/lon → Open-Meteo air-quality JSON) ───
AIR_QUALITY_KEY_PREFIX = "air_quality:current"
AIR_QUALITY_TTL_SECONDS = 900  # 15 minutes


def _air_quality_cache_key(lat: float, lon: float) -> str:
    return f"{AIR_QUALITY_KEY_PREFIX}:{round(lat, 2)}:{round(lon, 2)}"


def get_cached_air_quality(redis_client, lat: float, lon: float) -> Optional[dict[str, Any]]:
    """Return cached Open-Meteo air-quality JSON for (lat, lon) or None."""
    if not redis_client:
        return None
    try:
        key = _air_quality_cache_key(lat, lon)
        raw = redis_client.get(key)
        if raw is None:
            return None
        data = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
        return data if isinstance(data, dict) else None
    except Exception as e:
        logger.debug("get_cached_air_quality failed: %s", e)
        return None


def set_cached_air_quality(
    redis_client,
    lat: float,
    lon: float,
    data: dict[str, Any],
    ttl: int = AIR_QUALITY_TTL_SECONDS,
) -> None:
    """Store Open-Meteo air-quality JSON for (lat, lon)."""
    if not redis_client:
        return
    try:
        key = _air_quality_cache_key(lat, lon)
        payload = json.dumps(data)
        redis_client.setex(key, ttl, payload)
    except Exception as e:
        logger.debug("set_cached_air_quality failed: %s", e)
