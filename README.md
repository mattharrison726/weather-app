# Weather App

A locally hosted weather data engineering project. Ingests live weather data from a public REST API, stores it in a structured local database through an ETL pipeline, and displays it in a React web app.

Built as a portfolio project to demonstrate data engineering fundamentals: medallion architecture, idempotent pipelines, data quality validation, schema versioning, and pipeline observability.

## Stack

| Layer | Technology |
|-------|-----------|
| Weather API | [Open-Meteo](https://open-meteo.com/) — free, no API key required |
| Backend | Python 3.11+, FastAPI, uvicorn |
| Database | SQLite via SQLAlchemy 2.x + Alembic migrations |
| Pipeline | httpx, tenacity, APScheduler (optional) |
| Data validation | Pydantic v2 |
| Frontend | React 18 + TypeScript, Vite, Recharts |

## Architecture

Data flows through two layers (medallion architecture):

```
Open-Meteo API
    ↓  (httpx + tenacity retry)
raw_weather_ingest     ← Bronze: full JSON blob, never modified
    ↓  (Pydantic validation)
weather_observations   ← Silver: typed, clean, unit-named columns
    ↓
FastAPI REST API
    ↓
React frontend
```

Every pipeline run is recorded in `pipeline_runs` for observability. Validation failures are quarantined in `data_quality_issues` — the pipeline never crashes on bad data.

## Prerequisites

- Python 3.11+
- Node.js 18+

No API keys or external services required.

## Setup

### Backend

```bash
cd backend/

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp ../.env.example .env
# Edit .env to set your preferred location (defaults to London)

# Create the database and run migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --port 8000
```

The API is now running at **http://localhost:8000**.
Swagger UI (interactive API docs) is at **http://localhost:8000/docs**.

### Frontend

```bash
cd frontend/

npm install
npm run dev
```

The app is now running at **http://localhost:5173**.

## Usage

### Fetching weather data

The pipeline does not run automatically by default. Click **Refresh Data** in the app, or call the API directly:

```bash
curl -X POST http://localhost:8000/api/pipeline/trigger
```

This runs the full ETL pipeline: fetches from Open-Meteo → validates → stores in the database → returns a summary.

### Enabling the automatic scheduler

To have the pipeline run automatically in the background, set in `.env`:

```
SCHEDULER_ENABLED=true
SCHEDULER_INTERVAL_HOURS=6
```

Then restart the server.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Server health check |
| `GET` | `/api/weather/current` | Most recent weather observation |
| `GET` | `/api/weather/history` | Observation history (supports `?limit=` and date filters) |
| `POST` | `/api/pipeline/trigger` | Run the ETL pipeline immediately |
| `GET` | `/api/pipeline/runs` | Pipeline run history and audit log |

Full interactive documentation at `http://localhost:8000/docs`.

## Configuration

All configuration is via environment variables. Copy `.env.example` to `.env` and edit:

| Variable | Default | Description |
|----------|---------|-------------|
| `WEATHER_LATITUDE` | `51.5074` | Location latitude |
| `WEATHER_LONGITUDE` | `-0.1278` | Location longitude |
| `WEATHER_LOCATION_NAME` | `London` | Display name |
| `DATABASE_URL` | `sqlite:///./data/weather.db` | SQLite path |
| `PORT` | `8000` | API server port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `SCHEDULER_ENABLED` | `false` | Enable automatic background ingestion |
| `SCHEDULER_INTERVAL_HOURS` | `6` | Scheduler interval when enabled |

## Data Engineering Concepts

This project demonstrates:

- **Medallion Architecture** — raw bronze layer (full API response preserved) → clean silver layer (validated, typed)
- **Idempotency** — re-running the pipeline never creates duplicate rows (`UNIQUE` constraints + `INSERT OR IGNORE`)
- **Schema versioning** — every database change is an Alembic migration with `upgrade()` and `downgrade()`
- **Data quality gates** — Pydantic validators reject out-of-range values; failures are quarantined, not discarded
- **Data lineage** — every clean row has a foreign key back to the raw row that produced it
- **Pipeline observability** — `pipeline_runs` table records every execution with row counts, duration, and status
- **Retry logic** — transient HTTP errors retried with exponential backoff; 4xx errors fail immediately

## Project Structure

```
weather-app/
├── backend/
│   ├── app/
│   │   ├── config.py               # Environment config (pydantic-settings)
│   │   ├── main.py                 # FastAPI app + lifespan + CORS
│   │   ├── api/routes/
│   │   │   ├── weather.py          # Weather data endpoints
│   │   │   └── pipeline.py         # Pipeline trigger + run history
│   │   ├── db/
│   │   │   ├── engine.py           # SQLAlchemy engine + session factory
│   │   │   ├── models/             # ORM models (raw, transformed, pipeline)
│   │   │   └── migrations/         # Alembic migration scripts
│   │   ├── ingestion/
│   │   │   ├── client.py           # Open-Meteo HTTP client + retry
│   │   │   ├── loader.py           # Bronze table writer (idempotent)
│   │   │   └── scheduler.py        # APScheduler (opt-in)
│   │   ├── pipeline/
│   │   │   ├── runner.py           # ETL orchestrator + audit logging
│   │   │   ├── transform.py        # Bronze → silver transformation
│   │   │   └── validate.py         # Pydantic quality validators
│   │   └── schemas/                # Pydantic API response contracts
│   ├── alembic.ini
│   └── pyproject.toml
├── frontend/
│   └── src/
│       ├── api/client.ts           # Typed API client
│       ├── hooks/useWeather.ts     # Data fetching hook
│       ├── types/weather.ts        # TypeScript interfaces
│       └── components/             # React components
├── data/                           # SQLite database (gitignored)
├── logs/                           # Log files (gitignored)
├── .env.example                    # Environment variable template
└── .claude/                        # Architecture decisions + notes (gitignored)
```
