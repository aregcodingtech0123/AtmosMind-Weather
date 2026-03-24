# Backend Dockerfile - FastAPI + SQLite + Redis client
FROM python:3.11-slim

# SQLite is built into Python; Redis is a Python client. No extra system deps required.

WORKDIR /app

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .
RUN chmod +x /app/entrypoint.sh

# Optional: run as non-root (requires volume to be writable)
# RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
# USER appuser

# SQLite DB will be stored in /app/data (mounted volume in compose)
ENV DATABASE_PATH=/app/data/cities.db
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
