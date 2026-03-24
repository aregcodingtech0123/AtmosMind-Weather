"""
SQLite schema and helpers for cities autocomplete.
"""
import logging
import os
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

# Allow override via env (e.g. Docker: /app/data/cities.db)
DB_PATH = Path(os.getenv("DATABASE_PATH", str(Path(__file__).resolve().parent / "cities.db")))

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS cities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    is_popular INTEGER NOT NULL DEFAULT 0,
    name_lower TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cities_name_lower ON cities(name_lower);
CREATE INDEX IF NOT EXISTS idx_cities_is_popular ON cities(is_popular);
"""


def get_connection():
    """Return a connection to the SQLite database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create tables and indexes if they do not exist."""
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    except sqlite3.Error as e:
        logger.exception("Failed to init schema: %s", e)
        raise


def is_database_empty() -> bool:
    """Return True if the cities table does not exist or has no rows."""
    if not DB_PATH.exists():
        return True
    try:
        conn = get_connection()
        cur = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='cities'"
        )
        if cur.fetchone()[0] == 0:
            conn.close()
            return True
        cur = conn.execute("SELECT COUNT(*) FROM cities")
        count = cur.fetchone()[0]
        conn.close()
        return count == 0
    except Exception:
        return True


def search_by_prefix(conn: sqlite3.Connection, prefix: str, limit: int = 10) -> list[dict]:
    """
    Search cities by name prefix (case-insensitive).
    Returns list of dicts with keys: name, country, latitude, longitude.
    """
    if not prefix or limit <= 0:
        return []
    prefix_clean = prefix.strip().casefold()
    if not prefix_clean:
        return []
    pattern = f"{prefix_clean}%"
    try:
        cur = conn.execute(
            "SELECT name, country, latitude, longitude FROM cities WHERE name_lower LIKE ? ORDER BY name_lower LIMIT ?",
            (pattern, limit),
        )
        return [dict(row) for row in cur.fetchall()]
    except sqlite3.Error as e:
        logger.exception("SQLite search failed for prefix %r: %s", prefix, e)
        return []


def fetch_popular_for_redis(conn: sqlite3.Connection, limit: int = 1000) -> list[dict]:
    """Fetch up to `limit` popular cities for loading into Redis."""
    try:
        cur = conn.execute(
            "SELECT name, country, latitude, longitude FROM cities WHERE is_popular = 1 ORDER BY id LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]
    except sqlite3.Error as e:
        logger.exception("Failed to fetch popular cities: %s", e)
        return []


def get_coordinates_by_display_name(conn: sqlite3.Connection, display_name: str) -> dict | None:
    """
    Resolve "Name, Country" to coordinates from the cities table.
    Returns dict with name, country, latitude, longitude or None if not found.
    """
    if not display_name or not isinstance(display_name, str):
        return None
    parts = display_name.strip().split(",", 1)
    name = parts[0].strip() if parts else ""
    country = parts[1].strip() if len(parts) > 1 else ""
    if not name:
        return None
    name_lower = name.casefold()
    country_lower = country.casefold()
    try:
        # Compare country with Python casefold to avoid SQLite LOWER unicode limitations.
        cur = conn.execute(
            "SELECT name, country, latitude, longitude FROM cities WHERE name_lower = ?",
            (name_lower,),
        )
        for row in cur.fetchall():
            row_country = str(row["country"]).strip().casefold()
            if row_country == country_lower:
                return dict(row)
        return None
    except sqlite3.Error as e:
        logger.exception("get_coordinates_by_display_name failed for %r: %s", display_name, e)
        return None
