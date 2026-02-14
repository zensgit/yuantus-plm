"""
Alembic migrations environment for the Identity database (auth + audit only).

This is intentionally separate from the main `migrations/` environment so a
true split deployment can keep the identity DB schema minimal.

Supported:
- PostgreSQL (production)
- SQLite (development)
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy import MetaData

# Ensure yuantus package is importable
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(repo_root, "src"))

# Mark Alembic as running to prevent circular imports
os.environ["ALEMBIC_RUNNING"] = "true"

# Import models that belong to the identity database so their tables are
# registered under Base.metadata.
from yuantus.models.base import Base  # noqa: E402
from yuantus.models.audit import AuditLog  # noqa: F401,E402
from yuantus.security.auth.models import (  # noqa: F401,E402
    AuthCredential,
    AuthUser,
    Organization,
    OrgMembership,
    Tenant,
    TenantQuota,
)

# Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_database_url() -> str:
    """Get database URL from environment or config."""
    url = os.getenv("YUANTUS_DATABASE_URL")
    if url:
        return url

    config_url = config.get_main_option(
        "sqlalchemy.url", "sqlite:///yuantus_identity_dev.db"
    )
    if config_url.startswith("driver://"):
        return "sqlite:///yuantus_identity_dev.db"
    return config_url


# Target metadata for identity-only migrations.
IDENTITY_TABLE_NAMES = {
    "auth_tenants",
    "auth_organizations",
    "auth_users",
    "auth_credentials",
    "auth_org_memberships",
    "auth_tenant_quotas",
    "audit_logs",
}

identity_metadata = MetaData()
for name, table in Base.metadata.tables.items():
    if name in IDENTITY_TABLE_NAMES:
        table.tometadata(identity_metadata)

target_metadata = identity_metadata


def run_migrations_offline() -> None:
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

