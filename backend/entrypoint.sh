#!/bin/sh
set -e

# Ensure data dir exists for SQLite
mkdir -p /app/data

# Seed cities if database is empty (first run)
if python -c "
from database import is_database_empty
exit(0 if is_database_empty() else 1)
" 2>/dev/null; then
  echo "Database empty: running seed_cities.py..."
  python seed_cities.py || true
else
  echo "Database already populated; skipping seed."
fi

# Start the application
exec uvicorn api:app --host 0.0.0.0 --port 8000
