# AtmosMind

AI-powered weather dashboard with multilingual UX, localized city search, and a weather-focused AI assistant.

## What AtmosMind Does

- Real-time weather for any city (current, hourly, daily).
- Localized city autocomplete with Unicode-safe rendering.
- AI assistant for weather-only guidance (chat, advice, forecast summary).
- Favorites saved by coordinates (not static names), then localized dynamically by active language.
- Metric/Imperial unit support and route-aware SEO metadata (About, Privacy, city detail pages).

## Highlights

- **Full-stack**: React + TypeScript frontend (`frontend/weatherapicodes`), FastAPI backend (`backend/`).
- **AI integration**: Gemini-powered chat and weather advice.
- **Performance**: Redis + SQLite tiered autocomplete and cache.
- **Localization**: 12 languages, RTL support for Arabic, locale-aware text handling.
- **Unicode integrity**: City names are preserved as returned by APIs (no transliteration in the UI path).
- **Responsive UI**: Desktop uses a three-column header; tablet and mobile use a hamburger menu and slide-out panel so controls never overlap (see `Navbar.tsx` and `hooks/useMediaQuery.ts`).

## Tech Stack

- **Frontend**: React, TypeScript, Tailwind CSS, Framer Motion, Recharts, React Router, i18next/react-i18next
- **Backend**: Python, FastAPI, Uvicorn
- **AI**: Google Gemini
- **Data**: Open-Meteo (weather + geocoding), SQLite, Redis
- **Containerization**: Docker + Docker Compose

## Repository Layout

```text
AtmosMind-Weather-main/
├─ docker-compose.yml      # Root orchestration (backend + redis + frontend)
├─ backend/
│  ├─ api.py
│  ├─ ai_chat.py
│  ├─ ai_advice.py
│  ├─ weather_assistant.py
│  ├─ redis_cache.py
│  ├─ database.py
│  ├─ seed_cities.py
│  ├─ Dockerfile
│  ├─ docker-compose.yml   # Optional: backend-only compose
│  └─ requirements.txt
└─ frontend/weatherapicodes/
   ├─ src/
   │  ├─ components/        # Navbar, SearchBar, weather UI, chatbot, etc.
   │  ├─ hooks/             # useWeather, useFavorites, useMediaQuery, …
   │  ├─ context/
   │  ├─ services/        # API client (language, units, geocoding)
   │  └─ pages/             # About, Privacy
   ├─ public/locales/       # i18n JSON (12 languages)
   └─ package.json
```

## Prerequisites

- Docker Desktop (recommended for full stack)
- Google Gemini API key (for AI features)
- Node.js 18+ (local frontend only)
- Python 3.10+ (local backend only)

## Quick Start (Docker)

1. Create backend environment file:

```bash
cd backend
cp .env.example .env
```

2. Set at least:

```env
GOOGLE_API_KEY=your_key_here
REDIS_PASSWORD=change_this_to_a_long_random_password
```

3. From the **repository root** (where `docker-compose.yml` lives), run:

```bash
docker compose up --build
```

Services:

- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Backend**: [http://localhost:8000](http://localhost:8000)
- **API docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

## Local Development (Without Docker)

Run backend and frontend in two terminals. Point the frontend at the API if needed (e.g. `REACT_APP_API_URL=http://localhost:8000` in `frontend/weatherapicodes/.env` when the app reads it).

### Backend

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
pip install -r requirements.txt
python seed_cities.py
uvicorn api:app --reload --port 8000
```

### Frontend

```bash
cd frontend/weatherapicodes
npm install
npm start
```

## Environment Variables

`backend/.env` (see `backend/.env.example`):

```env
GOOGLE_API_KEY=
REDIS_URL=redis://:your_password@redis:6379/0
REDIS_PASSWORD=
DATABASE_PATH=/app/data/cities.db
```

## API Overview

- `POST /api/autocomplete` — localized city suggestions
- `POST /api/weather/batch` — batch weather for cards
- `POST /api/ai-weather` — AI weather summary by city
- `POST /api/chat` — weather assistant chat
- `POST /api/get-city-advice` — personalized weather advice
- `POST /api/get-forecast-summary` — detailed forecast narrative

## Internationalization

- Supported languages: `en`, `tr`, `fr`, `es`, `de`, `ja`, `zh`, `ko`, `ru`, `ar`, `it`, `pt`
- Arabic uses RTL layout (`dir="rtl"` via settings).
- Favorites use a coordinate-based ID; labels refresh when the language changes.
- City names stay raw Unicode end-to-end.

## Frontend Build

```bash
cd frontend/weatherapicodes
npm run build
```

Production static output is written to `frontend/weatherapicodes/build` (used by the frontend Docker image).

## License

MIT
