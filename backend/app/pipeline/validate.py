"""
Pydantic validators for weather data quality.

This is the data quality gate between the bronze and silver layers.
Every row must pass these validators before being written to weather_observations.

Data engineering principle: validate at the boundary between layers.
The silver table is the "trusted" layer — every row in it has been explicitly
validated. Don't let dirty data silently propagate into serving tables.

Pydantic's ValidationError contains ALL failures in a single pass (not just
the first one), which means we can record every field-level issue in one shot.

See .claude/notes/pydantic-validation-patterns.md for broader context.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator

# WMO (World Meteorological Organization) weather interpretation codes.
# Open-Meteo uses these codes — they're an international standard.
# See .claude/adr/003-api-open-meteo.md for the full reference.
WMO_DESCRIPTIONS: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Drizzle: Light",
    53: "Drizzle: Moderate",
    55: "Drizzle: Dense",
    56: "Freezing drizzle: Light",
    57: "Freezing drizzle: Heavy",
    61: "Rain: Slight",
    63: "Rain: Moderate",
    65: "Rain: Heavy",
    66: "Freezing rain: Light",
    67: "Freezing rain: Heavy",
    71: "Snow: Slight",
    73: "Snow: Moderate",
    75: "Snow: Heavy",
    77: "Snow grains",
    80: "Rain showers: Slight",
    81: "Rain showers: Moderate",
    82: "Rain showers: Violent",
    85: "Snow showers: Slight",
    86: "Snow showers: Heavy",
    95: "Thunderstorm",
    96: "Thunderstorm with hail: Slight",
    99: "Thunderstorm with hail: Heavy",
}


def wmo_description(code: Optional[int]) -> Optional[str]:
    """Look up a human-readable description for a WMO weather code.

    Returns None if code is None or unrecognised — we don't want to crash
    the pipeline because Open-Meteo added a new code we haven't mapped yet.
    """
    if code is None:
        return None
    return WMO_DESCRIPTIONS.get(code, f"Unknown weather code: {code}")


class WeatherObservationValidator(BaseModel):
    """Validates one weather observation before it goes to the silver table.

    Fields match the weather_observations table columns exactly.
    Optional fields reflect that Open-Meteo may not always return every field
    (e.g., precipitation may be absent rather than 0.0 in some responses).

    Validators enforce physical plausibility ranges:
    - Temperature: -90°C (Antarctica record) to 60°C (above any recorded max)
    - Humidity: 0–100% (definition of relative humidity)
    - Wind direction: 0–360 degrees
    - Precipitation: non-negative
    """
    location_key: str
    latitude: float
    longitude: float
    observed_at: datetime
    temperature_c: Optional[float] = None
    apparent_temperature_c: Optional[float] = None
    relative_humidity_pct: Optional[int] = None
    precipitation_mm: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_direction_deg: Optional[int] = None
    weather_code: Optional[int] = None
    weather_description: Optional[str] = None
    is_day: Optional[bool] = None

    @field_validator("temperature_c", "apparent_temperature_c")
    @classmethod
    def temperature_plausible(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (-90.0 <= v <= 60.0):
            raise ValueError(
                f"Temperature {v}°C is outside the plausible range [-90, 60]. "
                "The world record extremes are -89.2°C and 56.7°C."
            )
        return v

    @field_validator("relative_humidity_pct")
    @classmethod
    def humidity_in_range(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (0 <= v <= 100):
            raise ValueError(
                f"Relative humidity {v}% must be between 0 and 100 by definition."
            )
        return v

    @field_validator("wind_direction_deg")
    @classmethod
    def wind_direction_in_range(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (0 <= v <= 360):
            raise ValueError(
                f"Wind direction {v}° must be between 0 and 360."
            )
        return v

    @field_validator("precipitation_mm")
    @classmethod
    def precipitation_non_negative(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError(f"Precipitation {v}mm cannot be negative.")
        return v

    @field_validator("wind_speed_kmh")
    @classmethod
    def wind_speed_non_negative(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError(f"Wind speed {v} km/h cannot be negative.")
        return v

    @model_validator(mode="after")
    def require_observed_at(self) -> "WeatherObservationValidator":
        """observed_at is required — a row without a timestamp is useless."""
        if self.observed_at is None:
            raise ValueError("observed_at is required and cannot be None.")
        return self
