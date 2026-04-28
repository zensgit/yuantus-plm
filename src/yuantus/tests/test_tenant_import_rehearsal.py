from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine

from yuantus.scripts import tenant_import_rehearsal
from yuantus.scripts import tenant_import_rehearsal_handoff as handoff
from yuantus.scripts import tenant_import_rehearsal_implementation_packet as packet
from yuantus.scripts import tenant_import_rehearsal_next_action as next_action
from yuantus.scripts import tenant_import_rehearsal_plan as import_plan
from yuantus.scripts import tenant_import_rehearsal_readiness as readiness
from yuantus.scripts import tenant_import_rehearsal_source_preflight as source_preflight
from yuantus.scripts import tenant_import_rehearsal_target_preflight as target_preflight
from yuantus.scripts import tenant_migration_dry_run as dry_run


_SOURCE_URL = "sqlite:////tmp/source.db"
_TARGET_URL = "postgresql://user:secret@example.com/rehearsal"
_TARGET_URL_REDACTED = "postgresql://user:***@example.com/rehearsal"
_IMPORT_ORDER = ["meta_items", "meta_files", "meta_conversion_jobs"]
_SOURCE_ROW_COUNTS = {
    "meta_items": 2,
    "meta_files": 3,
    "meta_conversion_jobs": 1,
}


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _artifact_payloads() -> dict[str, dict]:
    return {
        "dry_run_json": {
            "schema_version": dry_run.SCHEMA_VERSION,
            "tenant_id": "Acme Prod",
            "target_schema": "yt_t_acme_prod",
            "ready_for_import": True,
            "blockers": [],
        },
        "readiness_json": {
            "schema_version": readiness.SCHEMA_VERSION,
            "tenant_id": "Acme Prod",
            "target_schema": "yt_t_acme_prod",
            "target_url": "postgresql://user:***@example.com/rehearsal",
            "ready_for_rehearsal": True,
            "blockers": [],
        },
        "handoff_json": {
            "schema_version": handoff.SCHEMA_VERSION,
            "tenant_id": "Acme Prod",
            "target_schema": "yt_t_acme_prod",
            "target_url": "postgresql://user:***@example.com/rehearsal",
            "ready_for_claude": True,
            "blockers": [],
        },
        "plan_json": {
            "schema_version": import_plan.SCHEMA_VERSION,
            "tenant_id": "Acme Prod",
            "target_schema": "yt_t_acme_prod",
            "source_url": _SOURCE_URL,
            "target_url": _TARGET_URL_REDACTED,
            "baseline_revision": dry_run.BASELINE_REVISION,
            "tenant_tables_in_import_order": _IMPORT_ORDER,
            "source_row_counts": _SOURCE_ROW_COUNTS,
            "ready_for_importer": True,
            "ready_for_cutover": False,
            "blockers": [],
        },
        "source_preflight_json": {
            "schema_version": source_preflight.SCHEMA_VERSION,
            "tenant_id": "Acme Prod",
            "target_schema": "yt_t_acme_prod",
            "ready_for_importer_source": True,
            "ready_for_cutover": False,
            "blockers": [],
        },
        "target_preflight_json": {
            "schema_version": target_preflight.SCHEMA_VERSION,
            "tenant_id": "Acme Prod",
            "target_schema": "yt_t_acme_prod",
            "target_url": _TARGET_URL_REDACTED,
            "ready_for_importer_target": True,
            "ready_for_cutover": False,
            "blockers": [],
        },
    }


def _write_green_artifacts(tmp_path: Path) -> dict[str, str]:
    paths: dict[str, str] = {}
    for key, payload in _artifact_payloads().items():
        paths[key] = str(_write_json(tmp_path / key, payload))
    return paths


def _write_green_implementation_packet(tmp_path: Path) -> Path:
    artifact_paths = _write_green_artifacts(tmp_path)
    next_action_json = _write_json(
        tmp_path / "next-action.json",
        {
            "schema_version": next_action.SCHEMA_VERSION,
            "next_action": packet.FINAL_NEXT_ACTION,
            "claude_required": True,
            "context": {
                "tenant_id": "Acme Prod",
                "target_schema": "yt_t_acme_prod",
                "target_url": _TARGET_URL_REDACTED,
                **artifact_paths,
            },
            "inputs": {},
            "blockers": [],
        },
    )
    report = packet.build_implementation_packet_report(
        next_action_json,
        output_md=tmp_path / "claude-task.md",
    )
    return _write_json(tmp_path / "implementation-packet.json", report)


def test_green_packet_with_confirmation_executes_row_copy(tmp_path, monkeypatch):
    implementation_packet_json = _write_green_implementation_packet(tmp_path)
    observed: dict[str, object] = {}

    def fake_execute_row_copy(**kwargs):
        observed.update(kwargs)
        return (
            [
                {
                    "table": "meta_items",
                    "source_rows_expected": 2,
                    "target_rows_inserted": 2,
                    "row_count_matches": True,
                }
            ],
            [],
        )

    monkeypatch.setattr(tenant_import_rehearsal, "_execute_row_copy", fake_execute_row_copy)

    report = tenant_import_rehearsal.build_rehearsal_scaffold_report(
        implementation_packet_json,
        confirm_rehearsal=True,
        source_url=_SOURCE_URL,
        target_url=_TARGET_URL,
    )

    assert report["schema_version"] == tenant_import_rehearsal.SCHEMA_VERSION
    assert report["ready_for_rehearsal_scaffold"] is True
    assert report["ready_for_import_execution"] is True
    assert report["ready_for_rehearsal_import"] is True
    assert report["import_executed"] is True
    assert report["db_connection_attempted"] is True
    assert report["ready_for_cutover"] is False
    assert report["blockers"] == []
    assert len(report["fresh_artifact_validations"]) == 6
    assert report["table_results"][0]["target_rows_inserted"] == 2
    assert observed["source_url"] == _SOURCE_URL
    assert observed["target_url"] == _TARGET_URL
    assert observed["target_schema"] == "yt_t_acme_prod"
    assert observed["import_order"] == _IMPORT_ORDER
    assert observed["source_row_counts"] == _SOURCE_ROW_COUNTS


def test_missing_confirmation_blocks_before_import(tmp_path, monkeypatch):
    implementation_packet_json = _write_green_implementation_packet(tmp_path)

    def fail_execute_row_copy(**kwargs):  # pragma: no cover - should not run
        raise AssertionError("row copy should not run without confirmation")

    monkeypatch.setattr(tenant_import_rehearsal, "_execute_row_copy", fail_execute_row_copy)

    report = tenant_import_rehearsal.build_rehearsal_scaffold_report(
        implementation_packet_json,
        confirm_rehearsal=False,
        source_url=_SOURCE_URL,
        target_url=_TARGET_URL,
    )

    assert report["ready_for_rehearsal_scaffold"] is False
    assert report["ready_for_rehearsal_import"] is False
    assert report["import_executed"] is False
    assert report["db_connection_attempted"] is False
    assert "missing --confirm-rehearsal" in report["blockers"]


def test_missing_runtime_urls_block_before_import(tmp_path, monkeypatch):
    implementation_packet_json = _write_green_implementation_packet(tmp_path)

    def fail_execute_row_copy(**kwargs):  # pragma: no cover - should not run
        raise AssertionError("row copy should not run without runtime URLs")

    monkeypatch.setattr(tenant_import_rehearsal, "_execute_row_copy", fail_execute_row_copy)

    report = tenant_import_rehearsal.build_rehearsal_scaffold_report(
        implementation_packet_json,
        confirm_rehearsal=True,
    )

    assert report["ready_for_rehearsal_scaffold"] is False
    assert report["db_connection_attempted"] is False
    assert "missing --source-url" in report["blockers"]
    assert "missing --target-url" in report["blockers"]


def test_target_url_must_be_postgres_and_match_packet(tmp_path, monkeypatch):
    implementation_packet_json = _write_green_implementation_packet(tmp_path)

    def fail_execute_row_copy(**kwargs):  # pragma: no cover - should not run
        raise AssertionError("row copy should not run for invalid target URL")

    monkeypatch.setattr(tenant_import_rehearsal, "_execute_row_copy", fail_execute_row_copy)

    report = tenant_import_rehearsal.build_rehearsal_scaffold_report(
        implementation_packet_json,
        confirm_rehearsal=True,
        source_url=_SOURCE_URL,
        target_url="sqlite:///target.db",
    )

    assert report["ready_for_rehearsal_scaffold"] is False
    assert "target_url must be a PostgreSQL URL" in report["blockers"]
    assert "target_url must match redacted implementation packet target_url" in report["blockers"]


def test_target_schema_must_match_managed_pattern(tmp_path, monkeypatch):
    implementation_packet_json = _write_green_implementation_packet(tmp_path)
    payload = json.loads(implementation_packet_json.read_text())
    payload["target_schema"] = "public"
    _write_json(implementation_packet_json, payload)

    def fail_execute_row_copy(**kwargs):  # pragma: no cover - should not run
        raise AssertionError("row copy should not run for unmanaged target schema")

    monkeypatch.setattr(tenant_import_rehearsal, "_execute_row_copy", fail_execute_row_copy)

    report = tenant_import_rehearsal.build_rehearsal_scaffold_report(
        implementation_packet_json,
        confirm_rehearsal=True,
        source_url=_SOURCE_URL,
        target_url=_TARGET_URL,
    )

    assert report["ready_for_rehearsal_scaffold"] is False
    assert "target_schema must match ^yt_t_[a-z0-9_]+$" in report["blockers"]


def test_global_table_in_plan_blocks_before_import(tmp_path, monkeypatch):
    implementation_packet_json = _write_green_implementation_packet(tmp_path)
    plan_path = tmp_path / "plan_json"
    plan_payload = json.loads(plan_path.read_text())
    plan_payload["tenant_tables_in_import_order"] = ["meta_items", "auth_users"]
    plan_payload["source_row_counts"] = {"meta_items": 2, "auth_users": 1}
    _write_json(plan_path, plan_payload)

    def fail_execute_row_copy(**kwargs):  # pragma: no cover - should not run
        raise AssertionError("row copy should not run for global table plan")

    monkeypatch.setattr(tenant_import_rehearsal, "_execute_row_copy", fail_execute_row_copy)

    report = tenant_import_rehearsal.build_rehearsal_scaffold_report(
        implementation_packet_json,
        confirm_rehearsal=True,
        source_url=_SOURCE_URL,
        target_url=_TARGET_URL,
    )

    assert report["ready_for_rehearsal_scaffold"] is False
    assert "plan includes global/control-plane tables: auth_users" in report["blockers"]


def test_missing_source_row_count_blocks_before_import(tmp_path, monkeypatch):
    implementation_packet_json = _write_green_implementation_packet(tmp_path)
    plan_path = tmp_path / "plan_json"
    plan_payload = json.loads(plan_path.read_text())
    plan_payload["source_row_counts"] = {"meta_items": 2}
    _write_json(plan_path, plan_payload)

    def fail_execute_row_copy(**kwargs):  # pragma: no cover - should not run
        raise AssertionError("row copy should not run without row counts")

    monkeypatch.setattr(tenant_import_rehearsal, "_execute_row_copy", fail_execute_row_copy)

    report = tenant_import_rehearsal.build_rehearsal_scaffold_report(
        implementation_packet_json,
        confirm_rehearsal=True,
        source_url=_SOURCE_URL,
        target_url=_TARGET_URL,
    )

    assert report["ready_for_rehearsal_scaffold"] is False
    assert (
        "plan source_row_counts missing import tables: "
        "meta_conversion_jobs, meta_files"
    ) in report["blockers"]


def test_blocked_implementation_packet_blocks_scaffold(tmp_path, monkeypatch):
    implementation_packet_json = _write_green_implementation_packet(tmp_path)
    payload = json.loads(implementation_packet_json.read_text())
    payload.update(
        {
            "ready_for_claude_importer": False,
            "blockers": ["operator gate failed"],
        }
    )
    _write_json(implementation_packet_json, payload)

    def fail_execute_row_copy(**kwargs):  # pragma: no cover - should not run
        raise AssertionError("row copy should not run for blocked packet")

    monkeypatch.setattr(tenant_import_rehearsal, "_execute_row_copy", fail_execute_row_copy)

    report = tenant_import_rehearsal.build_rehearsal_scaffold_report(
        implementation_packet_json,
        confirm_rehearsal=True,
        source_url=_SOURCE_URL,
        target_url=_TARGET_URL,
    )

    assert report["ready_for_rehearsal_scaffold"] is False
    assert (
        "implementation packet must have ready_for_claude_importer=true"
        in report["blockers"]
    )
    assert "implementation packet must have no blockers" in report["blockers"]


def test_stale_artifact_after_packet_generation_blocks_scaffold(tmp_path, monkeypatch):
    implementation_packet_json = _write_green_implementation_packet(tmp_path)
    payload = json.loads(implementation_packet_json.read_text())
    source_path = Path(payload["source_preflight_json"])
    source_payload = _artifact_payloads()["source_preflight_json"]
    source_payload.update(
        {
            "ready_for_importer_source": False,
            "blockers": ["source drifted"],
        }
    )
    _write_json(source_path, source_payload)

    def fail_execute_row_copy(**kwargs):  # pragma: no cover - should not run
        raise AssertionError("row copy should not run for stale artifact")

    monkeypatch.setattr(tenant_import_rehearsal, "_execute_row_copy", fail_execute_row_copy)

    report = tenant_import_rehearsal.build_rehearsal_scaffold_report(
        implementation_packet_json,
        confirm_rehearsal=True,
        source_url=_SOURCE_URL,
        target_url=_TARGET_URL,
    )

    assert report["ready_for_rehearsal_scaffold"] is False
    assert (
        "fresh source preflight artifact must have ready_for_importer_source=true"
        in report["blockers"]
    )
    assert "fresh source preflight artifact must have no blockers" in report["blockers"]


def test_wrong_artifact_schema_after_packet_generation_blocks_scaffold(
    tmp_path, monkeypatch
):
    implementation_packet_json = _write_green_implementation_packet(tmp_path)
    payload = json.loads(implementation_packet_json.read_text())
    source_path = Path(payload["source_preflight_json"])
    source_payload = _artifact_payloads()["source_preflight_json"]
    source_payload["schema_version"] = "wrong-schema"
    _write_json(source_path, source_payload)

    def fail_execute_row_copy(**kwargs):  # pragma: no cover - should not run
        raise AssertionError("row copy should not run for bad artifact schema")

    monkeypatch.setattr(tenant_import_rehearsal, "_execute_row_copy", fail_execute_row_copy)

    report = tenant_import_rehearsal.build_rehearsal_scaffold_report(
        implementation_packet_json,
        confirm_rehearsal=True,
        source_url=_SOURCE_URL,
        target_url=_TARGET_URL,
    )

    assert report["ready_for_rehearsal_scaffold"] is False
    assert any(
        blocker.startswith("fresh source preflight schema_version must be ")
        for blocker in report["blockers"]
    )


def test_tampered_packet_context_blocks_scaffold(tmp_path, monkeypatch):
    implementation_packet_json = _write_green_implementation_packet(tmp_path)
    payload = json.loads(implementation_packet_json.read_text())
    payload["target_schema"] = "yt_t_other"
    _write_json(implementation_packet_json, payload)

    def fail_execute_row_copy(**kwargs):  # pragma: no cover - should not run
        raise AssertionError("row copy should not run for tampered packet")

    monkeypatch.setattr(tenant_import_rehearsal, "_execute_row_copy", fail_execute_row_copy)

    report = tenant_import_rehearsal.build_rehearsal_scaffold_report(
        implementation_packet_json,
        confirm_rehearsal=True,
        source_url=_SOURCE_URL,
        target_url=_TARGET_URL,
    )

    assert report["ready_for_rehearsal_scaffold"] is False
    assert (
        "implementation packet target_schema must match fresh validation"
        in report["blockers"]
    )


def test_row_count_mismatch_blocks_report_after_db_attempt(tmp_path, monkeypatch):
    implementation_packet_json = _write_green_implementation_packet(tmp_path)

    def fake_execute_row_copy(**kwargs):
        return (
            [
                {
                    "table": "meta_items",
                    "source_rows_expected": 2,
                    "target_rows_inserted": 1,
                    "row_count_matches": False,
                }
            ],
            ["meta_items inserted 1 rows; expected 2"],
        )

    monkeypatch.setattr(tenant_import_rehearsal, "_execute_row_copy", fake_execute_row_copy)

    report = tenant_import_rehearsal.build_rehearsal_scaffold_report(
        implementation_packet_json,
        confirm_rehearsal=True,
        source_url=_SOURCE_URL,
        target_url=_TARGET_URL,
    )

    assert report["ready_for_rehearsal_scaffold"] is True
    assert report["ready_for_rehearsal_import"] is False
    assert report["db_connection_attempted"] is True
    assert report["import_executed"] is False
    assert "meta_items inserted 1 rows; expected 2" in report["blockers"]


def test_copy_table_moves_rows_between_sqlalchemy_connections(tmp_path):
    source_engine = create_engine(f"sqlite:///{tmp_path / 'source.db'}")
    target_engine = create_engine(f"sqlite:///{tmp_path / 'target.db'}")
    source_metadata = MetaData()
    target_metadata = MetaData()
    source_table = Table(
        "meta_items",
        source_metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String),
    )
    target_table = Table(
        "meta_items",
        target_metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String),
    )
    try:
        source_metadata.create_all(source_engine)
        target_metadata.create_all(target_engine)
        with source_engine.begin() as connection:
            connection.execute(
                source_table.insert(),
                [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}],
            )
        with source_engine.connect() as source_connection:
            with target_engine.begin() as target_connection:
                inserted = tenant_import_rehearsal._copy_table(
                    source_connection=source_connection,
                    target_connection=target_connection,
                    source_table=source_table,
                    target_table=target_table,
                    batch_size=1,
                )
        with target_engine.connect() as connection:
            rows = connection.execute(target_table.select().order_by(target_table.c.id)).all()
    finally:
        source_engine.dispose()
        target_engine.dispose()

    assert inserted == 2
    assert [(row.id, row.name) for row in rows] == [(1, "A"), (2, "B")]


def test_cli_writes_rehearsal_reports(tmp_path, monkeypatch):
    implementation_packet_json = _write_green_implementation_packet(tmp_path)
    output_json = tmp_path / "rehearsal.json"
    output_md = tmp_path / "rehearsal.md"

    def fake_execute_row_copy(**kwargs):
        return (
            [
                {
                    "table": "meta_items",
                    "source_rows_expected": 2,
                    "target_rows_inserted": 2,
                    "row_count_matches": True,
                }
            ],
            [],
        )

    monkeypatch.setattr(tenant_import_rehearsal, "_execute_row_copy", fake_execute_row_copy)

    result = tenant_import_rehearsal.main(
        [
            "--implementation-packet-json",
            str(implementation_packet_json),
            "--source-url",
            _SOURCE_URL,
            "--target-url",
            _TARGET_URL,
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--confirm-rehearsal",
            "--strict",
        ]
    )

    assert result == 0
    payload = json.loads(output_json.read_text())
    markdown = output_md.read_text()
    assert payload["ready_for_rehearsal_scaffold"] is True
    assert payload["ready_for_rehearsal_import"] is True
    assert payload["import_executed"] is True
    assert "# Tenant Import Rehearsal Report" in markdown
    assert "Scaffold guard passed: `true`" in markdown
    assert "Rehearsal import passed: `true`" in markdown
    assert "Import executed: `true`" in markdown
    assert "| `meta_items` | 2 | 2 | `true` |" in markdown


def test_cli_strict_exits_one_when_blocked(tmp_path):
    implementation_packet_json = _write_green_implementation_packet(tmp_path)

    result = tenant_import_rehearsal.main(
        [
            "--implementation-packet-json",
            str(implementation_packet_json),
            "--source-url",
            _SOURCE_URL,
            "--target-url",
            _TARGET_URL,
            "--output-json",
            str(tmp_path / "rehearsal.json"),
            "--output-md",
            str(tmp_path / "rehearsal.md"),
            "--strict",
        ]
    )

    assert result == 1


def test_rehearsal_source_preserves_guard_and_cutover_controls():
    source = Path(tenant_import_rehearsal.__file__).read_text()
    upper_source = source.upper()

    assert "CREATE SCHEMA" not in upper_source
    assert "DROP SCHEMA" not in upper_source
    assert "DROP TABLE" not in upper_source
    assert "TRUNCATE " not in upper_source
    assert "MERGE " not in upper_source
    assert '"ready_for_cutover": False' in source
    assert "GLOBAL_TABLE_NAMES" in source
