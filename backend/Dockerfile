# Backend Dockerfile - FastAPI + SQLite + Redis client
FROM python:3.11-slim

# SQLite is built into Python; Redis is a Python client. No extra system deps required.

WORKDIR /app

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .
# Strip any CRLF/BOM from the entrypoint (Windows checkouts) before making it executable
RUN sed -i -e 's/\r$//' -e '1s/^\xEF\xBB\xBF//' /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

# Non-root runtime user — /app/data must be writable (volume mount or image layer).
RUN adduser --disabled-password --gecos "" appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app \
    && chmod 755 /app \
    && chmod 775 /app/data

# SQLite DB will be stored in /app/data (mounted volume in compose)
ENV DATABASE_PATH=/app/data/cities.db
EXPOSE 8000

USER appuser

ENTRYPOINT ["./entrypoint.sh"]
