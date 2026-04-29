from __future__ import annotations

import json
from pathlib import Path

from yuantus.scripts import tenant_import_rehearsal
from yuantus.scripts import tenant_import_rehearsal_evidence as evidence
from yuantus.scripts import tenant_import_rehearsal_evidence_archive as archive
from yuantus.scripts import tenant_import_rehearsal_evidence_template as template
from yuantus.scripts import tenant_import_rehearsal_external_status as external_status
from yuantus.scripts import tenant_import_rehearsal_handoff as handoff
from yuantus.scripts import tenant_import_rehearsal_implementation_packet as packet
from yuantus.scripts import tenant_import_rehearsal_next_action as next_action
from yuantus.scripts import tenant_import_rehearsal_operator_packet as operator_packet
from yuantus.scripts import tenant_import_rehearsal_plan as import_plan
from yuantus.scripts import tenant_import_rehearsal_readiness as readiness
from yuantus.scripts import tenant_import_rehearsal_source_preflight as source_preflight
from yuantus.scripts import tenant_import_rehearsal_target_preflight as target_preflight
from yuantus.scripts import tenant_migration_dry_run as dry_run


_TARGET_URL_REDACTED = "postgresql://user:***@example.com/rehearsal"


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
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
            "target_url": _TARGET_URL_REDACTED,
            "ready_for_rehearsal": True,
            "blockers": [],
        },
        "handoff_json": {
            "schema_version": handoff.SCHEMA_VERSION,
            "tenant_id": "Acme Prod",
            "target_schema": "yt_t_acme_prod",
            "target_url": _TARGET_URL_REDACTED,
            "ready_for_claude": True,
            "blockers": [],
        },
        "plan_json": {
            "schema_version": import_plan.SCHEMA_VERSION,
            "tenant_id": "Acme Prod",
            "target_schema": "yt_t_acme_prod",
            "source_url": "sqlite:////tmp/source.db",
            "target_url": _TARGET_URL_REDACTED,
            "baseline_revision": dry_run.BASELINE_REVISION,
            "tenant_tables_in_import_order": ["meta_items"],
            "source_row_counts": {"meta_items": 2},
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


def _write_implementation_packet(tmp_path: Path) -> Path:
    artifact_paths: dict[str, str] = {}
    for key, payload in _artifact_payloads().items():
        artifact_paths[key] = str(_write_json(tmp_path / key, payload))
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
    packet_report = packet.build_implementation_packet_report(
        next_action_json,
        output_md=tmp_path / "claude-task.md",
    )
    return _write_json(tmp_path / "implementation-packet.json", packet_report)


def _write_operator_packet(tmp_path: Path) -> tuple[Path, dict]:
    implementation_packet_json = _write_implementation_packet(tmp_path)
    report = operator_packet.build_operator_packet_report(
        implementation_packet_json=implementation_packet_json,
        artifact_prefix=str(tmp_path / "tenant_acme"),
    )
    path = _write_json(tmp_path / "operator-packet.json", report)
    return path, report


def _write_rehearsal_outputs(operator_report: dict) -> None:
    outputs = operator_report["outputs"]
    rehearsal_report = {
        "schema_version": tenant_import_rehearsal.SCHEMA_VERSION,
        "implementation_packet_json": operator_report["implementation_packet_json"],
        "ready_for_rehearsal_import": True,
        "import_executed": True,
        "db_connection_attempted": True,
        "ready_for_cutover": False,
        "tenant_id": "Acme Prod",
        "target_schema": "yt_t_acme_prod",
        "target_url": _TARGET_URL_REDACTED,
        "table_results": [
            {
                "table": "meta_items",
                "source_rows_expected": 2,
                "target_rows_inserted": 2,
                "row_count_matches": True,
            }
        ],
        "blockers": [],
    }
    _write_json(Path(outputs["rehearsal_json"]), rehearsal_report)
    Path(outputs["rehearsal_md"]).write_text("# Tenant Import Rehearsal Report\n")


def _write_template_outputs(operator_report: dict) -> None:
    outputs = operator_report["outputs"]
    template_report = template.build_operator_evidence_template_report(
        rehearsal_json=outputs["rehearsal_json"],
        backup_restore_owner="Ops Owner",
        rehearsal_window="2026-04-30T10:00:00Z/2026-04-30T12:00:00Z",
        rehearsal_executed_by="Platform Operator",
        rehearsal_result="pass",
        evidence_reviewer="Platform Reviewer",
        evidence_date="2026-04-30",
        output_md=outputs["operator_evidence_md"],
    )
    _write_json(Path(outputs["operator_evidence_template_json"]), template_report)
    Path(outputs["operator_evidence_md"]).write_text(
        template.render_operator_evidence_markdown(template_report)
    )


def _write_evidence_outputs(operator_report: dict) -> None:
    outputs = operator_report["outputs"]
    evidence_report = evidence.build_rehearsal_evidence_report(
        rehearsal_json=outputs["rehearsal_json"],
        implementation_packet_json=operator_report["implementation_packet_json"],
        operator_evidence_md=outputs["operator_evidence_md"],
    )
    _write_json(Path(outputs["evidence_json"]), evidence_report)
    Path(outputs["evidence_md"]).write_text("# Tenant Import Rehearsal Evidence Report\n")


def _write_archive_outputs(operator_report: dict) -> None:
    outputs = operator_report["outputs"]
    archive_report = archive.build_rehearsal_evidence_archive_report(
        evidence_json=outputs["evidence_json"],
        operator_evidence_template_json=outputs["operator_evidence_template_json"],
    )
    _write_json(Path(outputs["archive_json"]), archive_report)
    Path(outputs["archive_md"]).write_text(
        archive.render_markdown_report(archive_report)
    )


def test_operator_packet_without_outputs_reports_row_copy_next_action(tmp_path):
    operator_packet_json, _operator_report = _write_operator_packet(tmp_path)

    report = external_status.build_external_status_report(
        operator_packet_json=operator_packet_json,
    )

    assert report["schema_version"] == external_status.SCHEMA_VERSION
    assert report["current_stage"] == "awaiting_row_copy_rehearsal"
    assert report["next_action"] == "run_row_copy_rehearsal"
    assert report["next_command_name"] == "row_copy_rehearsal"
    assert "tenant_import_rehearsal" in report["next_command"]
    assert report["ready_for_external_progress"] is True
    assert report["ready_for_cutover"] is False
    assert report["blockers"] == []


def test_completed_chain_reports_archive_ready_but_not_cutover(tmp_path):
    operator_packet_json, operator_report = _write_operator_packet(tmp_path)
    _write_rehearsal_outputs(operator_report)
    _write_template_outputs(operator_report)
    _write_evidence_outputs(operator_report)
    _write_archive_outputs(operator_report)

    report = external_status.build_external_status_report(
        operator_packet_json=operator_packet_json,
    )

    assert report["current_stage"] == "rehearsal_archive_ready"
    assert report["next_action"] == "review_archive_and_hold_cutover_gate"
    assert report["next_command"] == ""
    assert report["ready_for_external_progress"] is True
    assert report["ready_for_cutover"] is False
    assert report["blockers"] == []
    assert all(artifact["exists"] for artifact in report["artifacts"])
    assert all(artifact["ready"] for artifact in report["artifacts"])


def test_existing_invalid_rehearsal_blocks_status(tmp_path):
    operator_packet_json, operator_report = _write_operator_packet(tmp_path)
    _write_rehearsal_outputs(operator_report)
    outputs = operator_report["outputs"]
    payload = json.loads(Path(outputs["rehearsal_json"]).read_text())
    payload["ready_for_rehearsal_import"] = False
    payload["blockers"] = ["row mismatch"]
    _write_json(Path(outputs["rehearsal_json"]), payload)

    report = external_status.build_external_status_report(
        operator_packet_json=operator_packet_json,
    )

    assert report["current_stage"] == "blocked_external_status"
    assert report["next_action"] == "fix_blockers"
    assert report["ready_for_external_progress"] is False
    assert "rehearsal_json must have ready_for_rehearsal_import=true" in report["blockers"]
    assert "rehearsal_json must have no blockers" in report["blockers"]


def test_existing_rehearsal_without_markdown_blocks_status(tmp_path):
    operator_packet_json, operator_report = _write_operator_packet(tmp_path)
    _write_rehearsal_outputs(operator_report)
    Path(operator_report["outputs"]["rehearsal_md"]).unlink()

    report = external_status.build_external_status_report(
        operator_packet_json=operator_packet_json,
    )

    assert report["ready_for_external_progress"] is False
    assert any("companion rehearsal_md" in blocker for blocker in report["blockers"])


def test_invalid_operator_packet_blocks_before_artifact_progress(tmp_path):
    operator_packet_json, operator_report = _write_operator_packet(tmp_path)
    operator_report["ready_for_operator_execution"] = False
    operator_report["blockers"] = ["upstream blocked"]
    _write_json(operator_packet_json, operator_report)

    report = external_status.build_external_status_report(
        operator_packet_json=operator_packet_json,
    )

    assert report["current_stage"] == "blocked_external_status"
    assert report["ready_for_external_progress"] is False
    assert "operator packet must have ready_for_operator_execution=true" in report["blockers"]
    assert "operator packet must have no blockers" in report["blockers"]


def test_cli_writes_status_reports_and_strict_allows_pending_next_action(tmp_path):
    operator_packet_json, _operator_report = _write_operator_packet(tmp_path)
    output_json = tmp_path / "status.json"
    output_md = tmp_path / "status.md"

    exit_code = external_status.main(
        [
            "--operator-packet-json",
            str(operator_packet_json),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--strict",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text())
    assert payload["current_stage"] == "awaiting_row_copy_rehearsal"
    markdown = output_md.read_text()
    assert "Tenant Import Rehearsal External Status" in markdown
    assert "run_row_copy_rehearsal" in markdown


def test_cli_strict_returns_one_for_invalid_existing_artifact(tmp_path):
    operator_packet_json, operator_report = _write_operator_packet(tmp_path)
    _write_rehearsal_outputs(operator_report)
    Path(operator_report["outputs"]["rehearsal_md"]).unlink()

    exit_code = external_status.main(
        [
            "--operator-packet-json",
            str(operator_packet_json),
            "--output-json",
            str(tmp_path / "status.json"),
            "--output-md",
            str(tmp_path / "status.md"),
            "--strict",
        ]
    )

    assert exit_code == 1


def test_source_preserves_external_status_only_scope():
    source = Path(external_status.__file__).read_text()

    assert "create_engine" not in source
    assert "TENANCY_MODE" not in source
    assert "ready_for_cutover\": False" in source
