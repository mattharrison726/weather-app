"""
FastAPI application entrypoint.

The lifespan context manager handles startup and shutdown:
  - Startup: configure logging, optionally start the scheduler
  - Shutdown: gracefully stop the scheduler if it was running

Run the server:
    cd backend/
    uvicorn app.main:app --reload --port 8000
"""
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.api.routes import pipeline as pipeline_router


def _configure_logging() -> None:
    """Set up loguru with console + rotating file output.

    Two sinks:
      1. stderr — human-readable colourised output for the terminal
      2. logs/pipeline.log — structured text log for file persistence

    Data engineering note: structured logs (consistent format, queryable)
    are the foundation of observability. In production you'd ship these to
    a log aggregator (Datadog, CloudWatch, Loki). Here they land in a file.
    """
    import os
    os.makedirs("logs", exist_ok=True)

    logger.remove()  # Remove the default loguru handler

    # Console: concise, human-readable
    logger.add(
        sys.stderr,
        level=settings.log_level,
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> | {message}",
    )

    # File: full structured output, rotated daily, kept for 7 days
    logger.add(
        "logs/pipeline.log",
        level="DEBUG",
        rotation="1 day",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        encoding="utf-8",
    )

    logger.info(f"Logging configured | level={settings.log_level} | file=logs/pipeline.log")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan — runs setup on startup, teardown on shutdown.

    Using lifespan (rather than @app.on_event) is the current FastAPI best
    practice. It uses a generator so startup and shutdown logic stay together.
    """
    # --- STARTUP ---
    _configure_logging()

    logger.info(
        f"Weather App starting | "
        f"location={settings.weather_location_name} "
        f"({settings.weather_latitude}, {settings.weather_longitude})"
    )

    scheduler = None
    if settings.scheduler_enabled:
        from app.ingestion.scheduler import create_scheduler, start_scheduler
        scheduler = create_scheduler()
        start_scheduler(scheduler)
        logger.info(
            f"Scheduler enabled | interval={settings.scheduler_interval_hours}h"
        )
    else:
        logger.info(
            "Scheduler disabled (SCHEDULER_ENABLED=false). "
            "Use POST /api/pipeline/trigger to refresh data on demand."
        )

    yield  # Application runs here

    # --- SHUTDOWN ---
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")

    logger.info("Weather App stopped")


app = FastAPI(
    title="Weather App API",
    description=(
        "Data engineering weather app — ingests from Open-Meteo, "
        "stores in a local SQLite database, serves clean weather data."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: allow the React dev server (port 5173) and any localhost origin to
# call the API. In production you'd restrict this to your actual domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative React port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(pipeline_router.router)


@app.get("/health")
def health_check():
    """Simple health check — confirms the server is up."""
    return {"status": "ok", "location": settings.weather_location_name}
