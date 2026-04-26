import os
import json
import time

cities = [
    {"id": "london", "name": "London", "defaultName": "London, United Kingdom", "lat": 51.5085, "lon": -0.1257},
    {"id": "newyorkcity", "name": "New York", "defaultName": "New York, United States", "lat": 40.7143, "lon": -74.0060},
    {"id": "tokyo", "name": "Tokyo", "defaultName": "Tokyo, Japan", "lat": 35.6895, "lon": 139.6917},
    {"id": "istanbul", "name": "Istanbul", "defaultName": "Istanbul, Turkiye", "lat": 41.0138, "lon": 28.9603},
    {"id": "sydney", "name": "Sydney", "defaultName": "Sydney, Australia", "lat": -33.8678, "lon": 151.2073},
    {"id": "paris", "name": "Paris", "defaultName": "Paris, France", "lat": 48.8534, "lon": 2.3488},
    {"id": "dubai", "name": "Dubai", "defaultName": "Dubai, United Arab Emirates", "lat": 25.0772, "lon": 55.3093},
    {"id": "bangkok", "name": "Bangkok", "defaultName": "Bangkok, Thailand", "lat": 13.7540, "lon": 100.5014},
    {"id": "rome", "name": "Rome", "defaultName": "Rome, Italy", "lat": 41.8947, "lon": 12.4839},
    {"id": "berlin", "name": "Berlin", "defaultName": "Berlin, Germany", "lat": 52.5244, "lon": 13.4105},
    {"id": "seoul", "name": "Seoul", "defaultName": "Seoul, South Korea", "lat": 37.5665, "lon": 126.9780},
    {"id": "doha", "name": "Doha", "defaultName": "Doha, Qatar", "lat": 25.2854, "lon": 51.5310},
    {"id": "riodejaneiro", "name": "Rio de Janeiro", "defaultName": "Rio de Janeiro, Brazil", "lat": -22.9068, "lon": -43.1729},
    {"id": "cairo", "name": "Cairo", "defaultName": "Cairo, Egypt", "lat": 30.0444, "lon": 31.2357},
    {"id": "toronto", "name": "Toronto", "defaultName": "Toronto, Canada", "lat": 43.7001, "lon": -79.4163},
    {"id": "auckland", "name": "Auckland", "defaultName": "Auckland, New Zealand", "lat": -36.8485, "lon": 174.7633},
    {"id": "amsterdam", "name": "Amsterdam", "defaultName": "Amsterdam, Netherlands", "lat": 52.3676, "lon": 4.9041},
    {"id": "macau", "name": "Macau", "defaultName": "Macau", "lat": 22.1987, "lon": 113.5439},
    {"id": "hongkong", "name": "Hong Kong", "defaultName": "Hong Kong", "lat": 22.3193, "lon": 114.1694},
    {"id": "singapore", "name": "Singapore", "defaultName": "Singapore, SG", "lat": 1.3521, "lon": 103.8198},
    {"id": "kualalumpur", "name": "Kuala Lumpur", "defaultName": "Kuala Lumpur, Malaysia", "lat": 3.1390, "lon": 101.6869},
    {"id": "antalya", "name": "Antalya", "defaultName": "Antalya, Turkiye", "lat": 36.8969, "lon": 30.7133},
    {"id": "mecca", "name": "Mecca", "defaultName": "Mecca, Saudi Arabia", "lat": 21.3891, "lon": 39.8579},
    {"id": "venice", "name": "Venice", "defaultName": "Venezia, Italy", "lat": 45.4408, "lon": 12.3155},
    {"id": "buenosaires", "name": "Buenos Aires", "defaultName": "Buenos Aires, Argentina", "lat": -34.6037, "lon": -58.3816},
    {"id": "losangeles", "name": "Los Angeles", "defaultName": "Los Angeles, United States", "lat": 34.0522, "lon": -118.2437},
    {"id": "capetown", "name": "Cape Town", "defaultName": "Cape Town, South Africa", "lat": -33.9249, "lon": 18.4241},
    {"id": "edinburgh", "name": "Edinburgh", "defaultName": "Edinburgh, United Kingdom", "lat": 55.9533, "lon": -3.1883},
    {"id": "lisbon", "name": "Lisbon", "defaultName": "Lisbon, Portugal", "lat": 38.7223, "lon": -9.1393},
    {"id": "madrid", "name": "Madrid", "defaultName": "Madrid, Spain", "lat": 40.4168, "lon": -3.7038},
    {"id": "munich", "name": "Munich", "defaultName": "Munich, Germany", "lat": 48.1374, "lon": 11.5755},
    {"id": "budapest", "name": "Budapest", "defaultName": "Budapest, Hungary", "lat": 47.4979, "lon": 19.0402},
    {"id": "vienna", "name": "Vienna", "defaultName": "Wien, Austria", "lat": 48.2082, "lon": 16.3738},
    {"id": "marrakesh", "name": "Marrakesh", "defaultName": "Marakesh, Morocco", "lat": 31.6295, "lon": -7.9811},
    {"id": "frankfurt", "name": "Frankfurt", "defaultName": "Frankfurt, Germany", "lat": 50.1109, "lon": 8.6821},
    {"id": "warsaw", "name": "Warsaw", "defaultName": "Warsaw, Poland", "lat": 52.2297, "lon": 21.0122},
    {"id": "mumbai", "name": "Mumbai", "defaultName": "Mumbai, India", "lat": 19.0760, "lon": 72.8777},
    {"id": "newdelhi", "name": "New Delhi", "defaultName": "New Delhi, India", "lat": 28.6139, "lon": 77.2090},
    {"id": "mexicocity", "name": "Mexico City", "defaultName": "Mexico City, Mexico", "lat": 19.4326, "lon": -99.1332}
]

languages = ['en', 'tr', 'fr', 'es', 'de', 'ja', 'zh', 'hi', 'ru', 'ar', 'it', 'pt', 'bn', 'ur', 'tl', 'vi', 'uk', 'pl', 'nl', 'fi', 'da', 'no', 'sv', 'ha', 'ta', 'ms', 'id', 'jv', 'su', 'hu', 'cs', 'el', 'ro', 'fa', 'th', 'sw', 'az', 'kk', 'uz', 'ky', 'tk', 'ko']

try:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel("gemini-2.5-flash", generation_config={"response_mime_type": "application/json"})
except Exception as e:
    print(e)
    model = None

results = []

def generate_batch(cities_sub):
    names = [c["name"] for c in cities_sub]
    prompt = f"Translate the following list of cities: {names} into ALL of these 42 languages strictly: {languages}. Return a JSON object where the root keys are the city english names, and the values are objects mapping each of the 42 language codes to the translated city name. Return ONLY valid JSON."
    
    if model:
        resp = model.generate_content(prompt)
        return json.loads(resp.text)
    return {}

print("Requesting AI translations...")
# We do this in one shot to save time
try:
    translations_map = generate_batch(cities)
except Exception as e:
    print("Translation failed, using fallback:", e)
    translations_map = {}

# Assemble the TS string
ts_content = "import { SupportedLanguage } from '../context/SettingsContext';\n\n"
ts_content += "export interface PopularCity {\n  id: string;\n  defaultName: string;\n  names: Record<SupportedLanguage, string>;\n  latitude: number;\n  longitude: number;\n}\n\n"
ts_content += "export const POPULAR_CITIES: PopularCity[] = [\n"

for c in cities:
    tr_obj = translations_map.get(c["name"])
    if not tr_obj or len(tr_obj) < 42:
        # Fallback building
        tr_obj = {l: c["name"] for l in languages}
        # Inject standard manual ones to be safe
        ko_map = {'London': '런던', 'New York': '뉴욕', 'Tokyo': '도쿄', 'Istanbul': '이스탄불', 'Sydney': '시드니', 'Paris': '파리', 'Dubai': '두바이', 'Bangkok': '방콕'}
        tr_map = {'London': 'Londra', 'New York': 'New York', 'Tokyo': 'Tokyo', 'Istanbul': 'İstanbul', 'Sydney': 'Sidney', 'Paris': 'Paris', 'Dubai': 'Dubai', 'Rome': 'Roma', 'Berlin': 'Berlin'}
        tr_obj['ko'] = ko_map.get(c["name"], c["name"])
        tr_obj['tr'] = tr_map.get(c["name"], c["name"])

    names_str = json.dumps(tr_obj, ensure_ascii=False)
    ts_content += f'  {{\n    id: "{c["id"]}",\n    defaultName: "{c["defaultName"]}",\n    names: {names_str} as Record<SupportedLanguage, string>,\n    latitude: {c["lat"]},\n    longitude: {c["lon"]}\n  }},\n'

ts_content += "];\n"

# Verify folder exists
os.makedirs('frontend/src/data', exist_ok=True)
with open('frontend/src/data/popularCities.ts', 'w', encoding='utf-8') as f:
    f.write(ts_content)

print('Successfully generated frontend/src/data/popularCities.ts')
