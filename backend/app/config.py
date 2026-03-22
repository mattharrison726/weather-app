"""
Application configuration loaded from environment variables.

pydantic-settings reads from .env automatically and validates types at startup.
If a required variable is missing or the wrong type, the app refuses to start
with a clear error — failing fast is better than failing silently mid-request.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Weather location (Open-Meteo uses lat/lon)
    weather_latitude: float = 51.5074
    weather_longitude: float = -0.1278
    weather_location_name: str = "London"

    # Database
    database_url: str = "sqlite:///./data/weather.db"

    # Server
    port: int = 8000

    # Logging
    log_level: str = "INFO"

    # Scheduler — off by default for infrequent personal use.
    # Set SCHEDULER_ENABLED=true to enable automatic background ingestion.
    # SCHEDULER_INTERVAL_HOURS controls how often it runs (default: every 6 hours).
    scheduler_enabled: bool = False
    scheduler_interval_hours: int = 6

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def location_key(self) -> str:
        """Canonical string key for this location, used in DB UNIQUE constraints."""
        return f"{self.weather_latitude},{self.weather_longitude}"


settings = Settings()
