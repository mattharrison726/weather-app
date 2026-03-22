"""Pydantic response schemas for location API endpoints."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LocationResponse(BaseModel):
    """A location in the user's favorites list."""
    location_key: str
    name: str
    country: str
    latitude: float
    longitude: float
    added_at: datetime

    model_config = {"from_attributes": True}


class CatalogCityResponse(BaseModel):
    """A city from the static catalog (may or may not be a favorite)."""
    location_key: str
    name: str
    country: str
    latitude: float
    longitude: float
    is_favorite: bool  # True if the user has added this to their favorites


class BackfillRequest(BaseModel):
    """Request body for the backfill endpoint."""
    location_key: str
    start_date: str   # YYYY-MM-DD
    end_date: str     # YYYY-MM-DD


class BackfillResponse(BaseModel):
    """Summary result from a backfill run."""
    location_key: str
    location_name: str
    start_date: str
    end_date: str
    rows_written: int       # new raw rows inserted
    rows_skipped: int       # duplicate raw rows skipped (idempotent)
    rows_transformed: int   # clean rows written to silver table
    rows_failed: int        # rows that failed Pydantic validation
    duration_seconds: float
