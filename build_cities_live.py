"""
Regenerates frontend/src/data/popularCities.ts using Open-Meteo geocoding API
to get accurate native city names for all 42 supported languages.
"""
import json, requests, time, os

LANGUAGES = ['en', 'tr', 'fr', 'es', 'de', 'ja', 'zh', 'hi', 'ru', 'ar', 'it', 'pt',
             'bn', 'ur', 'tl', 'vi', 'uk', 'pl', 'nl', 'fi', 'da', 'no', 'sv', 'ha',
             'ta', 'ms', 'id', 'jv', 'su', 'hu', 'cs', 'el', 'ro', 'fa', 'th', 'sw',
             'az', 'kk', 'uz', 'ky', 'tk', 'ko']

CITIES = [
    {"id": "london",       "en": "London",        "lat": 51.5085,  "lon": -0.1257,   "defaultName": "London, United Kingdom"},
    {"id": "newyorkcity",  "en": "New York",       "lat": 40.7143,  "lon": -74.0060,  "defaultName": "New York, United States"},
    {"id": "tokyo",        "en": "Tokyo",          "lat": 35.6895,  "lon": 139.6917,  "defaultName": "Tokyo, Japan"},
    {"id": "istanbul",     "en": "Istanbul",       "lat": 41.0138,  "lon": 28.9603,   "defaultName": "Istanbul, Turkiye"},
    {"id": "sydney",       "en": "Sydney",         "lat": -33.8678, "lon": 151.2073,  "defaultName": "Sydney, Australia"},
    {"id": "paris",        "en": "Paris",          "lat": 48.8534,  "lon": 2.3488,    "defaultName": "Paris, France"},
    {"id": "dubai",        "en": "Dubai",          "lat": 25.0772,  "lon": 55.3093,   "defaultName": "Dubai, United Arab Emirates"},
    {"id": "bangkok",      "en": "Bangkok",        "lat": 13.7540,  "lon": 100.5014,  "defaultName": "Bangkok, Thailand"},
    {"id": "rome",         "en": "Rome",           "lat": 41.8947,  "lon": 12.4839,   "defaultName": "Rome, Italy"},
    {"id": "berlin",       "en": "Berlin",         "lat": 52.5244,  "lon": 13.4105,   "defaultName": "Berlin, Germany"},
    {"id": "seoul",        "en": "Seoul",          "lat": 37.5665,  "lon": 126.9780,  "defaultName": "Seoul, South Korea"},
    {"id": "doha",         "en": "Doha",           "lat": 25.2854,  "lon": 51.5310,   "defaultName": "Doha, Qatar"},
    {"id": "riodejaneiro", "en": "Rio de Janeiro", "lat": -22.9068, "lon": -43.1729,  "defaultName": "Rio de Janeiro, Brazil"},
    {"id": "cairo",        "en": "Cairo",          "lat": 30.0444,  "lon": 31.2357,   "defaultName": "Cairo, Egypt"},
    {"id": "toronto",      "en": "Toronto",        "lat": 43.7001,  "lon": -79.4163,  "defaultName": "Toronto, Canada"},
    {"id": "auckland",     "en": "Auckland",       "lat": -36.8485, "lon": 174.7633,  "defaultName": "Auckland, New Zealand"},
    {"id": "amsterdam",    "en": "Amsterdam",      "lat": 52.3676,  "lon": 4.9041,    "defaultName": "Amsterdam, Netherlands"},
    {"id": "macau",        "en": "Macau",          "lat": 22.1987,  "lon": 113.5439,  "defaultName": "Macau"},
    {"id": "hongkong",     "en": "Hong Kong",      "lat": 22.3193,  "lon": 114.1694,  "defaultName": "Hong Kong"},
    {"id": "singapore",    "en": "Singapore",      "lat": 1.3521,   "lon": 103.8198,  "defaultName": "Singapore, SG"},
    {"id": "kualalumpur",  "en": "Kuala Lumpur",   "lat": 3.1390,   "lon": 101.6869,  "defaultName": "Kuala Lumpur, Malaysia"},
    {"id": "antalya",      "en": "Antalya",        "lat": 36.8969,  "lon": 30.7133,   "defaultName": "Antalya, Turkiye"},
    {"id": "mecca",        "en": "Mecca",          "lat": 21.3891,  "lon": 39.8579,   "defaultName": "Mecca, Saudi Arabia"},
    {"id": "venice",       "en": "Venice",         "lat": 45.4408,  "lon": 12.3155,   "defaultName": "Venezia, Italy"},
    {"id": "buenosaires",  "en": "Buenos Aires",   "lat": -34.6037, "lon": -58.3816,  "defaultName": "Buenos Aires, Argentina"},
    {"id": "losangeles",   "en": "Los Angeles",    "lat": 34.0522,  "lon": -118.2437, "defaultName": "Los Angeles, United States"},
    {"id": "capetown",     "en": "Cape Town",      "lat": -33.9249, "lon": 18.4241,   "defaultName": "Cape Town, South Africa"},
    {"id": "edinburgh",    "en": "Edinburgh",      "lat": 55.9533,  "lon": -3.1883,   "defaultName": "Edinburgh, United Kingdom"},
    {"id": "lisbon",       "en": "Lisbon",         "lat": 38.7223,  "lon": -9.1393,   "defaultName": "Lisbon, Portugal"},
    {"id": "madrid",       "en": "Madrid",         "lat": 40.4168,  "lon": -3.7038,   "defaultName": "Madrid, Spain"},
    {"id": "munich",       "en": "Munich",         "lat": 48.1374,  "lon": 11.5755,   "defaultName": "Munich, Germany"},
    {"id": "budapest",     "en": "Budapest",       "lat": 47.4979,  "lon": 19.0402,   "defaultName": "Budapest, Hungary"},
    {"id": "vienna",       "en": "Vienna",         "lat": 48.2082,  "lon": 16.3738,   "defaultName": "Wien, Austria"},
    {"id": "marrakesh",    "en": "Marrakesh",      "lat": 31.6295,  "lon": -7.9811,   "defaultName": "Marakesh, Morocco"},
    {"id": "frankfurt",    "en": "Frankfurt",      "lat": 50.1109,  "lon": 8.6821,    "defaultName": "Frankfurt, Germany"},
    {"id": "warsaw",       "en": "Warsaw",         "lat": 52.2297,  "lon": 21.0122,   "defaultName": "Warsaw, Poland"},
    {"id": "mumbai",       "en": "Mumbai",         "lat": 19.0760,  "lon": 72.8777,   "defaultName": "Mumbai, India"},
    {"id": "newdelhi",     "en": "New Delhi",      "lat": 28.6139,  "lon": 77.2090,   "defaultName": "New Delhi, India"},
    {"id": "mexicocity",   "en": "Mexico City",    "lat": 19.4326,  "lon": -99.1332,  "defaultName": "Mexico City, Mexico"},
]

def fetch_name_for_lang(city_en: str, lat: float, lon: float, lang: str) -> str:
    """Fetch the localized city name from Open-Meteo for the given language."""
    try:
        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {"name": city_en, "count": 5, "language": lang, "format": "json"}
        r = requests.get(url, params=params, timeout=4)
        if r.status_code != 200:
            return city_en
        results = r.json().get("results", [])
        # Find the best match: closest coordinates
        best = None
        best_dist = float("inf")
        for row in results:
            rlat = row.get("latitude", 0)
            rlon = row.get("longitude", 0)
            dist = abs(rlat - lat) + abs(rlon - lon)
            if dist < best_dist:
                best_dist = dist
                best = row
        if best and best_dist < 2.0:  # within ~2 degrees
            return best.get("name", city_en)
    except Exception as e:
        print(f"  WARN: {city_en}/{lang}: {e}")
    return city_en

print(f"Fetching translations for {len(CITIES)} cities x {len(LANGUAGES)} languages...")
results = []
for city in CITIES:
    names = {}
    print(f"  Processing: {city['en']}")
    for lang in LANGUAGES:
        if lang == 'en':
            names['en'] = city['en']
            continue
        name = fetch_name_for_lang(city['en'], city['lat'], city['lon'], lang)
        names[lang] = name
        time.sleep(0.05)  # Be polite to Open-Meteo
    results.append({**city, "names": names})
    print(f"    Done. Sample: tr={names.get('tr').encode('ascii','replace').decode()}, ko={names.get('ko').encode('ascii','replace').decode()}, ja={names.get('ja').encode('ascii','replace').decode()}, ar={names.get('ar').encode('ascii','replace').decode()}")

# Write to TypeScript file
os.makedirs("frontend/src/data", exist_ok=True)
out_lines = [
    "import { SupportedLanguage } from '../context/SettingsContext';\n\n",
    "export interface PopularCity {\n",
    "  id: string;\n",
    "  defaultName: string;\n",
    "  names: Record<SupportedLanguage, string>;\n",
    "  latitude: number;\n",
    "  longitude: number;\n",
    "}\n\n",
    "export const POPULAR_CITIES: PopularCity[] = [\n",
]
for c in results:
    names_json = json.dumps(c["names"], ensure_ascii=False)
    out_lines.append(
        f'  {{\n'
        f'    id: "{c["id"]}",\n'
        f'    defaultName: "{c["defaultName"]}",\n'
        f'    names: {names_json} as Record<SupportedLanguage, string>,\n'
        f'    latitude: {c["lat"]},\n'
        f'    longitude: {c["lon"]}\n'
        f'  }},\n'
    )
out_lines.append("];\n")

with open("frontend/src/data/popularCities.ts", "w", encoding="utf-8") as f:
    f.writelines(out_lines)

print("\nDone! frontend/src/data/popularCities.ts has been regenerated.")
