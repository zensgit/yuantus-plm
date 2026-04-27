"""
Alembic migrations environment for tenant application schemas.

This env is Postgres-only and default-off. It excludes global/control-plane
tables and stores each tenant's alembic_version table inside the target schema.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

# Ensure yuantus package is importable
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(repo_root, "src"))

# Mark Alembic as running to prevent circular imports
os.environ["ALEMBIC_RUNNING"] = "true"

from yuantus.config import get_settings  # noqa: E402
from yuantus.scripts.tenant_schema import (  # noqa: E402
    _require_postgres_url,
    _validate_target_schema,
    build_tenant_metadata,
)


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = build_tenant_metadata()


def get_database_url() -> str:
    url = os.getenv("YUANTUS_DATABASE_URL")
    if url:
        return url

    config_url = config.get_main_option(
        "sqlalchemy.url", "sqlite:///yuantus_dev.db"
    )
    if config_url.startswith("driver://"):
        return "sqlite:///yuantus_dev.db"
    return config_url


def get_target_schema() -> str:
    x_args = context.get_x_argument(as_dictionary=True)
    raw_schema = x_args.get("target_schema") or get_settings().ALEMBIC_TARGET_SCHEMA
    return _validate_target_schema(raw_schema)


def get_create_schema() -> bool:
    x_args = context.get_x_argument(as_dictionary=True)
    raw_value = x_args.get("create_schema")
    if raw_value is None:
        return bool(get_settings().ALEMBIC_CREATE_SCHEMA)
    return str(raw_value).strip().lower() in {"1", "true", "yes", "on"}


def _quoted_schema(schema: str) -> str:
    # _validate_target_schema() restricts this to [a-z0-9_], but quote anyway
    # so the emitted migration SQL is explicit about schema scope.
    return f'"{schema}"'


def run_migrations_offline() -> None:
    url = _require_postgres_url(get_database_url())
    target_schema = get_target_schema()

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema=target_schema,
    )

    context.execute(f"SET search_path TO {_quoted_schema(target_schema)}, public")
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    target_schema = get_target_schema()
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _require_postgres_url(get_database_url())

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table_schema=target_schema,
        )

        with context.begin_transaction():
            if get_create_schema():
                connection.execute(
                    text(f"CREATE SCHEMA IF NOT EXISTS {_quoted_schema(target_schema)}")
                )
            connection.execute(
                text(f"SET search_path TO {_quoted_schema(target_schema)}, public")
            )
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
