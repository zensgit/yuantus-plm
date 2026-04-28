from __future__ import annotations

import json
from pathlib import Path

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
        path = _write_json(tmp_path / key, payload)
        paths[key] = str(path)
    return paths


def _next_action_ready(tmp_path: Path) -> dict:
    artifact_paths = _write_green_artifacts(tmp_path)
    return {
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
    }


def test_ready_next_action_generates_implementation_packet(tmp_path):
    next_action_json = _write_json(
        tmp_path / "next-action.json",
        _next_action_ready(tmp_path),
    )

    report = packet.build_implementation_packet_report(
        next_action_json,
        output_md=tmp_path / "claude-task.md",
    )

    assert report["schema_version"] == packet.SCHEMA_VERSION
    assert report["ready_for_claude_importer"] is True
    assert report["ready_for_cutover"] is False
    assert report["blockers"] == []
    assert report["tenant_id"] == "Acme Prod"
    assert report["source_preflight_json"].endswith("source_preflight_json")
    assert report["target_preflight_json"].endswith("target_preflight_json")
    assert len(report["artifact_validations"]) == 6
    assert all(
        validation["ready"] is True for validation in report["artifact_validations"]
    )


def test_not_final_next_action_blocks_packet(tmp_path):
    payload = _next_action_ready(tmp_path)
    payload.update(
        {
            "next_action": "run_target_preflight",
            "claude_required": False,
            "blockers": ["missing target preflight report"],
        }
    )
    next_action_json = _write_json(tmp_path / "next-action.json", payload)

    report = packet.build_implementation_packet_report(
        next_action_json,
        output_md=tmp_path / "claude-task.md",
    )

    assert report["ready_for_claude_importer"] is False
    assert f"next_action must be {packet.FINAL_NEXT_ACTION}" in report["blockers"]
    assert "next-action report must have claude_required=true" in report["blockers"]
    assert "next-action report must have no blockers" in report["blockers"]


def test_missing_required_artifact_path_blocks_packet(tmp_path):
    payload = _next_action_ready(tmp_path)
    payload["context"]["source_preflight_json"] = ""
    next_action_json = _write_json(tmp_path / "next-action.json", payload)

    report = packet.build_implementation_packet_report(
        next_action_json,
        output_md=tmp_path / "claude-task.md",
    )

    assert report["ready_for_claude_importer"] is False
    assert "next-action report missing source_preflight_json" in report["blockers"]


def test_missing_artifact_file_blocks_packet(tmp_path):
    payload = _next_action_ready(tmp_path)
    payload["context"]["source_preflight_json"] = str(tmp_path / "missing-source.json")
    next_action_json = _write_json(tmp_path / "next-action.json", payload)

    report = packet.build_implementation_packet_report(
        next_action_json,
        output_md=tmp_path / "claude-task.md",
    )

    assert report["ready_for_claude_importer"] is False
    assert (
        f"source preflight artifact {tmp_path / 'missing-source.json'} does not exist"
        in report["blockers"]
    )


def test_blocked_artifact_blocks_packet(tmp_path):
    payload = _next_action_ready(tmp_path)
    source_path = Path(payload["context"]["source_preflight_json"])
    source_payload = _artifact_payloads()["source_preflight_json"]
    source_payload.update(
        {
            "ready_for_importer_source": False,
            "blockers": ["missing source table"],
        }
    )
    _write_json(source_path, source_payload)
    next_action_json = _write_json(tmp_path / "next-action.json", payload)

    report = packet.build_implementation_packet_report(
        next_action_json,
        output_md=tmp_path / "claude-task.md",
    )

    assert report["ready_for_claude_importer"] is False
    assert (
        "source preflight artifact must have ready_for_importer_source=true"
        in report["blockers"]
    )
    assert "source preflight artifact must have no blockers" in report["blockers"]


def test_artifact_context_mismatch_blocks_packet(tmp_path):
    payload = _next_action_ready(tmp_path)
    dry_run_path = Path(payload["context"]["dry_run_json"])
    dry_run_payload = _artifact_payloads()["dry_run_json"]
    dry_run_payload["target_schema"] = "yt_t_other"
    _write_json(dry_run_path, dry_run_payload)
    next_action_json = _write_json(tmp_path / "next-action.json", payload)

    report = packet.build_implementation_packet_report(
        next_action_json,
        output_md=tmp_path / "claude-task.md",
    )

    assert report["ready_for_claude_importer"] is False
    assert "dry-run target_schema must match next-action context" in report["blockers"]


def test_cli_writes_json_and_markdown(tmp_path):
    next_action_json = _write_json(
        tmp_path / "next-action.json",
        _next_action_ready(tmp_path),
    )
    output_json = tmp_path / "packet.json"
    output_md = tmp_path / "claude-task.md"

    result = packet.main(
        [
            "--next-action-json",
            str(next_action_json),
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
    assert payload["ready_for_claude_importer"] is True
    assert "# Claude Task - P3.4.2 Tenant Import Rehearsal Importer" in markdown
    assert "Claude can implement importer: `true`" in markdown
    assert "ready_for_cutover=false" in markdown
    assert "## Artifact Integrity" in markdown
    assert "tenant_import_rehearsal" in markdown


def test_cli_strict_exits_one_when_blocked(tmp_path):
    payload = _next_action_ready(tmp_path)
    payload["claude_required"] = False
    next_action_json = _write_json(tmp_path / "next-action.json", payload)

    result = packet.main(
        [
            "--next-action-json",
            str(next_action_json),
            "--output-json",
            str(tmp_path / "packet.json"),
            "--output-md",
            str(tmp_path / "claude-task.md"),
            "--strict",
        ]
    )

    assert result == 1


def test_packet_source_does_not_connect_or_mutate_databases():
    source = Path(packet.__file__).read_text()
    upper_source = source.upper()

    assert "CREATE_ENGINE" not in upper_source
    assert "CONNECT(" not in upper_source
    assert "INSERT " not in upper_source
    assert "UPDATE " not in upper_source
    assert "DELETE " not in upper_source
    assert "CREATE SCHEMA" not in upper_source
    assert "DROP SCHEMA" not in upper_source
