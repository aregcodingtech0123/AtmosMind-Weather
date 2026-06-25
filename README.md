# AtmosMind

AtmosMind is an AI-powered global weather platform with a multilingual React dashboard, tiered city search, coordinate-based favorites, lifestyle quality indices, and a weather-scoped LangChain assistant. All Open-Meteo and air-quality traffic is proxied through the FastAPI backend so the browser never calls third-party weather APIs directly.

---

## Features

### Weather dashboard

- **City detail** — Current conditions, hourly charts, and 7-day forecasts loaded via `POST /api/weather/detail` (backend aggregates Open-Meteo forecast + lifestyle indices in one request).
- **Lifestyle indices** — Air quality, UV, pollen, and visibility/dew point on city pages, with per-card fallback when upstream data is unavailable.
- **Dynamic backgrounds** — WMO weather-code themes on city detail pages (clear, rainy, stormy, snowy, cloudy).
- **Units** — Metric/imperial toggle applied across the UI.
- **Popular cities** — Home grid temperatures via `POST /api/weather/batch` with Redis-backed caching.

### Search and favorites

- **Tiered autocomplete** — Redis (top popular cities) → SQLite prefix search → Open-Meteo geocoding fallback.
- **Coordinate-based favorites** — Stored as lat/lon; labels refresh when the UI language changes.
- **Geolocation** — Reverse geocoding for human-readable city names.

### AI assistant

- **LangChain agent** — Gemini `gemini-2.5-flash` with async weather tools and sliding-window Redis chat memory.
- **SSE streaming** — `POST /api/chat` streams tokens and status phases to the floating chatbot.
- **AI advice & forecast summaries** — On-demand narrative summaries and clothing/activity tips per city.
- **Input moderation** — Chat prompts screened before the agent runs.

### Internationalization

- **45 UI languages** — `i18next` with locale files under `frontend/public/locales/`.
- **RTL** — Arabic, Urdu, and Persian layouts supported.

### Security and operations

- **Rate limiting** — Redis sliding-window limits on chat, autocomplete, batch weather, and lifestyle endpoints (in-memory fallback when Redis is down).
- **CORS allowlist** — Configurable via `ALLOWED_ORIGINS`.
- **Production hardening** — FastAPI `/docs` disabled when `ENV=production`; non-root Docker user; security headers on Vercel (see [SECURITY.md](SECURITY.md)).
- **Structured logging** — [Loguru](https://github.com/Delgan/loguru): colorized logs in development, JSON on stdout in production.
- **LangSmith** — Optional LangChain tracing when `LANGCHAIN_TRACING_V2` and `LANGCHAIN_API_KEY` are set.
- **Open-Meteo throttling** — Batched outbound requests, retries on 429, and configurable cache pre-warm limits.

---

## Tech stack

| Area | Technologies |
|------|----------------|
| **Frontend** | React 19, TypeScript, Tailwind CSS, Framer Motion, Recharts, React Router v7, i18next |
| **Backend** | Python 3.11, FastAPI, Uvicorn, Pydantic, SQLite, httpx |
| **AI** | Google GenAI SDK, LangChain, `langchain-google-genai`, Redis chat memory |
| **Cache** | Redis (autocomplete index, weather cache, air-quality cache, rate limits) |
| **Observability** | Loguru, LangSmith (optional) |
| **CI/CD** | GitHub Actions, Docker Compose |
| **Deploy** | Vercel (frontend), Docker (full stack) |

---

## Repository layout

```text
AtmosMind-Weather-main/
├── .github/workflows/ci.yml   # Parallel pytest + Jest on main/master
├── docker-compose.yml         # app + redis + frontend (nginx)
├── README.md
├── SECURITY.md
├── backend/
│   ├── api.py                 # FastAPI routes, rate limits, SSE chat
│   ├── weather_detail.py        # Unified city-detail weather + lifestyle fetch
│   ├── lifestyle_indices.py     # Air quality / UV / pollen (parallel + cached)
│   ├── open_meteo_client.py     # Throttled batch Open-Meteo client
│   ├── langchain_agent.py       # Agent, streaming, tool loop
│   ├── langchain_memory.py      # Redis windowed chat history
│   ├── langchain_tools.py       # Async coordinate-first tools
│   ├── redis_cache.py           # Weather, air-quality, autocomplete caches
│   ├── security.py              # Rate limits, moderation, CORS helpers
│   ├── logging_config.py        # Loguru bootstrap + structured helpers
│   ├── observability.py         # LangSmith env bootstrap
│   ├── database.py              # SQLite search + schema
│   ├── tests/                   # Pytest suite
│   ├── Dockerfile
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.tsx
    │   ├── components/          # UI, charts, chatbot, lifestyle grid
    │   ├── hooks/               # useCityDetail, geolocation, favorites
    │   ├── services/api.ts      # Backend API client
    │   └── utils/               # chatStream, requestGuard, mappers
    ├── public/locales/          # i18n JSON (45 languages)
    ├── nginx.conf               # Proxies /api → backend in Docker
    ├── Dockerfile
    └── package.json
```

---

## Getting started

### Prerequisites

- **Docker Desktop** (recommended for local full-stack)
- **Google Gemini API key** (AI chat, advice, summaries)
- **Node.js 18+** and **Python 3.11+** (optional, for bare-metal dev)

### Option A — Docker Compose (recommended)

1. Copy and edit backend environment:

   ```bash
   cp backend/.env.example backend/.env
   ```

   Set at minimum:

   - `GOOGLE_API_KEY`
   - `REDIS_PASSWORD` (used by the Redis container and `REDIS_URL`)

2. From the repository root:

   ```bash
   docker compose up --build
   ```

3. Open:

   | Service | URL |
   |---------|-----|
   | Frontend | http://localhost:3000 |
   | Backend API | http://localhost:8000 |
   | API docs (dev only) | http://localhost:8000/docs |

   In Docker, the frontend nginx container proxies `/api/*` to the backend. For local `npm start`, the CRA proxy in `package.json` forwards `/api` to port 8000.

### Option B — Bare metal

**Backend**

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python seed_cities.py   # if cities.db is missing
uvicorn api:app --reload --port 8000
```

Ensure Redis is running and `REDIS_URL` in `backend/.env` is correct.

**Frontend**

```bash
cd frontend
npm install
npm start
```

Runs at http://localhost:3000 with API calls proxied to http://localhost:8000.

---

## API overview

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/weather/detail` | City detail: forecast + lifestyle indices |
| `GET` | `/api/lifestyle-indices` | Lifestyle indices only (lat/lon query) |
| `POST` | `/api/weather/batch` | Popular-city current weather |
| `POST` | `/api/autocomplete` | Tiered city search |
| `POST` | `/api/chat` | SSE LangChain weather assistant |
| `POST` | `/api/get-city-advice` | AI clothing/activity advice |
| `POST` | `/api/get-forecast-summary` | AI forecast narrative |
| `POST` | `/api/ai-weather` | Legacy Gemini weather tool flow |

---

## Environment variables

### Backend (`backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Google Gemini API key |
| `REDIS_PASSWORD` | Docker | Redis auth password |
| `REDIS_URL` | No | e.g. `redis://:password@redis:6379` |
| `DATABASE_PATH` | No | SQLite path (default `/app/data/cities.db` in Docker) |
| `ALLOWED_ORIGINS` | No | Comma-separated CORS origins |
| `ENV` | No | Set `production` to disable `/docs` and enable JSON logs |
| `LOG_LEVEL` | No | Loguru level (default `INFO` in production) |
| `PREWARM_CITIES_LIMIT` | No | Startup cache pre-warm cap (default `80`, `0` disables) |
| `LANGCHAIN_TRACING_V2` | No | `true` to enable LangSmith |
| `LANGCHAIN_API_KEY` | No | LangSmith API key |
| `LANGCHAIN_PROJECT` | No | LangSmith project (default `atmosmind-agent`) |
| `CHAT_MEMORY_WINDOW_K` | No | Chat memory window (5–10, default `10`) |

See [backend/.env.example](backend/.env.example) for the full list.

### Frontend

| Variable | Required | Description |
|----------|----------|-------------|
| `REACT_APP_API_URL` | Production | API host only, e.g. `https://api.example.com` (no `/api` suffix) |
| `REACT_APP_ADMIN_CONTACT_MAIL` | Contact form | EmailJS recipient |
| `REACT_APP_EMAILJS_*` | Contact form | EmailJS keys |

For local CRA dev, omit `REACT_APP_API_URL` to use the `package.json` proxy.

---

## Testing

**Backend** (58+ tests):

```bash
cd backend
python -m pytest -q
```

**Frontend** (Jest + React Testing Library):

```bash
cd frontend
npm test -- --watchAll=false
```

---

## CI/CD

GitHub Actions workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every push and pull request to `main` or `master`:

- **test-backend** — Python 3.11, Redis service, `pytest`
- **test-frontend** — Node 20, `npm ci`, Jest (non-interactive)

If either job fails, the workflow exits with a non-zero status. Configure **branch protection** and Vercel **“Wait for GitHub Checks”** so failed tests block merges and deployments.

---

## Deployment

### Frontend (Vercel)

- **Root directory:** `frontend`
- **Build command:** `npm run build`
- **Output directory:** `build`
- **Env:** `REACT_APP_API_URL` → your public API origin

SPA routing is configured in `frontend/vercel.json`.

### Full stack (Docker)

Use root `docker-compose.yml` on any host with Docker. Mount `backend/data` for persistent SQLite. Point your domain at the frontend container (port 80) or place a reverse proxy in front.

### Production checklist

- Set `ENV=production` on the backend
- Set `ALLOWED_ORIGINS` to your Vercel domain(s)
- Use strong `REDIS_PASSWORD`
- Never commit `.env` files
- Enable required CI status checks before deploy

---

## Security

See [SECURITY.md](SECURITY.md) for HTTP headers, CSP notes, and backend hardening details.

---

## License

This project is provided as-is for educational and portfolio use. Review third-party API terms ([Open-Meteo](https://open-meteo.com/), [Google AI](https://ai.google.dev/)) before production use.
