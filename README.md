# AtmosMind

AI-powered weather dashboard with multilingual UX, localized city search, and a weather-focused AI assistant.

## What AtmosMind Does

- Real-time weather for any city (current, hourly, daily).
- Localized city autocomplete with Unicode-safe rendering.
- AI assistant for weather-only guidance (chat, advice, forecast summary).
- Favorites saved by coordinates (not static names), then localized dynamically by active language.
- Metric/Imperial unit support and route-aware SEO metadata (About, Privacy, city detail pages).

## Highlights

- **Full-stack**: React + TypeScript frontend (`frontend/`), FastAPI backend (`backend/`).
- **AI integration**: Gemini-powered chat and weather advice.
- **Performance**: Redis + SQLite tiered autocomplete and cache.
- **Localization**: 12 languages, RTL support for Arabic, locale-aware text handling.
- **Unicode integrity**: City names are preserved as returned by APIs (no transliteration in the UI path).
- **Responsive UI**: Desktop three-column header; tablet/mobile hamburger + slide-out (`Navbar.tsx`, `hooks/useMediaQuery.ts`).

## Tech Stack

- **Frontend**: React, TypeScript, Tailwind CSS, Framer Motion, Recharts, React Router, i18next/react-i18next
- **Backend**: Python, FastAPI, Uvicorn
- **AI**: Google Gemini
- **Data**: Open-Meteo (weather + geocoding), SQLite, Redis
- **Containerization**: Docker + Docker Compose

## Repository Layout

```text
AtmosMind-Weather-main/
├─ .npmrc                    # legacy-peer-deps (optional root-level npm)
├─ docker-compose.yml
├─ backend/
│  ├─ api.py, ai_chat.py, ai_advice.py, …
│  ├─ Dockerfile
│  └─ requirements.txt
└─ frontend/                 # Create React App root (Vercel Root Directory)
   ├─ .npmrc                 # legacy-peer-deps for Vercel / local install
   ├─ package.json
   ├─ src/
   ├─ public/
   ├─ tailwind.config.js
   └─ Dockerfile            # production nginx image (Docker Compose)
```

## Prerequisites

- Docker Desktop (recommended for full stack)
- Google Gemini API key (AI features)
- Node.js 18+ (local frontend)
- Python 3.10+ (local backend)

## Quick Start (Docker)

1. `cd backend && cp .env.example .env` — set `GOOGLE_API_KEY` and `REDIS_PASSWORD`.
2. From repo root: `docker compose up --build`
3. Frontend [http://localhost:3000](http://localhost:3000) · Backend [http://localhost:8000](http://localhost:8000)

## Local Development (Without Docker)

Set `REACT_APP_API_URL=http://localhost:8000` in `frontend/.env` if your API client expects it.

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
python seed_cities.py
uvicorn api:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm start
```

`npm install` respects `frontend/.npmrc` (`legacy-peer-deps=true`) to avoid peer dependency resolution errors.

## Deploying the Frontend on Vercel

Use these **Project Settings → General → Build & Development**:

| Setting | Value |
|--------|--------|
| **Root Directory** | `frontend` |
| **Install Command** | `npm install` *(default; picks up `frontend/.npmrc`)* |
| **Build Command** | `npm run build` |
| **Output Directory** | `build` |

Framework Preset: **Create React App** (optional; the above overrides are enough).

Ensure production API URL is set under **Environment Variables**, e.g. `REACT_APP_API_URL=https://your-backend.example.com` (no trailing slash), then redeploy.

The repo includes `frontend/vercel.json` so client-side routes (e.g. `/about`, `/weather/...`) resolve correctly after refresh.

If you still see an **empty** `frontend/weatherapicodes` folder locally (left over from a locked directory during migration), close any process using that path and delete the folder manually—it is not part of the intended layout.

## Environment Variables

**Backend** (`backend/.env`): see `backend/.env.example` — `GOOGLE_API_KEY`, `REDIS_URL`, `REDIS_PASSWORD`, `DATABASE_PATH`, etc.

## API Overview

- `POST /api/autocomplete` — localized city suggestions  
- `POST /api/weather/batch` — batch weather for cards  
- `POST /api/ai-weather`, `/api/chat`, `/api/get-city-advice`, `/api/get-forecast-summary` — AI endpoints  

## Internationalization

Supported: `en`, `tr`, `fr`, `es`, `de`, `ja`, `zh`, `ko`, `ru`, `ar`, `it`, `pt`. Arabic uses RTL. Favorites are coordinate-based.

## Frontend production build

```bash
cd frontend
npm run build
```

Output: `frontend/build`.

## License

MIT
