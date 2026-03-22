"""
Locations API routes.

GET  /api/locations/catalog           — list all available cities
GET  /api/locations/favorites         — list user's favorited locations
POST /api/locations/{location_key}/favorite   — add a location as a favorite
DELETE /api/locations/{location_key}/favorite — remove a location from favorites
"""
from datetime import datetime

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.db.engine import get_db_session
from app.db.models.locations import Location
from app.locations.catalog import CATALOG, CATALOG_BY_KEY
from app.schemas.locations import CatalogCityResponse, LocationResponse

router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.get("/catalog", response_model=list[CatalogCityResponse])
def get_catalog():
    """Return the full catalog of available cities.

    Each city includes an `is_favorite` flag indicating whether the user
    has added it to their favorites list.
    """
    with get_db_session() as session:
        favorite_keys = {
            row.location_key
            for row in session.query(Location.location_key).all()
        }

    return [
        CatalogCityResponse(
            location_key=city.location_key,
            name=city.name,
            country=city.country,
            latitude=city.latitude,
            longitude=city.longitude,
            is_favorite=city.location_key in favorite_keys,
        )
        for city in CATALOG
    ]


@router.get("/favorites", response_model=list[LocationResponse])
def get_favorites():
    """Return the user's favorited locations, sorted by name."""
    with get_db_session() as session:
        locations = (
            session.query(Location)
            .order_by(Location.name)
            .all()
        )
    return [LocationResponse.model_validate(loc) for loc in locations]


@router.post("/favorites/{location_key}", response_model=LocationResponse, status_code=201)
def add_favorite(location_key: str):
    """Add a catalog city to favorites.

    The city must exist in the catalog. Calling this for an already-favorited
    location returns 200 instead of creating a duplicate.
    """
    city = CATALOG_BY_KEY.get(location_key)
    if city is None:
        raise HTTPException(
            status_code=404,
            detail=f"Location '{location_key}' not found in catalog.",
        )

    with get_db_session() as session:
        existing = session.get(Location, location_key)
        if existing:
            logger.info(f"Location {city.name} already in favorites — no-op")
            return LocationResponse.model_validate(existing)

        new_loc = Location(
            location_key=city.location_key,
            name=city.name,
            country=city.country,
            latitude=city.latitude,
            longitude=city.longitude,
            added_at=datetime.utcnow(),
        )
        session.add(new_loc)
        session.flush()
        response = LocationResponse.model_validate(new_loc)

    logger.info(f"Added {city.name}, {city.country} to favorites")
    return response


@router.delete("/favorites/{location_key}", status_code=204)
def remove_favorite(location_key: str):
    """Remove a location from favorites.

    Historical data for this location is preserved in the database —
    removing from favorites only stops future auto-pulls.
    """
    with get_db_session() as session:
        loc = session.get(Location, location_key)
        if loc is None:
            raise HTTPException(
                status_code=404,
                detail=f"Location '{location_key}' is not in your favorites.",
            )
        name = loc.name
        session.delete(loc)

    logger.info(f"Removed {name} from favorites")
