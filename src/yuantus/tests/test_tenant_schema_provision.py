from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from yuantus.scripts import tenant_schema


def test_resolve_schema_for_tenant_id_delegates_to_runtime_resolver():
    assert tenant_schema.resolve_schema_for_tenant_id("Acme Prod") == "yt_t_acme_prod"


def test_provision_create_false_returns_schema_without_opening_engine(monkeypatch):
    def fail_create_engine(*args, **kwargs):  # pragma: no cover - should not run
        raise AssertionError("create_engine should not be called for create=False")

    monkeypatch.setattr(tenant_schema, "create_engine", fail_create_engine)

    assert (
        tenant_schema.provision_tenant_schema("Acme Prod", create=False)
        == "yt_t_acme_prod"
    )


def test_provision_rejects_non_postgres_before_opening_engine(monkeypatch):
    monkeypatch.setattr(
        tenant_schema,
        "get_settings",
        lambda: SimpleNamespace(DATABASE_URL="sqlite:///yuantus_dev.db"),
    )

    def fail_create_engine(*args, **kwargs):  # pragma: no cover - should not run
        raise AssertionError("create_engine should not be called for non-Postgres")

    monkeypatch.setattr(tenant_schema, "create_engine", fail_create_engine)

    with pytest.raises(RuntimeError, match="requires a PostgreSQL DATABASE_URL"):
        tenant_schema.provision_tenant_schema("acme")


def test_provision_executes_idempotent_create_schema_and_disposes(monkeypatch):
    executed: list[str] = []
    disposed = {"value": False}

    class FakeConnection:
        def execute(self, statement):
            executed.append(str(statement))

    class FakeBegin:
        def __enter__(self):
            return FakeConnection()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeBegin()

        def dispose(self):
            disposed["value"] = True

    monkeypatch.setattr(
        tenant_schema,
        "get_settings",
        lambda: SimpleNamespace(DATABASE_URL="postgresql://user:pass@localhost/db"),
    )
    monkeypatch.setattr(tenant_schema, "create_engine", lambda *a, **kw: FakeEngine())

    assert tenant_schema.provision_tenant_schema("Acme Prod") == "yt_t_acme_prod"
    assert executed == ['CREATE SCHEMA IF NOT EXISTS "yt_t_acme_prod"']
    assert disposed["value"] is True


@pytest.mark.skipif(
    not os.getenv("YUANTUS_TEST_PG_DSN"),
    reason="requires YUANTUS_TEST_PG_DSN",
)
def test_provision_is_idempotent_against_real_postgres(monkeypatch):
    import uuid

    from sqlalchemy import create_engine, inspect, text
    from sqlalchemy.pool import NullPool

    tenant_id = f"provision-{uuid.uuid4().hex[:8]}"
    schema = tenant_schema.resolve_schema_for_tenant_id(tenant_id)
    dsn = os.environ["YUANTUS_TEST_PG_DSN"]
    monkeypatch.setattr(
        tenant_schema,
        "get_settings",
        lambda: SimpleNamespace(DATABASE_URL=dsn),
    )

    engine = create_engine(dsn, poolclass=NullPool)
    try:
        try:
            tenant_schema.provision_tenant_schema(tenant_id)
            tenant_schema.provision_tenant_schema(tenant_id)
            assert schema in inspect(engine).get_schema_names()
        finally:
            with engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
    finally:
        engine.dispose()


def test_cli_resolve_prints_schema(capsys):
    assert tenant_schema.main(["resolve", "--tenant-id", "Acme Prod"]) == 0
    assert capsys.readouterr().out.strip() == "yt_t_acme_prod"


def test_helper_source_does_not_contain_privilege_or_destructive_schema_commands():
    source = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "tenant_schema.py"
    ).read_text()
    upper_source = source.upper()
    assert "GRANT " not in upper_source
    assert "REVOKE " not in upper_source
    assert "OWNER TO" not in upper_source
