"""
Bronze layer: raw_weather_ingest table.

This is the landing zone for Open-Meteo API responses. The full JSON payload
is stored as-is in raw_payload — no transformation happens here.

Data engineering principle: land raw data first, transform later.
If the transform has a bug, the raw data is preserved and the transform
can be re-run without re-calling the API.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.engine import Base


class RawWeatherIngest(Base):
    __tablename__ = "raw_weather_ingest"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Location identifier — canonical string "lat,lon" used in UNIQUE constraint
    location_key: Mapped[str] = mapped_column(String(50), nullable=False)

    # When we called the API (UTC). Distinct from the data timestamp.
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # The time the weather data REPRESENTS (from the API response body).
    # This is what we use for idempotency — we never want two rows for the
    # same location at the same data timestamp.
    fetched_for_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Full request URL — invaluable for debugging ("what exactly did we ask for?")
    api_url: Mapped[str] = mapped_column(Text, nullable=False)

    # HTTP status code returned by Open-Meteo
    response_status_code: Mapped[int] = mapped_column(Integer, nullable=False)

    # The full JSON response body, serialized as a string.
    # Storing the raw payload means we can always re-parse with a new transform.
    raw_payload: Mapped[str] = mapped_column(Text, nullable=False)

    # Which version of our API parsing schema we expected.
    # If Open-Meteo changes their response format, we can identify affected rows.
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")

    # Has this row been through the transform step?
    # The transform queries WHERE processed = FALSE (indexed below).
    # Marking as True even on transform failure — the failure is recorded
    # in data_quality_issues, not by leaving this False indefinitely.
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Idempotency: one raw row per location per data timestamp.
    # INSERT OR IGNORE combined with this constraint makes re-ingestion a safe no-op.
    __table_args__ = (
        UniqueConstraint("location_key", "fetched_for_timestamp", name="uq_raw_location_timestamp"),
        Index("idx_raw_processed", "processed", "location_key"),
        Index("idx_raw_fetched_for", "fetched_for_timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<RawWeatherIngest id={self.id} location={self.location_key} "
            f"for={self.fetched_for_timestamp} processed={self.processed}>"
        )
