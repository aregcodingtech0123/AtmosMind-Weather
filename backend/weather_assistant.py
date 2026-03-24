import os
from datetime import datetime
import logging
import google.generativeai as genai
import requests
import json

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
    try:
        geo_url = (
            "https://geocoding-api.open-meteo.com/v1/search"
            f"?name={requests.utils.quote(query)}&count=1&language=en&format=json"
        )
        geo_resp = requests.get(geo_url, timeout=10)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
    except Exception:
        return None
    results = geo_data.get("results") if isinstance(geo_data, dict) else None
    if not results or len(results) == 0:
        return None
    first = results[0]
    try:
        lat = float(first.get("latitude"))
        lon = float(first.get("longitude"))
        return {"latitude": lat, "longitude": lon}
    except (TypeError, ValueError):
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


def get_live_weather(city_name: str):
    """
    Fetches current weather for a city using Open-Meteo (geocoding + forecast).
    No API key required. Returns same shape as before for compatibility.
    """
    if not city_name or not str(city_name).strip():
        return {"error": "City name is required."}

    city_name = str(city_name).strip()

    # 1. Geocoding: city name → latitude, longitude
    try:
        geo_url = (
            "https://geocoding-api.open-meteo.com/v1/search"
            f"?name={requests.utils.quote(city_name)}&count=1&language=en&format=json"
        )
        geo_resp = requests.get(geo_url, timeout=10)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
    except requests.RequestException as e:
        return {"error": f"Geocoding failed: could not resolve city '{city_name}'. Please check the name and try again."}
    except Exception as e:
        logger.exception("Geocoding unexpected error for %r: %s", city_name, e)
        return {"error": GENERIC_ERROR}

    results = geo_data.get("results") if isinstance(geo_data, dict) else None
    if not results or len(results) == 0:
        return {"error": f"No location found for '{city_name}'. Try a different spelling or a more specific name."}

    first = results[0]
    try:
        lat = float(first.get("latitude"))
        lon = float(first.get("longitude"))
    except (TypeError, ValueError):
        return {"error": "Geocoding returned invalid coordinates."}

    # Optional: use resolved name from API
    resolved_name = first.get("name") or city_name
    if isinstance(first.get("admin1"), str):
        resolved_name = f"{resolved_name}, {first['admin1']}"

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

