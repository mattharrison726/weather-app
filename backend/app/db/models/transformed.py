"""
Silver layer: weather_observations table.

This is the clean, validated, serving-ready table. Every row here has:
- Passed Pydantic validation
- Typed, named columns (units in the name: _c, _mm, _pct, _kmh, _deg)
- A foreign key back to the raw row it came from (data lineage)

Data engineering principle: column names include units to eliminate ambiguity.
"temperature" is ambiguous. "temperature_c" is not.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.engine import Base


class WeatherObservation(Base):
    __tablename__ = "weather_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Data lineage: which raw row produced this clean row?
    # This lets you trace any observation back to the exact API response.
    raw_ingest_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("raw_weather_ingest.id"), nullable=False
    )

    # Location
    location_key: Mapped[str] = mapped_column(String(50), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # The moment this weather data represents (UTC)
    observed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # --- Weather measurements ---
    # Units are in the column name: this is a data engineering convention.
    # It prevents unit confusion at every layer (Python, SQL, API response).

    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    apparent_temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)  # "feels like"
    relative_humidity_pct: Mapped[int | None] = mapped_column(Integer, nullable=True)   # 0-100
    precipitation_mm: Mapped[float | None] = mapped_column(Float, nullable=True)        # mm in period
    wind_speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_direction_deg: Mapped[int | None] = mapped_column(Integer, nullable=True)      # 0-360

    # WMO weather interpretation code (see ADR-003 for code reference)
    weather_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Human-readable description derived from weather_code
    weather_description: Mapped[str | None] = mapped_column(String(100), nullable=True)

    is_day: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Data quality flag set by the transform step
    # 'ok' = passed all validators
    # 'warning' = minor issues but row was salvageable
    # 'failed' = major validation failure (row still written with best-effort values)
    data_quality_flag: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ok"
    )

    # When this row was written by the transform step (UTC)
    transformed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Idempotency: one observation per location per timestamp
    __table_args__ = (
        UniqueConstraint("location_key", "observed_at", name="uq_obs_location_timestamp"),
        Index("idx_obs_location_time", "location_key", "observed_at"),
        Index("idx_obs_observed_at", "observed_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<WeatherObservation id={self.id} location={self.location_key} "
            f"at={self.observed_at} temp={self.temperature_c}°C>"
        )
