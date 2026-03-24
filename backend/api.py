import json
import logging
import threading
import warnings
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from collections import defaultdict, deque

warnings.filterwarnings("ignore", category=FutureWarning, message=".*google.generativeai.*")

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from weather_assistant import hava_durumu_asistani, get_live_weather, get_current_weather_by_coords, geocode_city
# city_autocomplete_ai (Gemini-based) is no longer used for autocomplete.
# Autocomplete is now served by the Redis→SQLite tiered strategy below.
from ai_advice import get_city_advice, get_forecast_summary
from ai_chat import chat as ai_chat

from database import get_connection, init_schema, fetch_popular_for_redis, search_by_prefix, get_coordinates_by_display_name
from redis_cache import (
    load_popular_cities_into_redis,
    search_redis,
    get_cached_weather,
    set_cached_weather,
    get_cached_weather_by_city,
    set_cached_weather_by_city,
)

logger = logging.getLogger(__name__)
GENERIC_ERROR_MESSAGE = "An unexpected error occurred while processing your request. Please try again later."

# Simple in-memory per-IP rate limiting for abuse prevention.
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 8
_rate_limit_store: dict[str, deque[float]] = defaultdict(deque)
_rate_limit_lock = threading.Lock()


def _get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _enforce_rate_limit(request: Request, endpoint_key: str) -> None:
    client_ip = _get_client_ip(request)
    key = f"{endpoint_key}:{client_ip}"
    now = time.time()
    with _rate_limit_lock:
        bucket = _rate_limit_store[key]
        while bucket and now - bucket[0] > RATE_LIMIT_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please wait a minute and try again.",
            )
        bucket.append(now)

# Optional Redis client (None if Redis unavailable)
_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import os
        import redis
        url = os.getenv("REDIS_URL", "redis://localhost:6379")
        _redis_client = redis.from_url(url, decode_responses=False)
        _redis_client.ping()
        return _redis_client
    except Exception as e:
        logger.warning("Redis not available: %s. City search will use SQLite only.", e)
        return None


def _prewarm_weather_cache(popular: list[dict]) -> None:
    """
    Background task: pre-warm Redis weather cache for the top 1000 popular cities.
    Runs once at startup so the first user request for any popular city is an
    instant cache hit. Uses a thread pool to parallelize Open-Meteo calls.
    Cities whose weather is already cached are skipped (TTL still alive).
    """
    r = _get_redis()
    if not r or not popular:
        return

    def _warm_one(city: dict) -> None:
        try:
            lat = float(city["latitude"])
            lon = float(city["longitude"])
            # Skip if already in cache (previous startup or recent batch request)
            if get_cached_weather(r, lat, lon) is not None:
                return
            data = get_current_weather_by_coords(lat, lon)
            if "error" not in data:
                set_cached_weather(r, lat, lon, data, ttl=900)  # 15-min TTL
        except Exception as exc:
            logger.debug("Pre-warm failed for %s: %s", city.get("name"), exc)

    logger.info("Pre-warming weather cache for %d popular cities…", len(popular))
    # 20 workers: fast enough, polite to Open-Meteo
    with ThreadPoolExecutor(max_workers=20) as pool:
        pool.map(_warm_one, popular)
    logger.info("Weather cache pre-warm complete.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init DB schema, load popular cities into Redis autocomplete index,
    # then kick off background weather pre-warming for the top 1000 cities.
    popular: list[dict] = []
    try:
        conn = get_connection()
        init_schema(conn)
        r = _get_redis()
        if r:
            popular = fetch_popular_for_redis(conn, limit=1000)
            if popular:
                load_popular_cities_into_redis(r, popular)
        conn.close()
    except Exception as e:
        logger.exception("Startup: failed to init DB or Redis cache: %s", e)

    # Fire-and-forget: pre-warm weather for popular cities in the background
    # so the main server starts instantly and the cache fills up concurrently.
    if popular:
        t = threading.Thread(
            target=_prewarm_weather_cache, args=(popular,), daemon=True, name="weather-prewarm"
        )
        t.start()

    yield

    # Shutdown: close Redis
    global _redis_client
    if _redis_client is not None:
        try:
            _redis_client.close()
        except Exception as e:
            logger.warning("Redis close: %s", e)
        _redis_client = None


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class WeatherRequest(BaseModel):
    city: str = Field(..., min_length=1, max_length=120)
    language: str = Field(default="en", min_length=2, max_length=8)
    unit: str = Field(default="metric", min_length=2, max_length=16)


class WeatherResponse(BaseModel):
    city: str | None
    temperature: float | None   # float — Open-Meteo returns numeric values
    condition: str | None
    humidity: int | None        # relative_humidity_2m is an integer percent
    wind: float | None          # wind speed in km/h
    time: str | None
    aiAnswer: str


@app.post("/api/ai-weather", response_model=WeatherResponse)
def ai_weather(req: WeatherRequest, request: Request):
    _enforce_rate_limit(request, "ai-weather")
    question = (
        f"Lütfen '{req.city}' şehri için güncel hava durumunu getir. "
        f"get_weather_in_city aracını kullan ve kısa, anlaşılır yanıt ver. "
        f"You MUST respond in '{req.language}' and use {'Fahrenheit (°F)' if req.unit == 'imperial' else 'Celsius (°C)'} for all temperature values."
    )

    ai_answer = hava_durumu_asistani(question)

    weather = get_live_weather(req.city)
    if isinstance(weather, dict) and "error" in weather:
        return WeatherResponse(
            city=None,
            temperature=None,
            condition=None,
            humidity=None,
            wind=None,
            time=None,
            aiAnswer=f"{ai_answer}\n\nHata: {weather['error']}",
        )

    return WeatherResponse(
        city=weather.get("city") if isinstance(weather, dict) else None,
        temperature=weather.get("temperature") if isinstance(weather, dict) else None,
        condition=weather.get("condition") if isinstance(weather, dict) else None,
        humidity=weather.get("humidity") if isinstance(weather, dict) else None,
        wind=weather.get("wind") if isinstance(weather, dict) else None,
        time=weather.get("local_time") if isinstance(weather, dict) else None,
        aiAnswer=str(ai_answer),
    )


# ─── Shared autocomplete constants ───────────────────────────────────────────
MIN_QUERY_LEN   = 3    # reject queries shorter than this (mirrors frontend guard)
MIN_SUGGESTIONS = 5    # always try to reach at least this many results
MAX_SUGGESTIONS = 8    # hard cap on suggestions returned


class AutocompleteRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    language: str = Field(default="en", min_length=2, max_length=8)


class AutocompleteResponse(BaseModel):
    suggestions: list[str]


def _tiered_search(prefix: str, language: str = "en") -> list[dict]:
    """
    Tiered city search — shared by both autocomplete endpoints.

    Tier 1 — Redis ZRANGEBYLEX (sub-millisecond, top-1000 popular cities):
        Uses the sorted-set lex index built at startup.
        e.g. prefix 'lon' → [London, United Kingdom] instantly.

    Tier 2 — SQLite LIKE prefix query (indexed on name_lower):
        Only executed if Redis returns fewer than MIN_SUGGESTIONS results.
        Covers the full city database including obscure cities.

    Tier 3 — Open-Meteo fallback via real-time HTTP request:
        Executed if we still have fewer than MIN_SUGGESTIONS results.
    """
    if not prefix or len(prefix) < MIN_QUERY_LEN:
        return []

    # Deduplicate by semantic location key (name + rounded coordinates),
    # not by display text. This avoids duplicates like:
    # "Ankara, TR" and "Ankara, TR (Ankara)".
    suggestions_set: set[tuple[str, float, float]] = set()
    suggestions_ordered: list[dict] = []

    normalized_language = (language or "en").strip().casefold().split("-")[0]

    # ── Tier 0 (localized-first): Open-Meteo when UI language is non-English ──
    if normalized_language != "en":
        try:
            url = "https://geocoding-api.open-meteo.com/v1/search"
            params = {
                "name": prefix,
                "count": 10,
                "language": normalized_language,
                "format": "json",
            }
            resp = requests.get(url, params=params, timeout=2.0)
            if resp.status_code == 200:
                data = resp.json()
                for row in data.get("results", []):
                    name = row.get("name")
                    country = row.get("country_code") or row.get("country", "")
                    if not name:
                        continue
                    try:
                        lat = float(row.get("latitude", 0))
                        lon = float(row.get("longitude", 0))
                    except (TypeError, ValueError):
                        continue
                    dedupe_key = (str(name).strip().casefold(), round(lat, 2), round(lon, 2))
                    if dedupe_key in suggestions_set:
                        continue
                    suggestions_set.add(dedupe_key)
                    suggestions_ordered.append({
                        "name": f"{name}, {country}" if country else name,
                        "lat": lat,
                        "lon": lon,
                    })
                    if len(suggestions_ordered) >= MAX_SUGGESTIONS:
                        break
        except Exception as exc:
            logger.warning("Localized Open-Meteo autocomplete failed for %r: %s", prefix, exc)
        # For non-English UI, do not fall back to Redis/SQLite English labels.
        # Return only localized API names to preserve character integrity.
        return suggestions_ordered[:MAX_SUGGESTIONS]

    # ── Tier 1: Redis ZRANGEBYLEX ─────────────────────────────────────────────
    if len(suggestions_ordered) < MIN_SUGGESTIONS:
        try:
            r = _get_redis()
            if r:
                redis_hits = search_redis(r, prefix, limit=MAX_SUGGESTIONS)
                for s in redis_hits:
                    try:
                        lat = float(s["lat"])
                        lon = float(s["lon"])
                    except (KeyError, TypeError, ValueError):
                        continue
                    dedupe_key = (str(s.get("name", "")).strip().casefold(), round(lat, 2), round(lon, 2))
                    if dedupe_key not in suggestions_set:
                        suggestions_set.add(dedupe_key)
                        suggestions_ordered.append({
                            "name": s.get("name", ""),
                            "lat": lat,
                            "lon": lon,
                        })
        except Exception as exc:
            logger.warning("Redis autocomplete failed for %r: %s", prefix, exc)

    # ── Tier 2: SQLite fallback ───────────────────────────────────────────────
    if len(suggestions_ordered) < MIN_SUGGESTIONS:
        try:
            conn = get_connection()
            sqlite_rows = search_by_prefix(
                conn, prefix, limit=MAX_SUGGESTIONS - len(suggestions_ordered)
            )
            conn.close()
            for row in sqlite_rows:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
                display = f"{row['name']}, {row['country']}"
                dedupe_key = (str(row["name"]).strip().casefold(), round(lat, 2), round(lon, 2))
                if dedupe_key not in suggestions_set:
                    suggestions_set.add(dedupe_key)
                    suggestions_ordered.append({
                        "name": display,
                        "lat": lat,
                        "lon": lon
                    })
        except Exception as exc:
            logger.exception("SQLite autocomplete failed for prefix %r: %s", prefix, exc)

    # ── Tier 3: Open-Meteo external fallback ──────────────────────────────────
    if len(suggestions_ordered) < MIN_SUGGESTIONS:
        try:
            url = "https://geocoding-api.open-meteo.com/v1/search"
            params = {
                "name": prefix,
                "count": 10,
                "language": normalized_language,
                "format": "json"
            }
            resp = requests.get(url, params=params, timeout=2.0)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                for row in results:
                    name = row.get("name")
                    country = row.get("country_code") or row.get("country", "")
                    if not name:
                        continue
                        
                    admin1 = row.get("admin1")
                    if admin1 and isinstance(admin1, str):
                        country = f"{country} ({admin1})"
                        
                    display = f"{name}, {country}" if country else name

                    try:
                        lat = float(row.get("latitude", 0))
                        lon = float(row.get("longitude", 0))
                    except (TypeError, ValueError):
                        continue
                    dedupe_key = (str(name).strip().casefold(), round(lat, 2), round(lon, 2))

                    if dedupe_key not in suggestions_set:
                        suggestions_set.add(dedupe_key)
                        suggestions_ordered.append({
                            "name": display,
                            "lat": lat,
                            "lon": lon
                        })
                        if len(suggestions_ordered) >= MAX_SUGGESTIONS:
                            break
        except Exception as exc:
            logger.warning("Open-Meteo fallback failed for prefix %r: %s", prefix, exc)

    return suggestions_ordered[:MAX_SUGGESTIONS]


@app.post("/api/autocomplete")
def autocomplete(req: AutocompleteRequest):
    """
    Fast, LLM-free autocomplete.
    Tier 1: Redis ZRANGEBYLEX on the top-1000 cities index (sub-ms).
    Tier 2: SQLite indexed LIKE fallback for full coverage.
    Returns a raw JSON bytes response to minimise serialisation overhead.
    """
    q = req.query.strip()
    if len(q) < MIN_QUERY_LEN:
        return Response(
            content='{"suggestions":[]}',
            media_type="application/json",
        )

    results = _tiered_search(q, req.language)
    payload = json.dumps({"suggestions": results}, ensure_ascii=False)
    return Response(content=payload, media_type="application/json")


@app.get("/api/search-city")
def search_city(q: str = "", lang: str = "en"):
    """
    GET alias of the same tiered search — kept for backwards compatibility.
    """
    prefix = (q or "").strip()
    results = _tiered_search(prefix, lang)
    payload = json.dumps({"suggestions": results}, ensure_ascii=False)
    return Response(content=payload, media_type="application/json")


# ─── Get city advice (Feature 1) ─────────────────────────────────────────────
class GetCityAdviceRequest(BaseModel):
    city: str = Field(..., min_length=1, max_length=120)
    weather_summary: str = Field(..., min_length=1, max_length=1500)
    language: str = Field(default="en", min_length=2, max_length=8)
    unit: str = Field(default="metric", min_length=2, max_length=16)


class GetCityAdviceResponse(BaseModel):
    advice: str


@app.post("/api/get-city-advice", response_model=GetCityAdviceResponse)
def get_city_advice_endpoint(req: GetCityAdviceRequest, request: Request):
    _enforce_rate_limit(request, "get-city-advice")
    advice = get_city_advice(req.city, req.weather_summary, req.language, req.unit)
    return GetCityAdviceResponse(advice=advice)


class GetForecastSummaryRequest(BaseModel):
    city: str = Field(..., min_length=1, max_length=120)
    weather_summary: str = Field(..., min_length=1, max_length=1500)
    language: str = Field(default="en", min_length=2, max_length=8)
    unit: str = Field(default="metric", min_length=2, max_length=16)


class GetForecastSummaryResponse(BaseModel):
    summary: str


@app.post("/api/get-forecast-summary", response_model=GetForecastSummaryResponse)
def get_forecast_summary_endpoint(req: GetForecastSummaryRequest, request: Request):
    _enforce_rate_limit(request, "get-forecast-summary")
    summary = get_forecast_summary(req.city, req.weather_summary, req.language, req.unit)
    return GetForecastSummaryResponse(summary=summary)


# ─── Global weather chatbot (Feature 2) ──────────────────────────────────────
class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str = Field(..., min_length=1, max_length=500)


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    language: str = Field(default="en", min_length=2, max_length=8)
    unit: str = Field(default="metric", min_length=2, max_length=16)


class ChatResponse(BaseModel):
    reply: str


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest, request: Request):
    _enforce_rate_limit(request, "chat")
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    reply = ai_chat(messages, req.language, req.unit)
    return ChatResponse(reply=reply)


# ─── Batch current weather for popular city cards ─────────────────────────────
class BatchWeatherRequest(BaseModel):
    cities: list[str]  # e.g. ["London, United Kingdom", "Tokyo, Japan"]


class BatchWeatherItem(BaseModel):
    city: str
    temperature: float | None = None
    condition: str | None = None
    weather_code: int | None = None
    error: str | None = None


class BatchWeatherResponse(BaseModel):
    results: list[BatchWeatherItem]
    temperatures: dict[str, float] = {}  # city name -> current temperature (for easy frontend binding)


def _resolve_coords(city_display: str):
    """Return (lat, lon) for city display name: DB first, then geocoding."""
    try:
        conn = get_connection()
        row = get_coordinates_by_display_name(conn, city_display)
        conn.close()
        if row is not None:
            return float(row["latitude"]), float(row["longitude"])
    except Exception as e:
        logger.debug("DB resolve failed for %r: %s", city_display, e)
    coords = geocode_city(city_display)
    if coords:
        return coords["latitude"], coords["longitude"]
    return None


def _fetch_one_weather(city_display: str, lat: float, lon: float):
    """Get current weather for one city. Check Redis first for instant dashboard; then Open-Meteo. Cache 15 min."""
    r = _get_redis()
    cached = get_cached_weather(r, lat, lon)
    if cached is not None:
        return BatchWeatherItem(
            city=city_display,
            temperature=cached.get("temperature"),
            condition=cached.get("condition"),
            weather_code=cached.get("weather_code"),
        )
    data = get_current_weather_by_coords(lat, lon)
    if "error" in data:
        return BatchWeatherItem(city=city_display, error=data["error"])
    payload = {
        "temperature": data.get("temperature"),
        "condition": data.get("condition"),
        "weather_code": data.get("weather_code"),
    }
    if r:
        set_cached_weather(r, lat, lon, payload, ttl=900)
    return BatchWeatherItem(
        city=city_display,
        temperature=payload["temperature"],
        condition=payload["condition"],
        weather_code=payload["weather_code"],
    )


def _fetch_one_weather_by_name(city_display: str):
    """Fallback: check Redis first, then get_live_weather (Open-Meteo). Cache by city name 15 min."""
    r = _get_redis()
    cached = get_cached_weather_by_city(r, city_display)
    if cached is not None:
        return BatchWeatherItem(
            city=city_display,
            temperature=cached.get("temperature"),
            condition=cached.get("condition"),
            weather_code=cached.get("weather_code"),
        )
    data = get_live_weather(city_display)
    if not isinstance(data, dict) or "error" in data:
        return BatchWeatherItem(city=city_display, error=data.get("error", "Unknown error") if isinstance(data, dict) else "No data")
    payload = {
        "temperature": data.get("temperature"),
        "condition": data.get("condition"),
        "weather_code": None,  # get_live_weather does not return WMO code
    }
    if r:
        set_cached_weather_by_city(r, city_display, payload, ttl=900)
    return BatchWeatherItem(
        city=city_display,
        temperature=payload["temperature"],
        condition=payload["condition"],
        weather_code=payload["weather_code"],
    )


@app.post("/api/weather/batch", response_model=BatchWeatherResponse)
def weather_batch(req: BatchWeatherRequest):
    """
    Fetch current temperature (and condition) for popular city names.
    CRITICAL: Redis is checked first per city; if e.g. London was fetched 5 min ago, return from cache
    so the dashboard stays instant. On cache miss, use Open-Meteo (coords from DB or geocode, then
    get_current_weather_by_coords; fallback get_live_weather). Cache TTL 15 minutes.
    Returns results array and temperatures map (city name -> °C) for frontend binding.
    """
    cities = [c.strip() for c in (req.cities or []) if c and c.strip()]
    if not cities:
        return BatchWeatherResponse(results=[], temperatures={})

    # Resolve all cities to (lat, lon) or None
    resolved = []
    for city_display in cities:
        coords = _resolve_coords(city_display)
        if coords is not None:
            resolved.append((city_display, coords[0], coords[1]))
        else:
            resolved.append((city_display, None, None))

    results = []
    max_workers = min(10, len(resolved))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_city = {}
        for city_display, lat, lon in resolved:
            if lat is not None and lon is not None:
                future_to_city[executor.submit(_fetch_one_weather, city_display, lat, lon)] = city_display
            else:
                future_to_city[executor.submit(_fetch_one_weather_by_name, city_display)] = city_display

        for future in as_completed(future_to_city):
            try:
                results.append(future.result())
            except Exception as e:
                city_display = future_to_city[future]
                logger.exception("Batch weather failed for %r: %s", city_display, e)
                results.append(BatchWeatherItem(city=city_display, error=GENERIC_ERROR_MESSAGE))

    # Preserve order of input cities
    by_city = {r.city: r for r in results}
    ordered = [by_city.get(c, BatchWeatherItem(city=c, error="Unknown")) for c in cities]
    temperatures = {r.city: r.temperature for r in ordered if r.temperature is not None}
    return BatchWeatherResponse(results=ordered, temperatures=temperatures)

