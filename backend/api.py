from logging_config import setup_logging

setup_logging()

import json
import logging
import os
import socket
import threading
import requests
import asyncio
from contextlib import asynccontextmanager

from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.base import BaseHTTPMiddleware

from weather_assistant import hava_durumu_asistani, get_live_weather, get_current_weather_by_coords, geocode_city
from open_meteo_client import get_current_weather_batch_by_coords
# city_autocomplete_ai (Gemini-based) is no longer used for autocomplete.
# Autocomplete is now served by the Redis→SQLite tiered strategy below.
from ai_advice import get_city_advice, get_forecast_summary
from langchain_agent import AtmosMindAgent, create_atmosmind_agent

from database import get_connection, init_schema, fetch_popular_for_redis, search_by_prefix, get_coordinates_by_display_name
from redis_cache import (
    load_popular_cities_into_redis,
    search_redis,
    get_cached_weather,
    set_cached_weather,
    get_cached_weather_by_city,
    set_cached_weather_by_city,
)
from security import (
    RATE_LIMIT_MAX_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
    enforce_rate_limit,
    evaluate_chat_input_safety,
    get_allowed_origins,
    get_client_ip,
    get_cors_origin_regex,
)
from lifestyle_indices import LifestyleIndicesResponse, fetch_lifestyle_indices
from weather_detail import ForecastUnavailableError, WeatherDetailResponse, fetch_weather_detail
from observability import configure_langsmith_tracing, langsmith_tracing_active
from logging_config import log_redis_event

logger = logging.getLogger(__name__)
GENERIC_ERROR_MESSAGE = "An unexpected error occurred while processing your request. Please try again later."

EXTERNAL_API_HOSTS = (
    "generativelanguage.googleapis.com",
    "api.open-meteo.com",
    "geocoding-api.open-meteo.com",
)

# Optional Redis client (None if Redis unavailable)
_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        url = os.getenv("REDIS_URL", "redis://localhost:6379")
        _redis_client = redis.from_url(url, decode_responses=False)
        _redis_client.ping()
        return _redis_client
    except Exception as e:
        log_redis_event(
            "connect_failed",
            component="api._get_redis",
            fallback="sqlite_autocomplete",
            error=str(e),
        )
        return None


def _prewarm_weather_cache(popular: list[dict]) -> None:
    """
    Background task: pre-warm Redis weather cache for popular cities.

    Uses chunked Open-Meteo *batch* requests (not parallel per-city calls) to avoid 429s.
    """
    r = _get_redis()
    if not r or not popular:
        return

    prewarm_limit = max(0, int(os.getenv("PREWARM_CITIES_LIMIT", "80")))
    if prewarm_limit == 0:
        logger.info("Weather cache pre-warm disabled (PREWARM_CITIES_LIMIT=0).")
        return

    candidates = popular[:prewarm_limit]
    misses: list[tuple[dict, float, float]] = []
    for city in candidates:
        try:
            lat = float(city["latitude"])
            lon = float(city["longitude"])
            if get_cached_weather(r, lat, lon) is None:
                misses.append((city, lat, lon))
        except (KeyError, TypeError, ValueError) as exc:
            logger.debug("Pre-warm skip invalid city row %s: %s", city, exc)

    if not misses:
        logger.info("Weather cache pre-warm: all %d candidates already cached.", len(candidates))
        return

    logger.info(
        "Pre-warming weather cache for %d cities (%d cache misses, chunked batch API)…",
        len(candidates),
        len(misses),
    )
    coords = [(lat, lon) for _city, lat, lon in misses]
    batch_results = get_current_weather_batch_by_coords(coords)

    warmed = 0
    for (city, lat, lon), data in zip(misses, batch_results):
        if "error" in data:
            logger.debug("Pre-warm miss for %s: %s", city.get("name"), data.get("error"))
            continue
        payload = {
            "temperature": data.get("temperature"),
            "condition": data.get("condition"),
            "weather_code": data.get("weather_code"),
        }
        set_cached_weather(r, lat, lon, payload, ttl=900)
        warmed += 1

    logger.info("Weather cache pre-warm complete (%d/%d stored).", warmed, len(misses))


async def _warmup_external_dns() -> None:
    """Resolve external API hostnames at startup to prime Docker's DNS cache."""
    loop = asyncio.get_running_loop()

    async def _resolve(host: str) -> None:
        try:
            await loop.run_in_executor(None, socket.getaddrinfo, host, 443)
            logger.info("DNS warmup OK: %s", host)
        except OSError as exc:
            logger.warning("DNS warmup failed for %s: %s", host, exc)

    await asyncio.gather(*(_resolve(host) for host in EXTERNAL_API_HOSTS))


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

    try:
        await _warmup_external_dns()
    except Exception as e:
        logger.warning("Startup: external DNS warmup failed: %s", e)

    configure_langsmith_tracing()

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


def _is_production_env() -> bool:
    return os.getenv("ENV", "").strip().casefold() == "production"


_fastapi_kwargs: dict = {"lifespan": lifespan}
if _is_production_env():
    _fastapi_kwargs.update(docs_url=None, redoc_url=None, openapi_url=None)

app = FastAPI(**_fastapi_kwargs)

# Mirror frontend security headers when the API is exposed directly (non-Vercel).
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "X-DNS-Prefetch-Control": "off",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        for key, value in _SECURITY_HEADERS.items():
            if key not in response.headers:
                response.headers[key] = value
        return response


app.add_middleware(SecurityHeadersMiddleware)

# CORS: ALLOWED_ORIGINS (comma-separated) + regex for Vercel preview deploys (*.vercel.app).
# Example ALLOWED_ORIGINS: https://atmosmindweather.com,https://www.atmosmindweather.com,http://localhost:3000
_cors_allowed_origins = get_allowed_origins()
_cors_origin_regex = get_cors_origin_regex()

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allowed_origins,
    allow_origin_regex=_cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

@app.get("/health")
async def health_check():
    return {"status": "ok", "redis": _get_redis() is not None}


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
async def ai_weather(req: WeatherRequest, request: Request):
    await enforce_rate_limit(request, "ai-weather", _get_redis())
    question = (
        f"Lütfen '{req.city}' şehri için güncel hava durumunu getir. "
        f"get_weather_in_city aracını kullan ve kısa, anlaşılır yanıt ver. "
        f"You are a multi-lingual assistant. You must respond in the same language currently selected by the user in the UI. If the UI is set to 'Español', your responses must be in Spanish. If '한국어', respond in Korean. The active language is '{req.language}'. "
        f"Use {'Fahrenheit (°F)' if req.unit == 'imperial' else 'Celsius (°C)'} for all temperature values."
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

    Tier 0 — Localized Open-Meteo for non-English UI (filtered to PPL* feature codes).
    Tier 1 — Redis ZRANGEBYLEX (sub-millisecond, top-1000 popular cities).
    Tier 2 — SQLite LIKE prefix query (indexed on name_lower).
    Tier 3 — Open-Meteo external fallback (filtered to PPL* feature codes).

    Only populated places (feature_code starting with 'PPL') are kept.
    Results are sorted by population descending and deduplicated by
    the semantic key: name_lower|admin1_lower|country_code_upper.
    """
    if not prefix or len(prefix) < MIN_QUERY_LEN:
        return []

    # PPL feature codes cover populated places only (cities, towns, villages).
    # Excluded: AIRP (airports), RSTN (rail stations), LCTY (localities), etc.
    ALLOWED_FEATURE_PREFIXES = ("PPL",)

    def _is_ppl(feature_code: str | None) -> bool:
        if not feature_code:
            return True  # SQLite/Redis rows don't carry feature_code — allow them through
        return str(feature_code).upper().startswith(ALLOWED_FEATURE_PREFIXES)

    def _make_dedup_key(name: str, admin1: str | None, country_code: str | None) -> tuple:
        return (
            name.strip().casefold(),
            (admin1 or "").strip().casefold(),
            (country_code or "").strip().upper(),
        )

    def _make_display(name: str, admin1: str | None, country: str | None) -> str:
        parts = [name.strip()]
        if admin1 and admin1.strip():
            parts.append(admin1.strip())
        if country and country.strip():
            parts.append(country.strip())
        return ", ".join(parts)

    suggestions_set: set[tuple] = set()
    suggestions_ordered: list[dict] = []

    normalized_language = (language or "en").strip().casefold().split("-")[0]

    # ── Tier 0 (localized-first): Open-Meteo when UI language is non-English ──
    if normalized_language != "en":
        try:
            url = "https://geocoding-api.open-meteo.com/v1/search"
            params = {
                "name": prefix,
                "count": 15,
                "language": normalized_language,
                "format": "json",
            }
            resp = requests.get(url, params=params, timeout=2.0)
            if resp.status_code == 200:
                data = resp.json()
                rows = sorted(
                    data.get("results", []),
                    key=lambda r: r.get("population", 0) or 0,
                    reverse=True,
                )
                for row in rows:
                    if not _is_ppl(row.get("feature_code")):
                        continue
                    name = row.get("name")
                    if not name:
                        continue
                    try:
                        lat = float(row.get("latitude", 0))
                        lon = float(row.get("longitude", 0))
                    except (TypeError, ValueError):
                        continue
                    admin1 = row.get("admin1") or ""
                    country_code = row.get("country_code") or row.get("country") or ""
                    dedup_key = _make_dedup_key(name, admin1, country_code)
                    if dedup_key in suggestions_set:
                        continue
                    suggestions_set.add(dedup_key)
                    suggestions_ordered.append({
                        "name": _make_display(name, admin1, country_code),
                        "lat": lat,
                        "lon": lon,
                        "population": row.get("population") or 0,
                    })
                    if len(suggestions_ordered) >= MAX_SUGGESTIONS:
                        break
        except Exception as exc:
            logger.warning("Localized Open-Meteo autocomplete failed for %r: %s", prefix, exc)
        return suggestions_ordered[:MAX_SUGGESTIONS]

    # ── Tier 1: Redis ZRANGEBYLEX ─────────────────────────────────────────────
    if len(suggestions_ordered) < MIN_SUGGESTIONS:
        try:
            r = _get_redis()
            if r is not None:
                redis_hits = search_redis(r, prefix, limit=MAX_SUGGESTIONS)
                for s in redis_hits:
                    try:
                        lat = float(s["lat"])
                        lon = float(s["lon"])
                    except (KeyError, TypeError, ValueError):
                        continue
                    # Redis entries are pre-filtered popular cities; no feature_code available
                    raw_name = s.get("name", "")
                    # Parse existing "City, Country" display from Redis into components
                    parts = [p.strip() for p in raw_name.split(",")]
                    city_name = parts[0] if parts else raw_name
                    country_part = parts[-1] if len(parts) > 1 else ""
                    dedup_key = _make_dedup_key(city_name, None, country_part)
                    if dedup_key not in suggestions_set:
                        suggestions_set.add(dedup_key)
                        suggestions_ordered.append({
                            "name": raw_name,
                            "lat": lat,
                            "lon": lon,
                            "population": s.get("population", 0) or 0,
                        })
        except Exception as exc:
            log_redis_event(
                "operation_failed",
                component="autocomplete.search_redis",
                fallback="sqlite",
                error=str(exc),
            )

    # ── Tier 2: SQLite fallback ───────────────────────────────────────────────
    if len(suggestions_ordered) < MIN_SUGGESTIONS:
        conn = None
        try:
            conn = get_connection()
            sqlite_rows = search_by_prefix(
                conn, prefix, limit=MAX_SUGGESTIONS - len(suggestions_ordered)
            )
            for row in sqlite_rows:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
                city_name = row["name"]
                country_part = row.get("country") or row.get("country_code") or ""
                admin1_part = row.get("admin1") or ""
                dedup_key = _make_dedup_key(city_name, admin1_part, country_part)
                if dedup_key not in suggestions_set:
                    suggestions_set.add(dedup_key)
                    suggestions_ordered.append({
                        "name": _make_display(city_name, admin1_part, country_part),
                        "lat": lat,
                        "lon": lon,
                        "population": row.get("population", 0) or 0,
                    })
        except Exception as exc:
            logger.warning("SQLite autocomplete failed for prefix %r: %s", prefix, exc)
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    # ── Tier 3: Open-Meteo external fallback ──────────────────────────────────
    if len(suggestions_ordered) < MIN_SUGGESTIONS:
        try:
            url = "https://geocoding-api.open-meteo.com/v1/search"
            params = {
                "name": prefix,
                "count": 15,
                "language": normalized_language,
                "format": "json"
            }
            resp = requests.get(url, params=params, timeout=2.0)
            if resp.status_code == 200:
                data = resp.json()
                rows = sorted(
                    data.get("results", []),
                    key=lambda r: r.get("population", 0) or 0,
                    reverse=True,
                )
                for row in rows:
                    if not _is_ppl(row.get("feature_code")):
                        continue
                    name = row.get("name")
                    if not name:
                        continue
                    try:
                        lat = float(row.get("latitude", 0))
                        lon = float(row.get("longitude", 0))
                    except (TypeError, ValueError):
                        continue
                    admin1 = row.get("admin1") or ""
                    country_code = row.get("country_code") or ""
                    country_display = row.get("country") or country_code
                    dedup_key = _make_dedup_key(name, admin1, country_code)
                    if dedup_key not in suggestions_set:
                        suggestions_set.add(dedup_key)
                        suggestions_ordered.append({
                            "name": _make_display(name, admin1, country_display),
                            "lat": lat,
                            "lon": lon,
                            "population": row.get("population") or 0,
                        })
                        if len(suggestions_ordered) >= MAX_SUGGESTIONS:
                            break
        except Exception as exc:
            logger.warning("Open-Meteo fallback failed for prefix %r: %s", prefix, exc)

    # Sort by population descending so major cities always appear first
    suggestions_ordered.sort(key=lambda s: s.get("population", 0) or 0, reverse=True)

    return suggestions_ordered[:MAX_SUGGESTIONS]


@app.post("/api/autocomplete")
async def autocomplete(req: AutocompleteRequest, request: Request):
    """
    Fast, LLM-free autocomplete.
    Tier 1: Redis ZRANGEBYLEX on the top-1000 cities index (sub-ms).
    Tier 2: SQLite indexed LIKE fallback for full coverage.
    Tier 3: Open-Meteo geocoding fallback when local tiers are insufficient.
    Returns a raw JSON bytes response to minimise serialisation overhead.
    Never raises HTTP 500 — degrades to an empty suggestion list on failure.
    """
    await enforce_rate_limit(request, "autocomplete", _get_redis())
    q = req.query.strip()
    if len(q) < MIN_QUERY_LEN:
        return Response(
            content='{"suggestions":[]}',
            media_type="application/json",
        )

    try:
        results = _tiered_search(q, req.language)
    except Exception as exc:
        logger.exception("Autocomplete failed for query %r: %s", q, exc)
        results = []

    payload = json.dumps({"suggestions": results}, ensure_ascii=False)
    return Response(content=payload, media_type="application/json")


@app.get("/api/search-city")
def search_city(q: str = "", lang: str = "en"):
    """
    GET alias of the same tiered search — kept for backwards compatibility.
    Never raises HTTP 500 — degrades to an empty suggestion list on failure.
    """
    prefix = (q or "").strip()
    if len(prefix) < MIN_QUERY_LEN:
        return Response(
            content='{"suggestions":[]}',
            media_type="application/json",
        )

    try:
        results = _tiered_search(prefix, lang)
    except Exception as exc:
        logger.exception("search-city failed for query %r: %s", prefix, exc)
        results = []

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
async def get_city_advice_endpoint(req: GetCityAdviceRequest, request: Request):
    await enforce_rate_limit(request, "get-city-advice", _get_redis())
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
async def get_forecast_summary_endpoint(req: GetForecastSummaryRequest, request: Request):
    await enforce_rate_limit(request, "get-forecast-summary", _get_redis())
    summary = get_forecast_summary(req.city, req.weather_summary, req.language, req.unit)
    return GetForecastSummaryResponse(summary=summary)


# ─── Global weather chatbot (Feature 2) ──────────────────────────────────────
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def strip_control_chars(cls, value: str) -> str:
        cleaned = "".join(ch for ch in value if ch == "\n" or ch == "\t" or ord(ch) >= 32)
        if not cleaned.strip():
            raise ValueError("Message content cannot be empty.")
        return cleaned


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1, max_length=40)
    language: str = Field(default="en", min_length=2, max_length=8)
    unit: str = Field(default="metric", min_length=2, max_length=16)
    session_id: str | None = Field(default=None, max_length=128)
    city_name: str | None = Field(default=None, max_length=120)
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)


class ChatResponse(BaseModel):
    reply: str


_atmosmind_agent: AtmosMindAgent | None = None

AGENT_ERROR_REPLY_TR = (
    "Hava durumu asistanı şu an yanıt veremiyor. Lütfen birkaç saniye sonra tekrar deneyin."
)
AGENT_ERROR_REPLY_EN = (
    "The weather assistant cannot respond right now. Please try again in a moment."
)
AGENT_NETWORK_ERROR_REPLY_TR = (
    "Hava durumu asistanına bağlanılamadı. İnternet bağlantınızı kontrol edip tekrar deneyin."
)
AGENT_NETWORK_ERROR_REPLY_EN = (
    "Could not reach the weather assistant. Check your internet connection and try again."
)


def _is_network_error(exc: Exception) -> bool:
    msg = str(exc).casefold()
    network_markers = (
        "name resolution",
        "clientconnectordnserror",
        "temporary failure",
        "connect timeout",
        "connection refused",
        "network is unreachable",
        "nodename nor servname",
        "failed to resolve",
    )
    return any(marker in msg for marker in network_markers)


def _agent_error_reply(language: str, exc: Exception | None = None) -> str:
    code = (language or "en").strip().casefold().split("-")[0]
    is_tr = code == "tr"
    if exc is not None and _is_network_error(exc):
        return AGENT_NETWORK_ERROR_REPLY_TR if is_tr else AGENT_NETWORK_ERROR_REPLY_EN
    return AGENT_ERROR_REPLY_TR if is_tr else AGENT_ERROR_REPLY_EN


def get_atmosmind_agent() -> AtmosMindAgent:
    """Lazy singleton for the LangChain weather agent."""
    global _atmosmind_agent
    if _atmosmind_agent is None:
        configure_langsmith_tracing()
        _atmosmind_agent = create_atmosmind_agent()
    return _atmosmind_agent


def _format_sse(payload: dict[str, str] | str) -> str:
    if isinstance(payload, str):
        return f"data: {payload}\n\n"
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _sse_error_chunk(language: str, exc: Exception | None = None) -> str:
    """Unified SSE error frame — always includes top-level ``error`` for the React parser."""
    message = _agent_error_reply(language, exc)
    return _format_sse({"error": message, "type": "error", "reply": message})


async def chat_sse_generator(req: ChatRequest, session_id: str):
    """
    Single SSE generator for /api/chat — success tokens and failures share one stream.

    Always terminates with ``data: [DONE]`` so the frontend never hangs waiting.
    """
    yield _format_sse({"type": "status", "phase": "started"})
    user_input = req.messages[-1].content
    session_hint = f"{session_id[:8]}…" if len(session_id) > 8 else session_id
    logger.info(
        "Chat SSE stream started session_hint=%s language=%s langsmith_tracing=%s",
        session_hint,
        req.language,
        langsmith_tracing_active(),
    )

    safety = await evaluate_chat_input_safety(user_input, req.language)
    if not safety.allowed:
        if safety.message:
            yield _format_sse({"type": "token", "content": safety.message})
        yield _format_sse("[DONE]")
        return

    try:
        agent = get_atmosmind_agent()
        yield _format_sse({"type": "status", "phase": "agent"})
        async for token in agent.astream(
            session_id=session_id,
            user_input=user_input,
            language=req.language,
            unit=req.unit,
            city_name=req.city_name,
            latitude=req.latitude,
            longitude=req.longitude,
        ):
            if token:
                yield _format_sse({"type": "token", "content": token})
    except Exception as exc:
        logger.error("Agent Error: %s", str(exc), exc_info=True)
        yield _sse_error_chunk(req.language, exc)
    finally:
        yield _format_sse("[DONE]")


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest, request: Request):
    await enforce_rate_limit(request, "chat", _get_redis())
    session_id = (req.session_id or "").strip() or get_client_ip(request)

    return StreamingResponse(
        chat_sse_generator(req, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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


def _batch_item_from_payload(city_display: str, data: dict) -> BatchWeatherItem:
    if "error" in data:
        return BatchWeatherItem(city=city_display, error=data["error"])
    return BatchWeatherItem(
        city=city_display,
        temperature=data.get("temperature"),
        condition=data.get("condition"),
        weather_code=data.get("weather_code"),
    )


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
async def weather_batch(req: BatchWeatherRequest, request: Request):
    """
    Fetch current temperature (and condition) for popular city names.

    Redis is checked first per city. Cache misses are filled with chunked Open-Meteo
    batch requests (one HTTP call per chunk, not N parallel single-city calls).
    """
    await enforce_rate_limit(request, "weather-batch", _get_redis())
    cities = [c.strip() for c in (req.cities or []) if c and c.strip()]
    if not cities:
        return BatchWeatherResponse(results=[], temperatures={})

    r = _get_redis()
    results_by_city: dict[str, BatchWeatherItem] = {}
    to_fetch: list[tuple[str, float, float]] = []
    name_only: list[str] = []

    for city_display in cities:
        coords = _resolve_coords(city_display)
        if coords is None:
            name_only.append(city_display)
            continue

        lat, lon = coords
        cached = get_cached_weather(r, lat, lon) if r else None
        if cached is not None:
            results_by_city[city_display] = BatchWeatherItem(
                city=city_display,
                temperature=cached.get("temperature"),
                condition=cached.get("condition"),
                weather_code=cached.get("weather_code"),
            )
        else:
            to_fetch.append((city_display, lat, lon))

    if to_fetch:
        coords = [(lat, lon) for _city, lat, lon in to_fetch]
        batch_data = get_current_weather_batch_by_coords(coords)
        for (city_display, lat, lon), data in zip(to_fetch, batch_data):
            if "error" not in data and r:
                payload = {
                    "temperature": data.get("temperature"),
                    "condition": data.get("condition"),
                    "weather_code": data.get("weather_code"),
                }
                set_cached_weather(r, lat, lon, payload, ttl=900)
            results_by_city[city_display] = _batch_item_from_payload(city_display, data)

    for city_display in name_only:
        try:
            results_by_city[city_display] = _fetch_one_weather_by_name(city_display)
        except Exception as e:
            logger.exception("Batch weather failed for %r: %s", city_display, e)
            results_by_city[city_display] = BatchWeatherItem(
                city=city_display, error=GENERIC_ERROR_MESSAGE
            )

    ordered = [results_by_city.get(c, BatchWeatherItem(city=c, error="Unknown")) for c in cities]
    temperatures = {item.city: item.temperature for item in ordered if item.temperature is not None}
    return BatchWeatherResponse(results=ordered, temperatures=temperatures)


# ─── City detail: unified forecast + lifestyle indices ───────────────────────


class WeatherDetailRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    language: str = Field(default="en", min_length=2, max_length=8)
    unit: Literal["metric", "imperial"] = "metric"


@app.post("/api/weather/detail", response_model=WeatherDetailResponse)
async def weather_detail_endpoint(req: WeatherDetailRequest, request: Request):
    """
    Unified city-detail payload for the frontend.

    Fetches Open-Meteo forecast and lifestyle indices concurrently on the server.
    The browser must not call Open-Meteo directly.
    """
    await enforce_rate_limit(request, "weather-detail", _get_redis())
    try:
        return await fetch_weather_detail(
            req.latitude,
            req.longitude,
            language=req.language,
            unit=req.unit,
            redis_client=_get_redis(),
        )
    except ForecastUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Weather forecast temporarily unavailable.") from exc
    except Exception as exc:
        logger.exception(
            "Weather detail failed for (%s, %s): %s",
            req.latitude,
            req.longitude,
            exc,
        )
        raise HTTPException(status_code=503, detail="Weather forecast temporarily unavailable.") from exc


# ─── Lifestyle indices (air quality, UV, pollen, visibility, dew point) ───────


@app.get("/api/lifestyle-indices", response_model=LifestyleIndicesResponse)
async def lifestyle_indices_endpoint(
    request: Request,
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
):
    """
    Dynamic lifestyle indices for the city detail view.

    Fetches Open-Meteo Forecast + Air Quality APIs in parallel for the given coordinates.
    """
    await enforce_rate_limit(request, "lifestyle-indices", _get_redis())
    return await fetch_lifestyle_indices(latitude, longitude, redis_client=_get_redis())

