from __future__ import annotations

import json
from pathlib import Path

from yuantus.scripts import tenant_import_rehearsal_handoff as handoff
from yuantus.scripts import tenant_import_rehearsal_plan as plan
from yuantus.scripts import tenant_migration_dry_run as dry_run


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _dry_run_ready() -> dict:
    return {
        "schema_version": dry_run.SCHEMA_VERSION,
        "tenant_id": "Acme Prod",
        "target_schema": "yt_t_acme_prod",
        "source_url": "sqlite:////tmp/source.db",
        "baseline_revision": dry_run.BASELINE_REVISION,
        "tenant_tables_in_import_order": [
            "meta_items",
            "meta_files",
            "meta_conversion_jobs",
        ],
        "excluded_global_tables_present": ["auth_users", "rbac_users"],
        "row_counts": {
            "meta_items": 2,
            "meta_files": 3,
            "meta_conversion_jobs": 1,
        },
        "ready_for_import": True,
        "blockers": [],
    }


def _handoff_ready() -> dict:
    return {
        "schema_version": handoff.SCHEMA_VERSION,
        "tenant_id": "Acme Prod",
        "target_schema": "yt_t_acme_prod",
        "target_url": "postgresql://user:***@example.com/rehearsal",
        "ready_for_claude": True,
        "blockers": [],
    }


def test_ready_inputs_generate_importer_plan(tmp_path):
    dry_run_json = _write_json(tmp_path / "dry-run.json", _dry_run_ready())
    handoff_json = _write_json(tmp_path / "handoff.json", _handoff_ready())

    report = plan.build_import_plan_report(
        dry_run_json=dry_run_json,
        handoff_json=handoff_json,
    )

    assert report["schema_version"] == plan.SCHEMA_VERSION
    assert report["ready_for_importer"] is True
    assert report["ready_for_cutover"] is False
    assert report["blockers"] == []
    assert report["tenant_tables_in_import_order"] == [
        "meta_items",
        "meta_files",
        "meta_conversion_jobs",
    ]
    assert report["source_row_counts"]["meta_files"] == 3
    assert report["skipped_global_tables"] == ["auth_users", "rbac_users"]


def test_handoff_not_ready_blocks_plan(tmp_path):
    dry_run_json = _write_json(tmp_path / "dry-run.json", _dry_run_ready())
    handoff_report = _handoff_ready()
    handoff_report.update(
        {
            "ready_for_claude": False,
            "blockers": ["readiness report must have ready_for_rehearsal=true"],
        }
    )
    handoff_json = _write_json(tmp_path / "handoff.json", handoff_report)

    report = plan.build_import_plan_report(
        dry_run_json=dry_run_json,
        handoff_json=handoff_json,
    )

    assert report["ready_for_importer"] is False
    assert "handoff report must have ready_for_claude=true" in report["blockers"]
    assert "handoff report must have no blockers" in report["blockers"]


def test_global_table_in_import_order_blocks_plan(tmp_path):
    dry_run_report = _dry_run_ready()
    dry_run_report["tenant_tables_in_import_order"] = ["meta_items", "auth_users"]
    dry_run_report["row_counts"] = {"meta_items": 1, "auth_users": 1}
    dry_run_json = _write_json(tmp_path / "dry-run.json", dry_run_report)
    handoff_json = _write_json(tmp_path / "handoff.json", _handoff_ready())

    report = plan.build_import_plan_report(
        dry_run_json=dry_run_json,
        handoff_json=handoff_json,
    )

    assert report["ready_for_importer"] is False
    assert (
        "import plan includes global/control-plane tables: auth_users"
        in report["blockers"]
    )


def test_row_count_coverage_must_match_import_order(tmp_path):
    dry_run_report = _dry_run_ready()
    dry_run_report["row_counts"] = {
        "meta_items": 2,
        "meta_files": 3,
        "stray_table": 1,
    }
    dry_run_json = _write_json(tmp_path / "dry-run.json", dry_run_report)
    handoff_json = _write_json(tmp_path / "handoff.json", _handoff_ready())

    report = plan.build_import_plan_report(
        dry_run_json=dry_run_json,
        handoff_json=handoff_json,
    )

    assert report["ready_for_importer"] is False
    assert (
        "row_counts missing import tables: meta_conversion_jobs" in report["blockers"]
    )
    assert "row_counts contains tables outside import order: stray_table" in report[
        "blockers"
    ]


def test_tenant_or_schema_mismatch_blocks_plan(tmp_path):
    dry_run_json = _write_json(tmp_path / "dry-run.json", _dry_run_ready())
    handoff_report = _handoff_ready()
    handoff_report["tenant_id"] = "Other Tenant"
    handoff_report["target_schema"] = "yt_t_other"
    handoff_json = _write_json(tmp_path / "handoff.json", handoff_report)

    report = plan.build_import_plan_report(
        dry_run_json=dry_run_json,
        handoff_json=handoff_json,
    )

    assert report["ready_for_importer"] is False
    assert "tenant_id must match handoff" in report["blockers"]
    assert "target_schema must match handoff" in report["blockers"]


def test_cli_writes_json_and_markdown(tmp_path):
    dry_run_json = _write_json(tmp_path / "dry-run.json", _dry_run_ready())
    handoff_json = _write_json(tmp_path / "handoff.json", _handoff_ready())
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"

    result = plan.main(
        [
            "--dry-run-json",
            str(dry_run_json),
            "--handoff-json",
            str(handoff_json),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--strict",
        ]
    )

    assert result == 0
    payload = json.loads(output_json.read_text())
    markdown = output_md.read_text()
    assert payload["ready_for_importer"] is True
    assert "# Tenant Import Rehearsal Plan" in markdown
    assert "Ready for cutover: `false`" in markdown


def test_cli_strict_exits_one_when_blocked(tmp_path):
    dry_run_report = _dry_run_ready()
    dry_run_report["ready_for_import"] = False
    dry_run_json = _write_json(tmp_path / "dry-run.json", dry_run_report)
    handoff_json = _write_json(tmp_path / "handoff.json", _handoff_ready())

    result = plan.main(
        [
            "--dry-run-json",
            str(dry_run_json),
            "--handoff-json",
            str(handoff_json),
            "--output-json",
            str(tmp_path / "plan.json"),
            "--output-md",
            str(tmp_path / "plan.md"),
            "--strict",
        ]
    )

    assert result == 1


def test_plan_source_does_not_connect_or_mutate_databases():
    source = Path(plan.__file__).read_text()
    upper_source = source.upper()

    assert "CREATE_ENGINE" not in upper_source
    assert "CONNECT(" not in upper_source
    assert "CREATE SCHEMA" not in upper_source
    assert "DROP SCHEMA" not in upper_source
    assert "os.environ" not in source
