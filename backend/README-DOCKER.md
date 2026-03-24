# Running the Backend with Docker

## Prerequisites

- Docker and Docker Compose installed
- (Optional) `GOOGLE_API_KEY` in `.env` or export for AI features

## Quick start

From the `backend` directory:

```bash
# Build and start app + Redis
docker compose up --build

# Or in detached mode
docker compose up -d --build
```

- **API:** http://localhost:8000  
- **Redis:** localhost:6379  

## First run

- `entrypoint.sh` runs `seed_cities.py` automatically if the database is empty (first start).
- SQLite DB is stored in `./data/cities.db` (host volume).
- Redis data is stored in a named volume `redis_data` (persisted across restarts).

## Environment

- `REDIS_URL=redis://redis:6379` (set in compose)
- `DATABASE_PATH=/app/data/cities.db` (set in compose)
- Pass `GOOGLE_API_KEY` via `.env` or:  
  `GOOGLE_API_KEY=your_key docker compose up --build`

## Commands

```bash
# Stop
docker compose down

# Stop and remove Redis data
docker compose down -v

# Rebuild after code changes
docker compose up --build
```
