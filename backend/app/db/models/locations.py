"""
Locations table — tracks user-favorited locations for automatic pipeline runs.

Every row here is a "favorite" location. The pipeline auto-runs for all rows
in this table when triggered without a specific location_key. One-off triggers
and backfill can target any catalog location, even if not in this table.

Design note: the catalog of available cities lives as a static Python list in
app/locations/catalog.py — it doesn't need a DB table because it never changes
at runtime. Only the user's chosen favorites need persistence.
"""
from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.engine import Base


class Location(Base):
    __tablename__ = "locations"

    # location_key is the canonical identifier used across all tables.
    # Format: "{latitude},{longitude}" — matches the convention in raw and silver tables.
    location_key: Mapped[str] = mapped_column(String(50), primary_key=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # When the user added this location as a favorite
    added_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Location {self.name}, {self.country} ({self.location_key})>"
