"""
SQLAlchemy engine and session factory.

Design notes:
- A single engine is created at module import time (connection pool is shared)
- Sessions are created per-request (or per-pipeline-run) and always closed in a
  try/finally or context manager — never left open
- SQLite requires PRAGMA foreign_keys=ON to enforce FK constraints (off by default)
"""
import os
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


def _get_database_url() -> str:
    """Resolve the database URL, creating the data/ directory if needed."""
    url = settings.database_url
    # For SQLite file URLs, ensure the directory exists
    if url.startswith("sqlite:///"):
        path = url.replace("sqlite:///", "")
        if path and path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    return url


engine = create_engine(
    _get_database_url(),
    # echo=True logs all SQL statements — useful for debugging, turn off in prod
    echo=settings.log_level == "DEBUG",
    # connect_args for SQLite: check_same_thread=False allows the engine to be
    # used from multiple threads (needed by APScheduler + FastAPI sharing one engine)
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    """Enable foreign key enforcement for every SQLite connection.

    SQLite disables FK constraints by default for backwards compatibility.
    This pragma must be set per connection — it doesn't persist.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    # WAL mode improves concurrent read performance
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models in this project."""
    pass


@contextmanager
def get_db_session():
    """Context manager that yields a database session and handles commit/rollback.

    Usage:
        with get_db_session() as session:
            session.add(some_object)
            # commit happens automatically on exit if no exception

    This is the preferred way to use sessions in non-FastAPI code (pipeline runner,
    scheduler). FastAPI routes use the get_db dependency instead.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
