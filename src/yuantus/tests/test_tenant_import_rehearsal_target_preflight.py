from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import pytest

from yuantus.scripts import tenant_import_rehearsal_plan as plan
from yuantus.scripts import tenant_import_rehearsal_target_preflight as preflight
from yuantus.scripts import tenant_migration_dry_run as dry_run


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _plan_ready() -> dict:
    return {
        "schema_version": plan.SCHEMA_VERSION,
        "tenant_id": "Acme Prod",
        "target_schema": "yt_t_acme_prod",
        "target_url": "postgresql://user:***@example.com/rehearsal",
        "baseline_revision": dry_run.BASELINE_REVISION,
        "tenant_tables_in_import_order": [
            "meta_items",
            "meta_files",
            "meta_conversion_jobs",
        ],
        "source_row_counts": {
            "meta_items": 2,
            "meta_files": 3,
            "meta_conversion_jobs": 1,
        },
        "ready_for_importer": True,
        "ready_for_cutover": False,
        "blockers": [],
    }


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value


class _RowsResult:
    def __init__(self, rows):
        self.rows = [(row,) for row in rows]

    def __iter__(self):
        return iter(self.rows)


class _FakeConnection:
    def __init__(
        self,
        *,
        schema_exists: bool = True,
        tables: set[str] | None = None,
        alembic_version: str = dry_run.BASELINE_REVISION,
    ):
        self.schema_exists = schema_exists
        self.tables = tables or {
            "alembic_version",
            "meta_items",
            "meta_files",
            "meta_conversion_jobs",
        }
        self.alembic_version = alembic_version
        self.statements: list[str] = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append(sql)
        if "pg_namespace" in sql:
            return _ScalarResult(self.schema_exists)
        if "information_schema.tables" in sql:
            return _RowsResult(self.tables)
        if "alembic_version" in sql:
            return _ScalarResult(self.alembic_version)
        raise AssertionError(f"unexpected SQL: {sql}")


class _FakeConnect:
    def __init__(self, connection: _FakeConnection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeEngine:
    def __init__(self, connection: _FakeConnection):
        self.connection = connection
        self.disposed = False

    def connect(self):
        return _FakeConnect(self.connection)

    def dispose(self):
        self.disposed = True


def test_missing_confirm_blocks_before_opening_engine(tmp_path, monkeypatch):
    plan_json = _write_json(tmp_path / "plan.json", _plan_ready())

    def fail_create_engine(*args, **kwargs):  # pragma: no cover - should not run
        raise AssertionError("create_engine should not be called without confirmation")

    monkeypatch.setattr(preflight, "create_engine", fail_create_engine)

    report = preflight.build_target_preflight_report(
        plan_json=plan_json,
        target_url="postgresql://user:secret@example.com/rehearsal",
        target_schema="yt_t_acme_prod",
        confirm_target_preflight=False,
    )

    assert report["ready_for_importer_target"] is False
    assert "missing --confirm-target-preflight" in report["blockers"]
    assert "secret" not in json.dumps(report)


def test_non_postgres_target_blocks_before_opening_engine(tmp_path, monkeypatch):
    plan_json = _write_json(tmp_path / "plan.json", _plan_ready())

    def fail_create_engine(*args, **kwargs):  # pragma: no cover - should not run
        raise AssertionError("create_engine should not be called for non-Postgres")

    monkeypatch.setattr(preflight, "create_engine", fail_create_engine)

    report = preflight.build_target_preflight_report(
        plan_json=plan_json,
        target_url="sqlite:///target.db",
        target_schema="yt_t_acme_prod",
        confirm_target_preflight=True,
    )

    assert report["ready_for_importer_target"] is False
    assert "target_url must be a PostgreSQL URL" in report["blockers"]


def test_blocked_plan_blocks_before_opening_engine(tmp_path, monkeypatch):
    payload = _plan_ready()
    payload.update({"ready_for_importer": False, "blockers": ["plan blocker"]})
    plan_json = _write_json(tmp_path / "plan.json", payload)

    def fail_create_engine(*args, **kwargs):  # pragma: no cover - should not run
        raise AssertionError("create_engine should not be called for blocked plan")

    monkeypatch.setattr(preflight, "create_engine", fail_create_engine)

    report = preflight.build_target_preflight_report(
        plan_json=plan_json,
        target_url="postgresql://user:secret@example.com/rehearsal",
        target_schema="yt_t_acme_prod",
        confirm_target_preflight=True,
    )

    assert report["ready_for_importer_target"] is False
    assert "plan report must have ready_for_importer=true" in report["blockers"]
    assert "plan report must have no blockers" in report["blockers"]


def test_ready_target_schema_passes_and_disposes(tmp_path, monkeypatch):
    plan_json = _write_json(tmp_path / "plan.json", _plan_ready())
    connection = _FakeConnection()
    engine = _FakeEngine(connection)
    monkeypatch.setattr(preflight, "create_engine", lambda *a, **kw: engine)

    report = preflight.build_target_preflight_report(
        plan_json=plan_json,
        target_url="postgresql://user:secret@example.com/rehearsal",
        target_schema="yt_t_acme_prod",
        confirm_target_preflight=True,
    )

    assert report["ready_for_importer_target"] is True
    assert report["ready_for_cutover"] is False
    assert report["blockers"] == []
    assert report["target_schema_exists"] is True
    assert report["alembic_version"] == dry_run.BASELINE_REVISION
    assert report["missing_target_tables"] == []
    assert report["global_tables_present"] == []
    assert engine.disposed is True
    assert "secret" not in json.dumps(report)


def test_missing_schema_wrong_version_missing_tables_and_globals_block(tmp_path, monkeypatch):
    plan_json = _write_json(tmp_path / "plan.json", _plan_ready())
    connection = _FakeConnection(
        schema_exists=True,
        tables={"alembic_version", "meta_items", "auth_users"},
        alembic_version="old_revision",
    )
    monkeypatch.setattr(
        preflight, "create_engine", lambda *a, **kw: _FakeEngine(connection)
    )

    report = preflight.build_target_preflight_report(
        plan_json=plan_json,
        target_url="postgresql://user:secret@example.com/rehearsal",
        target_schema="yt_t_acme_prod",
        confirm_target_preflight=True,
    )

    assert report["ready_for_importer_target"] is False
    assert (
        f"target alembic_version must be {dry_run.BASELINE_REVISION}"
        in report["blockers"]
    )
    assert (
        "target schema missing tenant tables: meta_conversion_jobs, meta_files"
        in report["blockers"]
    )
    assert (
        "target schema contains global/control-plane tables: auth_users"
        in report["blockers"]
    )


def test_missing_schema_blocks_without_version_query(tmp_path, monkeypatch):
    plan_json = _write_json(tmp_path / "plan.json", _plan_ready())
    connection = _FakeConnection(schema_exists=False)
    monkeypatch.setattr(
        preflight, "create_engine", lambda *a, **kw: _FakeEngine(connection)
    )

    report = preflight.build_target_preflight_report(
        plan_json=plan_json,
        target_url="postgresql://user:secret@example.com/rehearsal",
        target_schema="yt_t_acme_prod",
        confirm_target_preflight=True,
    )

    assert report["ready_for_importer_target"] is False
    assert "target schema is missing" in report["blockers"]
    assert f"target alembic_version must be {dry_run.BASELINE_REVISION}" in report[
        "blockers"
    ]
    assert all("alembic_version" not in sql for sql in connection.statements)


def test_cli_writes_json_and_markdown(tmp_path, monkeypatch):
    plan_json = _write_json(tmp_path / "plan.json", _plan_ready())
    output_json = tmp_path / "preflight.json"
    output_md = tmp_path / "preflight.md"
    monkeypatch.setattr(
        preflight, "create_engine", lambda *a, **kw: _FakeEngine(_FakeConnection())
    )

    result = preflight.main(
        [
            "--plan-json",
            str(plan_json),
            "--target-url",
            "postgresql://user:secret@example.com/rehearsal",
            "--target-schema",
            "yt_t_acme_prod",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--confirm-target-preflight",
            "--strict",
        ]
    )

    assert result == 0
    payload = json.loads(output_json.read_text())
    markdown = output_md.read_text()
    assert payload["ready_for_importer_target"] is True
    assert "# Tenant Import Target Preflight Report" in markdown
    assert "Ready for cutover: `false`" in markdown
    assert "secret" not in json.dumps(payload)
    assert "secret" not in markdown


def test_cli_strict_exits_one_when_blocked(tmp_path, monkeypatch):
    plan_json = _write_json(tmp_path / "plan.json", _plan_ready())

    def fail_create_engine(*args, **kwargs):  # pragma: no cover - should not run
        raise AssertionError("create_engine should not be called without confirmation")

    monkeypatch.setattr(preflight, "create_engine", fail_create_engine)

    result = preflight.main(
        [
            "--plan-json",
            str(plan_json),
            "--target-url",
            "postgresql://user:secret@example.com/rehearsal",
            "--target-schema",
            "yt_t_acme_prod",
            "--output-json",
            str(tmp_path / "preflight.json"),
            "--output-md",
            str(tmp_path / "preflight.md"),
            "--strict",
        ]
    )

    assert result == 1


def test_source_has_no_mutation_statements():
    source = Path(preflight.__file__).read_text()
    upper_source = source.upper()

    assert "INSERT " not in upper_source
    assert "UPDATE " not in upper_source
    assert "DELETE " not in upper_source
    assert "CREATE SCHEMA" not in upper_source
    assert "DROP SCHEMA" not in upper_source
    assert ".COMMIT(" not in upper_source


@pytest.mark.skipif(
    not os.getenv("YUANTUS_TEST_PG_DSN"),
    reason="requires YUANTUS_TEST_PG_DSN",
)
def test_target_preflight_against_real_postgres(tmp_path):
    from sqlalchemy import create_engine, text

    run_id = uuid.uuid4().hex[:8]
    schema = f"yt_t_preflight_{run_id}"
    dsn = os.environ["YUANTUS_TEST_PG_DSN"]
    plan_payload = _plan_ready()
    plan_payload["target_schema"] = schema
    plan_json = _write_json(tmp_path / "plan.json", plan_payload)

    engine = create_engine(dsn)
    try:
        with engine.connect() as connection:
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
            connection.execute(
                text(f'CREATE TABLE "{schema}".alembic_version (version_num text)')
            )
            connection.execute(
                text(
                    f'INSERT INTO "{schema}".alembic_version (version_num) '
                    "VALUES (:version)"
                ),
                {"version": dry_run.BASELINE_REVISION},
            )
            for table_name in plan_payload["tenant_tables_in_import_order"]:
                connection.execute(text(f'CREATE TABLE "{schema}"."{table_name}" (id int)'))
            connection.commit()

        report = preflight.build_target_preflight_report(
            plan_json=plan_json,
            target_url=dsn,
            target_schema=schema,
            confirm_target_preflight=True,
        )

        assert report["ready_for_importer_target"] is True
        assert report["blockers"] == []
    finally:
        with engine.connect() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            connection.commit()
        engine.dispose()
