"""
Alembic environment configuration.

This file runs when any alembic command is executed. It:
1. Configures the database connection using our Settings class
2. Imports all ORM models (via app.db.models) so autogenerate can detect schema changes
3. Runs migrations in either 'offline' (SQL output) or 'online' (direct DB) mode
"""
import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Add backend/ to sys.path so `from app.xxx import ...` works when alembic runs
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from app.config import settings
from app.db.engine import Base

# Import all models — without these imports, alembic autogenerate won't see the tables
import app.db.models  # noqa: F401

# Alembic Config object (reads alembic.ini)
config = context.config

# Override the sqlalchemy.url from alembic.ini with our Settings value
config.set_main_option("sqlalchemy.url", settings.database_url)

# Set up Python logging from the alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The MetaData object containing all our table definitions.
# This is what alembic compares against the actual database to detect changes.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a database connection — outputs SQL to stdout.

    Useful for: reviewing what SQL will run, applying migrations on prod
    without giving alembic direct DB access.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
