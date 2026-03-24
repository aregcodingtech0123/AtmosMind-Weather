"""
Seed the SQLite cities table from the bundled cities.json.
This replaces the previous Open-Meteo API approach so seeding works
offline inside Docker (no network dependency at startup).

Run manually:  python seed_cities.py
Auto-run:      entrypoint.sh calls this when the DB is empty.
"""
import json
import logging
import sqlite3
import sys
from pathlib import Path

# Ensure we can import from the same directory
sys.path.insert(0, str(Path(__file__).resolve().parent))
from database import DB_PATH, get_connection, init_schema

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# cities.json lives next to this script (and is COPY'd into /app/ in Docker)
CITIES_JSON = Path(__file__).resolve().parent / "cities.json"


def load_cities_from_json() -> list[dict]:
    """Load city records from the bundled cities.json file."""
    if not CITIES_JSON.exists():
        logger.error("cities.json not found at %s", CITIES_JSON)
        return []
    with open(CITIES_JSON, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        logger.error("cities.json must contain a JSON array")
        return []
    logger.info("Loaded %d cities from %s", len(data), CITIES_JSON)
    return data


def run_seed() -> None:
    conn = get_connection()
    try:
        # Ensure schema exists
        init_schema(conn)

        # Wipe any stale rows (idempotent re-seeding)
        conn.execute("DELETE FROM cities")
        conn.commit()

        cities = load_cities_from_json()
        if not cities:
            logger.error("No city data found — check cities.json. Exiting without seeding.")
            return

        inserted = 0
        seen: set[tuple[str, str]] = set()

        for c in cities:
            name = (c.get("name") or "").strip()
            country = (c.get("country") or "").strip()
            if not name or not country:
                continue

            key = (name.casefold(), country.casefold())
            if key in seen:
                continue
            seen.add(key)

            try:
                lat = float(c.get("latitude", 0))
                lon = float(c.get("longitude", 0))
            except (TypeError, ValueError):
                logger.warning("Invalid lat/lon for %s — skipping", name)
                continue

            name_lower = name.casefold()
            try:
                conn.execute(
                    "INSERT INTO cities (name, country, latitude, longitude, is_popular, name_lower) "
                    "VALUES (?, ?, ?, ?, 1, ?)",
                    (name, country, lat, lon, name_lower),
                )
                inserted += 1
            except sqlite3.Error as e:
                logger.warning("Insert failed for %s: %s", name, e)

        conn.commit()
        logger.info("Seeded %d cities into %s", inserted, DB_PATH)

    except Exception as e:
        logger.exception("Seed failed: %s", e)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_seed()
