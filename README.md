# Karwan-e-Khizr

A real-time transit app for Islamabad/Rawalpindi with AI-powered journey planning, live bus tracking, and voice commands.

Built for the **Bano Qabil × Alibaba Cloud AI Hackathon**.

## Features

- **Live Bus Tracking** — Real-time vehicle positions on MapLibre map
- **Journey Planning** — Multi-modal route finding (bus + walking) with fare calculation
- **AI Assistant** — Voice/text commands using LLM intent extraction
- **ETA Predictions** — LightGBM model trained on synthetic simulation data
- **Road-Following Routes** — Polylines snap to actual roads via OSRM

## Prerequisites

- Node.js 18+ (frontend)
- Python 3.13+ (backend)
- Docker (for PostgreSQL/PostGIS)
- pip (Python package manager)

## Setup

### 1. Start the database

```bash
cd backend
docker-compose up -d
```

This starts PostgreSQL with PostGIS on `localhost:5432`.

### 2. Initialize the database

```bash
cd backend
python -m alembic upgrade head
```

### 3. Start the backend

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Start the frontend

```bash
cd frontend/web
npm install
npm run dev
```

The frontend runs at `http://localhost:5173` (or next available port).

## Configuration

Backend environment variables (in `backend/.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/karwan` | PostgreSQL connection |
| `GEMINI_API_KEY` | — | Google Gemini API key for AI |
| `GROQ_API_KEY` | — | Groq API key (fallback) |

Frontend environment variables (in `frontend/web/.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000/api/v1` | Backend API URL |
| `VITE_USE_MOCK_DATA` | `false` | Set to `true` for demo without backend |

## Architecture

```
karwan-e-khizr/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routers
│   │   ├── core/             # Config, database
│   │   ├── db/               # SQLAlchemy models
│   │   ├── eta/              # ETA prediction (LightGBM)
│   │   ├── geospatial/       # Location resolution, routing
│   │   ├── journey/          # Journey planning engine
│   │   └── simulation/       # Vehicle simulation engine
│   ├── scripts/              # Data scripts
│   └── tests/
├── frontend/
│   └── web/
│       ├── src/
│       │   ├── components/   # UI components
│       │   ├── screens/      # App screens
│       │   └── services/     # API clients
│       └── shared/           # Types, hooks, services
└── problems.md               # QA bug tracker
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/transit/realtime/vehicles` | GET | All active vehicles |
| `/api/v1/transit/realtime/vehicles/{id}` | GET | Single vehicle position |
| `/api/v1/transit/realtime/vehicles/{id}/eta` | GET | ETA with ML prediction |
| `/api/v1/transit/catalog/routes` | GET | All routes |
| `/api/v1/transit/catalog/routes/{id}/stops` | GET | Stops on a route |
| `/api/v1/transit/catalog/routes/{id}/geometry` | GET | Road-following polyline |
| `/api/v1/transit/catalog/stops` | GET | All stops |
| `/api/v1/journey/plan` | POST | Plan a journey |

## Scripts

| Script | Description |
|--------|-------------|
| `scripts/train_eta_model.py` | Train the ETA prediction model |
| `scripts/fix_trip_times.py` | Reset trip timestamps |
| `scripts/fix_stop_times.py` | Recalculate stop_time offsets |
| `scripts/dedup_stops.py` | Remove duplicate stops |
| `scripts/update_remaining_coords.py` | Geocode stops without coordinates |
