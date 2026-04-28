from __future__ import annotations

import json
from pathlib import Path

from yuantus.scripts import tenant_import_rehearsal
from yuantus.scripts import tenant_import_rehearsal_handoff as handoff
from yuantus.scripts import tenant_import_rehearsal_implementation_packet as packet
from yuantus.scripts import tenant_import_rehearsal_next_action as next_action
from yuantus.scripts import tenant_import_rehearsal_plan as import_plan
from yuantus.scripts import tenant_import_rehearsal_readiness as readiness
from yuantus.scripts import tenant_import_rehearsal_source_preflight as source_preflight
from yuantus.scripts import tenant_import_rehearsal_target_preflight as target_preflight
from yuantus.scripts import tenant_migration_dry_run as dry_run


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
            "target_url": "postgresql://user:***@example.com/rehearsal",
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
            "target_url": "postgresql://user:***@example.com/rehearsal",
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
                "target_url": "postgresql://user:***@example.com/rehearsal",
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


def test_green_packet_with_confirmation_passes_scaffold_guard(tmp_path):
    implementation_packet_json = _write_green_implementation_packet(tmp_path)

    report = tenant_import_rehearsal.build_rehearsal_scaffold_report(
        implementation_packet_json,
        confirm_rehearsal=True,
    )

    assert report["schema_version"] == tenant_import_rehearsal.SCHEMA_VERSION
    assert report["ready_for_rehearsal_scaffold"] is True
    assert report["ready_for_import_execution"] is True
    assert report["import_executed"] is False
    assert report["db_connection_attempted"] is False
    assert report["ready_for_cutover"] is False
    assert report["blockers"] == []
    assert len(report["fresh_artifact_validations"]) == 6


def test_missing_confirmation_blocks_before_import(tmp_path):
    implementation_packet_json = _write_green_implementation_packet(tmp_path)

    report = tenant_import_rehearsal.build_rehearsal_scaffold_report(
        implementation_packet_json,
        confirm_rehearsal=False,
    )

    assert report["ready_for_rehearsal_scaffold"] is False
    assert report["import_executed"] is False
    assert report["db_connection_attempted"] is False
    assert "missing --confirm-rehearsal" in report["blockers"]


def test_blocked_implementation_packet_blocks_scaffold(tmp_path):
    implementation_packet_json = _write_green_implementation_packet(tmp_path)
    payload = json.loads(implementation_packet_json.read_text())
    payload.update(
        {
            "ready_for_claude_importer": False,
            "blockers": ["operator gate failed"],
        }
    )
    _write_json(implementation_packet_json, payload)

    report = tenant_import_rehearsal.build_rehearsal_scaffold_report(
        implementation_packet_json,
        confirm_rehearsal=True,
    )

    assert report["ready_for_rehearsal_scaffold"] is False
    assert (
        "implementation packet must have ready_for_claude_importer=true"
        in report["blockers"]
    )
    assert "implementation packet must have no blockers" in report["blockers"]


def test_stale_artifact_after_packet_generation_blocks_scaffold(tmp_path):
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

    report = tenant_import_rehearsal.build_rehearsal_scaffold_report(
        implementation_packet_json,
        confirm_rehearsal=True,
    )

    assert report["ready_for_rehearsal_scaffold"] is False
    assert (
        "fresh source preflight artifact must have ready_for_importer_source=true"
        in report["blockers"]
    )
    assert "fresh source preflight artifact must have no blockers" in report["blockers"]


def test_wrong_artifact_schema_after_packet_generation_blocks_scaffold(tmp_path):
    implementation_packet_json = _write_green_implementation_packet(tmp_path)
    payload = json.loads(implementation_packet_json.read_text())
    source_path = Path(payload["source_preflight_json"])
    source_payload = _artifact_payloads()["source_preflight_json"]
    source_payload["schema_version"] = "wrong-schema"
    _write_json(source_path, source_payload)

    report = tenant_import_rehearsal.build_rehearsal_scaffold_report(
        implementation_packet_json,
        confirm_rehearsal=True,
    )

    assert report["ready_for_rehearsal_scaffold"] is False
    assert any(
        blocker.startswith("fresh source preflight schema_version must be ")
        for blocker in report["blockers"]
    )


def test_tampered_packet_context_blocks_scaffold(tmp_path):
    implementation_packet_json = _write_green_implementation_packet(tmp_path)
    payload = json.loads(implementation_packet_json.read_text())
    payload["target_schema"] = "yt_t_other"
    _write_json(implementation_packet_json, payload)

    report = tenant_import_rehearsal.build_rehearsal_scaffold_report(
        implementation_packet_json,
        confirm_rehearsal=True,
    )

    assert report["ready_for_rehearsal_scaffold"] is False
    assert (
        "implementation packet target_schema must match fresh validation"
        in report["blockers"]
    )


def test_cli_writes_scaffold_reports(tmp_path):
    implementation_packet_json = _write_green_implementation_packet(tmp_path)
    output_json = tmp_path / "rehearsal.json"
    output_md = tmp_path / "rehearsal.md"

    result = tenant_import_rehearsal.main(
        [
            "--implementation-packet-json",
            str(implementation_packet_json),
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
    assert payload["import_executed"] is False
    assert "Scaffold guard passed: `true`" in markdown
    assert "Import executed: `false`" in markdown


def test_cli_strict_exits_one_when_blocked(tmp_path):
    implementation_packet_json = _write_green_implementation_packet(tmp_path)

    result = tenant_import_rehearsal.main(
        [
            "--implementation-packet-json",
            str(implementation_packet_json),
            "--output-json",
            str(tmp_path / "rehearsal.json"),
            "--output-md",
            str(tmp_path / "rehearsal.md"),
            "--strict",
        ]
    )

    assert result == 1


def test_scaffold_source_does_not_connect_or_mutate_databases():
    source = Path(tenant_import_rehearsal.__file__).read_text()
    upper_source = source.upper()

    assert "CREATE_ENGINE" not in upper_source
    assert "CONNECT(" not in upper_source
    assert "INSERT " not in upper_source
    assert "UPDATE " not in upper_source
    assert "DELETE " not in upper_source
    assert "CREATE SCHEMA" not in upper_source
    assert "DROP SCHEMA" not in upper_source
