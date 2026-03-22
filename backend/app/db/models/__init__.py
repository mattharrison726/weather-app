# Import all models here so Alembic's autogenerate can discover them.
# If a model isn't imported here, alembic won't include it in migrations.
from app.db.models.raw import RawWeatherIngest  # noqa: F401
from app.db.models.transformed import WeatherObservation  # noqa: F401
from app.db.models.pipeline import PipelineRun, DataQualityIssue  # noqa: F401
from app.db.models.locations import Location  # noqa: F401
