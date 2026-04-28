from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine, text

from yuantus.scripts import tenant_import_rehearsal_plan as plan
from yuantus.scripts import tenant_import_rehearsal_source_preflight as preflight
from yuantus.scripts import tenant_migration_dry_run as dry_run


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _plan_ready() -> dict:
    return {
        "schema_version": plan.SCHEMA_VERSION,
        "tenant_id": "Acme Prod",
        "target_schema": "yt_t_acme_prod",
        "source_url": "sqlite:////tmp/source.db",
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


def _expected_columns() -> dict[str, set[str]]:
    return {
        "meta_items": {"id", "item_number", "name"},
        "meta_files": {"id", "item_id", "filename"},
        "meta_conversion_jobs": {"id", "file_id", "status"},
    }


def _create_sqlite_source(tmp_path: Path, statements: list[str]) -> str:
    source_path = tmp_path / "source.db"
    engine = create_engine(f"sqlite:///{source_path}")
    try:
        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))
    finally:
        engine.dispose()
    return f"sqlite:///{source_path}"


def test_missing_confirm_blocks_before_opening_engine(tmp_path, monkeypatch):
    plan_json = _write_json(tmp_path / "plan.json", _plan_ready())

    def fail_create_engine(*args, **kwargs):  # pragma: no cover - should not run
        raise AssertionError("create_engine should not be called without confirmation")

    monkeypatch.setattr(preflight, "create_engine", fail_create_engine)

    report = preflight.build_source_preflight_report(
        plan_json=plan_json,
        source_url="sqlite:///source.db",
        confirm_source_preflight=False,
    )

    assert report["ready_for_importer_source"] is False
    assert "missing --confirm-source-preflight" in report["blockers"]


def test_blocked_plan_blocks_before_opening_engine(tmp_path, monkeypatch):
    payload = _plan_ready()
    payload.update({"ready_for_importer": False, "blockers": ["plan blocker"]})
    plan_json = _write_json(tmp_path / "plan.json", payload)

    def fail_create_engine(*args, **kwargs):  # pragma: no cover - should not run
        raise AssertionError("create_engine should not be called for blocked plan")

    monkeypatch.setattr(preflight, "create_engine", fail_create_engine)

    report = preflight.build_source_preflight_report(
        plan_json=plan_json,
        source_url="sqlite:///source.db",
        confirm_source_preflight=True,
    )

    assert report["ready_for_importer_source"] is False
    assert "plan report must have ready_for_importer=true" in report["blockers"]
    assert "plan report must have no blockers" in report["blockers"]


def test_plan_table_missing_from_metadata_blocks_before_opening_engine(
    tmp_path, monkeypatch
):
    payload = _plan_ready()
    payload["tenant_tables_in_import_order"] = ["meta_items", "unknown_table"]
    plan_json = _write_json(tmp_path / "plan.json", payload)
    monkeypatch.setattr(
        preflight,
        "_expected_columns_by_table",
        lambda import_order: {"meta_items": {"id"}, "unknown_table": set()},
    )

    def fail_create_engine(*args, **kwargs):  # pragma: no cover - should not run
        raise AssertionError("create_engine should not be called for bad metadata")

    monkeypatch.setattr(preflight, "create_engine", fail_create_engine)

    report = preflight.build_source_preflight_report(
        plan_json=plan_json,
        source_url="sqlite:///source.db",
        confirm_source_preflight=True,
    )

    assert report["ready_for_importer_source"] is False
    assert (
        "plan includes tables missing from tenant metadata: unknown_table"
        in report["blockers"]
    )


def test_ready_source_schema_passes_with_extra_columns_reported(tmp_path, monkeypatch):
    plan_json = _write_json(tmp_path / "plan.json", _plan_ready())
    source_url = _create_sqlite_source(
        tmp_path,
        [
            "create table meta_items (id integer, item_number text, name text, extra text)",
            "create table meta_files (id integer, item_id integer, filename text)",
            "create table meta_conversion_jobs (id integer, file_id integer, status text)",
        ],
    )
    monkeypatch.setattr(
        preflight,
        "_expected_columns_by_table",
        lambda import_order: _expected_columns(),
    )

    report = preflight.build_source_preflight_report(
        plan_json=plan_json,
        source_url=source_url,
        confirm_source_preflight=True,
    )

    assert report["ready_for_importer_source"] is True
    assert report["ready_for_cutover"] is False
    assert report["blockers"] == []
    assert report["missing_source_tables"] == []
    assert report["column_mismatches"]["meta_items"] == {
        "missing_columns": [],
        "extra_columns": ["extra"],
    }


def test_missing_source_table_and_required_columns_block(tmp_path, monkeypatch):
    plan_json = _write_json(tmp_path / "plan.json", _plan_ready())
    source_url = _create_sqlite_source(
        tmp_path,
        [
            "create table meta_items (id integer, item_number text)",
            "create table meta_files (id integer, item_id integer, filename text)",
        ],
    )
    monkeypatch.setattr(
        preflight,
        "_expected_columns_by_table",
        lambda import_order: _expected_columns(),
    )

    report = preflight.build_source_preflight_report(
        plan_json=plan_json,
        source_url=source_url,
        confirm_source_preflight=True,
    )

    assert report["ready_for_importer_source"] is False
    assert (
        "source missing planned tenant tables: meta_conversion_jobs"
        in report["blockers"]
    )
    assert (
        "source missing required columns for planned tables: meta_items"
        in report["blockers"]
    )
    assert report["column_mismatches"]["meta_items"]["missing_columns"] == ["name"]


def test_cli_writes_json_and_markdown(tmp_path, monkeypatch):
    plan_json = _write_json(tmp_path / "plan.json", _plan_ready())
    source_url = _create_sqlite_source(
        tmp_path,
        [
            "create table meta_items (id integer, item_number text, name text)",
            "create table meta_files (id integer, item_id integer, filename text)",
            "create table meta_conversion_jobs (id integer, file_id integer, status text)",
        ],
    )
    monkeypatch.setattr(
        preflight,
        "_expected_columns_by_table",
        lambda import_order: _expected_columns(),
    )
    output_json = tmp_path / "source-preflight.json"
    output_md = tmp_path / "source-preflight.md"

    result = preflight.main(
        [
            "--plan-json",
            str(plan_json),
            "--source-url",
            source_url,
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--confirm-source-preflight",
            "--strict",
        ]
    )

    assert result == 0
    payload = json.loads(output_json.read_text())
    markdown = output_md.read_text()
    assert payload["ready_for_importer_source"] is True
    assert "# Tenant Import Source Preflight Report" in markdown
    assert "Ready for cutover: `false`" in markdown


def test_cli_strict_exits_one_when_blocked(tmp_path, monkeypatch):
    plan_json = _write_json(tmp_path / "plan.json", _plan_ready())

    def fail_create_engine(*args, **kwargs):  # pragma: no cover - should not run
        raise AssertionError("create_engine should not be called without confirmation")

    monkeypatch.setattr(preflight, "create_engine", fail_create_engine)

    result = preflight.main(
        [
            "--plan-json",
            str(plan_json),
            "--source-url",
            "sqlite:///source.db",
            "--output-json",
            str(tmp_path / "source-preflight.json"),
            "--output-md",
            str(tmp_path / "source-preflight.md"),
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
    assert "CREATE TABLE" not in upper_source
    assert "DROP TABLE" not in upper_source
    assert ".COMMIT(" not in upper_source
