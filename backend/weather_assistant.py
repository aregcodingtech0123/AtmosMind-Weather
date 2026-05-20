import os
from datetime import datetime
import logging
import google.generativeai as genai
import requests
import json

from city_name_normalize import city_name_geocode_variants

# ────────────────────────────────────────────────
# 1. AYARLAR
# ────────────────────────────────────────────────
# API Key'ini buraya gir
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)
logger = logging.getLogger(__name__)

GENERIC_ERROR = "An unexpected error occurred while processing your request. Please try again later."

# ────────────────────────────────────────────────
# 2. HAVA DURUMU ÇEKEN FONKSİYON (Open-Meteo: geocoding + forecast)
# ────────────────────────────────────────────────

def geocode_city(display_name: str) -> dict | None:
    """
    Resolve "Name, Country" or city name to latitude/longitude via Open-Meteo geocoding.
    Returns {"latitude": float, "longitude": float} or None on failure.
    """
    if not display_name or not str(display_name).strip():
        return None
    # Use base name (before comma) for geocoding
    query = str(display_name).strip().split(",")[0].strip()
    if not query:
        return None
    variants = city_name_geocode_variants(query)
    for v in variants:
        for lang in ("en", "tr"):
            hit = _open_meteo_geocode_first(v, language=lang)
            if hit is not None:
                return {"latitude": hit["lat"], "longitude": hit["lon"]}
    return None


# WMO weather code → short condition string (Open-Meteo uses WMO codes)
def _weather_code_to_condition(code: int) -> str:
    if code is None:
        return "Unknown"
    wmo = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Foggy",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    return wmo.get(int(code), "Unknown")


def _open_meteo_geocode_first(query: str, language: str = "en") -> dict | None:
    """
    Return {"lat", "lon", "city"} for the top geocoding hit, or None.
    """
    if not query or not str(query).strip():
        return None
    q = str(query).strip()
    try:
        geo_url = (
            "https://geocoding-api.open-meteo.com/v1/search"
            f"?name={requests.utils.quote(q)}&count=1&language={language}&format=json"
        )
        geo_resp = requests.get(geo_url, timeout=10)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
    except Exception:
        return None
    results = geo_data.get("results") if isinstance(geo_data, dict) else None
    if not results:
        return None
    first = results[0]
    try:
        lat = float(first.get("latitude"))
        lon = float(first.get("longitude"))
    except (TypeError, ValueError):
        return None
    resolved_name = first.get("name") or q
    if isinstance(first.get("admin1"), str):
        resolved_name = f"{resolved_name}, {first['admin1']}"
    return {"lat": lat, "lon": lon, "city": resolved_name}


def _resolve_city_location(city_name: str) -> dict:
    """
    Geocode a city name to coordinates and a display label.
    Tries normalized variants (handles Turkish suffixes / apostrophe forms) and
    multiple API languages before failing.
    Returns {"lat", "lon", "city"} or {"error": "...", "hint": "...", ...}.
    """
    if not city_name or not str(city_name).strip():
        return {"error": "City name is required."}

    raw_input = str(city_name).strip()
    variants = city_name_geocode_variants(raw_input)
    if not variants:
        return {"error": "City name is required."}

    languages = ("en", "tr")
    attempts_log: list[str] = []

    for v in variants:
        for lang in languages:
            attempts_log.append(f"{v!r} (lang={lang})")
            hit = _open_meteo_geocode_first(v, language=lang)
            if hit is not None:
                if v != raw_input or lang != "en":
                    logger.debug(
                        "Geocode resolved %r → %r via query=%r lang=%s",
                        raw_input,
                        hit.get("city"),
                        v,
                        lang,
                    )
                return hit

    logger.info("Geocode failed for %r after tries: %s", raw_input, attempts_log[:12])
    return {
        "error": (
            f"No location found for '{raw_input}'. "
            "Try the city name without grammar endings (e.g. Kopenhag or Copenhagen), or add the country."
        ),
        "original_city_argument": raw_input,
        "hint": (
            "The name may include a grammatical suffix (e.g. Turkish -'a/-e) or local spelling. "
            "Ask the user to confirm the standard city name in Latin script, or retry with a shorter base form."
        ),
        "geocode_attempts": attempts_log[:16],
    }


def get_live_weather(city_name: str):
    """
    Fetches current weather for a city using Open-Meteo (geocoding + forecast).
    No API key required. Returns same shape as before for compatibility.
    """
    location = _resolve_city_location(city_name)
    if "error" in location:
        return location

    lat = location["lat"]
    lon = location["lon"]
    resolved_name = location["city"]

    # 2. Forecast: current weather at lat, lon
    try:
        forecast_url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&current_weather=true"
            "&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
        )
        fc_resp = requests.get(forecast_url, timeout=10)
        fc_resp.raise_for_status()
        fc_data = fc_resp.json()
    except requests.RequestException as e:
        return {"error": f"Weather API failed: could not fetch forecast for {resolved_name}. Please try again later."}
    except Exception as e:
        logger.exception("Forecast unexpected error for %r: %s", resolved_name, e)
        return {"error": GENERIC_ERROR}

    if not isinstance(fc_data, dict):
        return {"error": "Forecast API returned invalid data."}

    current_weather = fc_data.get("current_weather")
    current = fc_data.get("current", {})

    if not current_weather:
        return {"error": "Forecast API did not return current weather."}

    try:
        temperature = current_weather.get("temperature")
        if temperature is not None:
            temperature = round(float(temperature), 1)
        wind_speed = current_weather.get("windspeed")
        if wind_speed is not None:
            wind_speed = round(float(wind_speed), 1)
        weather_code = current_weather.get("weathercode")
        condition = _weather_code_to_condition(weather_code)

        humidity = None
        if isinstance(current, dict) and "relative_humidity_2m" in current:
            humidity = current.get("relative_humidity_2m")
            if humidity is not None:
                humidity = int(float(humidity))

        time_str = current_weather.get("time")
        local_time_24 = None
        if time_str and isinstance(time_str, str):
            try:
                # ISO format e.g. 2024-01-15T14:00
                parsed = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                local_time_24 = parsed.strftime("%H:%M")
            except ValueError:
                pass

        weather_info = {
            "city": resolved_name,
            "temperature": temperature,
            "condition": condition,
            "humidity": humidity,
            "wind": wind_speed,
            "local_time": local_time_24,
        }
        return weather_info
    except (TypeError, ValueError) as e:
        logger.exception("Forecast parse error for %r: %s", resolved_name, e)
        return {"error": GENERIC_ERROR}


def get_weather_forecast(city_name: str, forecast_days: int = 7) -> dict:
    """
    Fetches current conditions plus daily and hourly forecast for a city.
    Used by the chat assistant for future-date questions.
    """
    location = _resolve_city_location(city_name)
    if "error" in location:
        return location

    lat = location["lat"]
    lon = location["lon"]
    resolved_name = location["city"]
    days = max(1, min(int(forecast_days or 7), 16))

    try:
        forecast_url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&current_weather=true"
            "&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
            "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max"
            "&hourly=temperature_2m,precipitation_probability,weather_code,wind_speed_10m"
            f"&forecast_days={days}"
            "&timezone=auto"
        )
        fc_resp = requests.get(forecast_url, timeout=10)
        fc_resp.raise_for_status()
        fc_data = fc_resp.json()
    except requests.RequestException:
        return {"error": f"Weather API failed: could not fetch forecast for {resolved_name}. Please try again later."}
    except Exception as e:
        logger.exception("Forecast fetch error for %r: %s", resolved_name, e)
        return {"error": GENERIC_ERROR}

    if not isinstance(fc_data, dict):
        return {"error": "Forecast API returned invalid data."}

    current_weather = fc_data.get("current_weather") or {}
    current = fc_data.get("current") or {}
    daily = fc_data.get("daily") or {}
    hourly = fc_data.get("hourly") or {}

    try:
        current_block = None
        if current_weather:
            temperature = current_weather.get("temperature")
            if temperature is not None:
                temperature = round(float(temperature), 1)
            wind_speed = current_weather.get("windspeed")
            if wind_speed is not None:
                wind_speed = round(float(wind_speed), 1)
            weather_code = current_weather.get("weathercode")
            humidity = current.get("relative_humidity_2m")
            if humidity is not None:
                humidity = int(float(humidity))
            current_block = {
                "temperature": temperature,
                "condition": _weather_code_to_condition(weather_code),
                "humidity": humidity,
                "wind_kmh": wind_speed,
                "observed_at": current_weather.get("time"),
            }

        daily_forecast = []
        dates = daily.get("time") or []
        for i, date_str in enumerate(dates):
            code = (daily.get("weather_code") or [None])[i]
            t_max = (daily.get("temperature_2m_max") or [None])[i]
            t_min = (daily.get("temperature_2m_min") or [None])[i]
            precip = (daily.get("precipitation_sum") or [None])[i]
            wind_max = (daily.get("wind_speed_10m_max") or [None])[i]
            daily_forecast.append({
                "date": date_str,
                "temp_max_c": round(float(t_max), 1) if t_max is not None else None,
                "temp_min_c": round(float(t_min), 1) if t_min is not None else None,
                "condition": _weather_code_to_condition(code),
                "precipitation_mm": round(float(precip), 1) if precip is not None else None,
                "wind_max_kmh": round(float(wind_max), 1) if wind_max is not None else None,
            })

        hourly_forecast = []
        hourly_times = hourly.get("time") or []
        for i, time_str in enumerate(hourly_times[:48]):
            code = (hourly.get("weather_code") or [None])[i]
            temp = (hourly.get("temperature_2m") or [None])[i]
            precip_prob = (hourly.get("precipitation_probability") or [None])[i]
            wind = (hourly.get("wind_speed_10m") or [None])[i]
            hourly_forecast.append({
                "time": time_str,
                "temperature_c": round(float(temp), 1) if temp is not None else None,
                "condition": _weather_code_to_condition(code),
                "precipitation_probability_pct": int(precip_prob) if precip_prob is not None else None,
                "wind_kmh": round(float(wind), 1) if wind is not None else None,
            })

        return {
            "city": resolved_name,
            "timezone": fc_data.get("timezone"),
            "current": current_block,
            "daily": daily_forecast,
            "hourly": hourly_forecast,
        }
    except (TypeError, ValueError) as e:
        logger.exception("Forecast parse error for %r: %s", resolved_name, e)
        return {"error": GENERIC_ERROR}


def get_current_weather_by_coords(lat: float, lon: float) -> dict:
    """
    Fetch current weather for given coordinates using Open-Meteo (no geocoding).
    Returns dict with temperature, condition, weather_code, or {"error": "..."}.
    Used by batch endpoint with Redis cache.
    """
    try:
        forecast_url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&current_weather=true"
            "&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
        )
        fc_resp = requests.get(forecast_url, timeout=10)
        fc_resp.raise_for_status()
        fc_data = fc_resp.json()
    except requests.RequestException as e:
        logger.warning("Forecast request error for coords (%s, %s): %s", lat, lon, e)
        return {"error": "Unable to fetch weather data at the moment. Please try again later."}
    except Exception as e:
        logger.exception("Unexpected forecast error for coords (%s, %s): %s", lat, lon, e)
        return {"error": GENERIC_ERROR}

    if not isinstance(fc_data, dict):
        return {"error": "Invalid forecast data"}

    current_weather = fc_data.get("current_weather")
    if not current_weather:
        return {"error": "No current weather"}

    try:
        temperature = current_weather.get("temperature")
        if temperature is not None:
            temperature = round(float(temperature), 1)
        weather_code = current_weather.get("weathercode")
        condition = _weather_code_to_condition(weather_code)
        return {
            "temperature": temperature,
            "condition": condition,
            "weather_code": weather_code,
        }
    except (TypeError, ValueError):
        return {"error": "Failed to parse forecast"}

# ────────────────────────────────────────────────
# 3. GEMINI TOOL TANIMI
# ────────────────────────────────────────────────
tools_schema = [{
    "name": "get_weather_in_city",
    "description": "Belirtilen şehir için güncel hava durumunu verir.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "city": {"type": "STRING", "description": "Şehir adı (Örn: Istanbul, Ankara)"},
        },
        "required": ["city"]
    }
}]

model = genai.GenerativeModel(model_name='gemini-2.5-flash', tools=tools_schema)

# ────────────────────────────────────────────────
# 4. ASİSTAN FONKSİYONU
# ────────────────────────────────────────────────
def hava_durumu_asistani(soru):
    logger.info("Received AI weather request")
    messages = [{"role": "user", "parts": [soru]}]

    try:
        response = model.generate_content(messages)
        part = response.candidates[0].content.parts[0]
    except Exception as e:
        logger.exception("Gemini request failed: %s", e)
        return GENERIC_ERROR

    if part.function_call:
        fc = part.function_call
        city_name = fc.args.get("city")
        logger.info("Fetching live weather via tool for city")

        api_data = get_live_weather(city_name)
        logger.debug("Tool weather payload fetched successfully")

        messages.append(response.candidates[0].content)
        messages.append({
            "role": "user",
            "parts": [{"function_response": {"name": "get_weather_in_city", "response": api_data}}]
        })

        final_res = model.generate_content(messages)
        return f"\nGEMINI CEVABI: {final_res.text}"

    else:
        return f"\nGEMINI CEVABI (Toolsuz): {response.text}"

