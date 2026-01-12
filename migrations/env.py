"""
Alembic migrations environment for YuantusPLM.

Supports:
- PostgreSQL (production)
- SQLite (development)
- Multi-tenant URL resolution
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure yuantus package is importable
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(repo_root, "src"))

# Mark Alembic as running to prevent circular imports
os.environ["ALEMBIC_RUNNING"] = "true"

# Import all models to register them with SQLAlchemy metadata
from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.models.base import Base, WorkflowBase

import_all_models()

# Import identity models as well
from yuantus.security.auth.models import (  # noqa: F401
    AuthUser,
    Tenant,
    Organization,
    OrgMembership,
    TenantQuota,
)
from yuantus.security.rbac.models import RBACUser, RBACRole  # noqa: F401
from yuantus.models import user as _user  # noqa: F401

# Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for migrations
# Include both Base and WorkflowBase metadata
from sqlalchemy import MetaData

# Create combined metadata for autogenerate
combined_metadata = MetaData()
for table in Base.metadata.tables.values():
    table.tometadata(combined_metadata)
for table in WorkflowBase.metadata.tables.values():
    table.tometadata(combined_metadata)

target_metadata = combined_metadata


def get_database_url() -> str:
    """Get database URL from environment or config."""
    # Priority: environment variable > alembic.ini
    url = os.getenv("YUANTUS_DATABASE_URL")
    if url:
        return url

    # Fallback to config file (for local dev)
    config_url = config.get_main_option(
        "sqlalchemy.url", "sqlite:///yuantus_dev.db"
    )
    if config_url.startswith("driver://"):
        return "sqlite:///yuantus_dev.db"
    return config_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Build configuration with database URL
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
