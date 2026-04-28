from __future__ import annotations

import json
from pathlib import Path

from yuantus.scripts import tenant_import_rehearsal_implementation_packet as packet
from yuantus.scripts import tenant_import_rehearsal_next_action as next_action


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _next_action_ready() -> dict:
    return {
        "schema_version": next_action.SCHEMA_VERSION,
        "next_action": packet.FINAL_NEXT_ACTION,
        "claude_required": True,
        "context": {
            "tenant_id": "Acme Prod",
            "target_schema": "yt_t_acme_prod",
            "target_url": "postgresql://user:***@example.com/rehearsal",
            "dry_run_json": "output/tenant_acme_dry_run.json",
            "readiness_json": "output/tenant_acme_readiness.json",
            "handoff_json": "output/tenant_acme_handoff.json",
            "plan_json": "output/tenant_acme_plan.json",
            "source_preflight_json": "output/tenant_acme_source_preflight.json",
            "target_preflight_json": "output/tenant_acme_target_preflight.json",
        },
        "inputs": {},
        "blockers": [],
    }


def test_ready_next_action_generates_implementation_packet(tmp_path):
    next_action_json = _write_json(tmp_path / "next-action.json", _next_action_ready())

    report = packet.build_implementation_packet_report(
        next_action_json,
        output_md=tmp_path / "claude-task.md",
    )

    assert report["schema_version"] == packet.SCHEMA_VERSION
    assert report["ready_for_claude_importer"] is True
    assert report["ready_for_cutover"] is False
    assert report["blockers"] == []
    assert report["tenant_id"] == "Acme Prod"
    assert report["source_preflight_json"].endswith("source_preflight.json")
    assert report["target_preflight_json"].endswith("target_preflight.json")


def test_not_final_next_action_blocks_packet(tmp_path):
    payload = _next_action_ready()
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
    payload = _next_action_ready()
    payload["context"]["source_preflight_json"] = ""
    next_action_json = _write_json(tmp_path / "next-action.json", payload)

    report = packet.build_implementation_packet_report(
        next_action_json,
        output_md=tmp_path / "claude-task.md",
    )

    assert report["ready_for_claude_importer"] is False
    assert "next-action report missing source_preflight_json" in report["blockers"]


def test_cli_writes_json_and_markdown(tmp_path):
    next_action_json = _write_json(tmp_path / "next-action.json", _next_action_ready())
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
    assert "tenant_import_rehearsal" in markdown


def test_cli_strict_exits_one_when_blocked(tmp_path):
    payload = _next_action_ready()
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
