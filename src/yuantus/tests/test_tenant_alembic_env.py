from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from yuantus.scripts.tenant_schema import (
    GLOBAL_TABLE_NAMES,
    _require_postgres_url,
    _validate_target_schema,
    build_combined_metadata,
    build_tenant_metadata,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_global_table_names_include_identity_rbac_associations_and_legacy_users():
    assert GLOBAL_TABLE_NAMES == {
        "audit_logs",
        "auth_credentials",
        "auth_org_memberships",
        "auth_organizations",
        "auth_tenant_quotas",
        "auth_tenants",
        "auth_users",
        "rbac_permissions",
        "rbac_resources",
        "rbac_role_permissions",
        "rbac_roles",
        "rbac_user_permissions",
        "rbac_user_roles",
        "rbac_users",
        "users",
    }


def test_tenant_metadata_excludes_global_tables_and_partitions_combined_metadata():
    combined_names = set(build_combined_metadata().tables)
    tenant_names = set(build_tenant_metadata().tables)

    assert GLOBAL_TABLE_NAMES <= combined_names
    assert tenant_names.isdisjoint(GLOBAL_TABLE_NAMES)
    assert combined_names == GLOBAL_TABLE_NAMES | tenant_names


@pytest.mark.parametrize(
    ("schema", "expected"),
    [
        ("yt_t_acme", "yt_t_acme"),
        (" yt_t_acme_123 ", "yt_t_acme_123"),
        ("yt_t_" + "a" * 58, "yt_t_" + "a" * 58),
    ],
)
def test_validate_target_schema_accepts_managed_schema_names(schema, expected):
    assert _validate_target_schema(schema) == expected


@pytest.mark.parametrize(
    "schema",
    [
        None,
        "",
        " ",
        "acme",
        "public",
        "yt_t_Acme",
        "yt_t_acme-prod",
        "yt_t_acme;drop",
        "yt_t_" + "a" * 59,
    ],
)
def test_validate_target_schema_rejects_unmanaged_or_unsafe_names(schema):
    with pytest.raises(ValueError):
        _validate_target_schema(schema)


def test_require_postgres_url_rejects_non_postgres_urls():
    with pytest.raises(RuntimeError, match="requires a PostgreSQL DATABASE_URL"):
        _require_postgres_url("sqlite:///yuantus_dev.db")

    assert _require_postgres_url("postgresql://user:pass@localhost/db").startswith(
        "postgresql"
    )
    assert _require_postgres_url("postgresql+psycopg://user:pass@localhost/db").startswith(
        "postgresql"
    )


def _run_tenant_alembic_sql(*, target_schema: str, database_url: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": "src",
            "YUANTUS_DATABASE_URL": database_url,
            "YUANTUS_ALEMBIC_TARGET_SCHEMA": "",
        }
    )
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "alembic_tenant.ini",
            "-x",
            f"target_schema={target_schema}",
            "upgrade",
            "head",
            "--sql",
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_offline_sql_starts_with_search_path_and_has_no_ddl_before_it():
    result = _run_tenant_alembic_sql(
        target_schema="yt_t_contract", database_url="postgresql://user:pass@localhost/db"
    )
    assert result.returncode == 0, result.stderr

    meaningful_lines = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip() and not line.strip().startswith("--")
    ]
    assert meaningful_lines[0] == 'SET search_path TO "yt_t_contract", public;'


def test_offline_sql_rejects_missing_or_invalid_target_schema():
    result = _run_tenant_alembic_sql(
        target_schema="public", database_url="postgresql://user:pass@localhost/db"
    )
    assert result.returncode != 0
    assert "target_schema must match" in result.stderr


def test_offline_sql_rejects_non_postgres_database_url():
    result = _run_tenant_alembic_sql(
        target_schema="yt_t_contract", database_url="sqlite:///yuantus_dev.db"
    )
    assert result.returncode != 0
    assert "requires a PostgreSQL DATABASE_URL" in result.stderr


def test_tenant_env_pins_version_table_schema_to_target_schema():
    env_source = (REPO_ROOT / "migrations_tenant" / "env.py").read_text()
    assert "version_table_schema=target_schema" in env_source
    assert "include_schemas=True" in env_source
