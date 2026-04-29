from __future__ import annotations

import json
from pathlib import Path

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


def _write_green_packet(tmp_path: Path) -> Path:
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
    report = packet.build_implementation_packet_report(
        next_action_json,
        output_md=tmp_path / "claude-task.md",
    )
    return _write_json(tmp_path / "implementation-packet.json", report)


def test_green_packet_builds_ordered_operator_commands(tmp_path):
    implementation_packet_json = _write_green_packet(tmp_path)

    report = operator_packet.build_operator_packet_report(
        implementation_packet_json=implementation_packet_json,
        artifact_prefix="output/acme-prod",
    )

    assert report["schema_version"] == operator_packet.SCHEMA_VERSION
    assert report["ready_for_operator_execution"] is True
    assert report["ready_for_cutover"] is False
    assert report["blockers"] == []
    assert [command["name"] for command in report["commands"]] == [
        "row_copy_rehearsal",
        "operator_evidence_template",
        "evidence_gate",
        "archive_manifest",
    ]
    assert report["outputs"]["archive_json"] == (
        "output/acme-prod_import_rehearsal_evidence_archive.json"
    )
    commands = "\n".join(command["command"] for command in report["commands"])
    assert "${SOURCE_DATABASE_URL}" in commands
    assert "${TARGET_DATABASE_URL}" in commands
    assert "secret" not in json.dumps(report)


def test_default_artifact_prefix_uses_target_schema(tmp_path):
    implementation_packet_json = _write_green_packet(tmp_path)

    report = operator_packet.build_operator_packet_report(
        implementation_packet_json=implementation_packet_json,
    )

    assert report["artifact_prefix"] == "output/yt_t_acme_prod"
    assert report["outputs"]["rehearsal_json"] == (
        "output/yt_t_acme_prod_import_rehearsal.json"
    )


def test_invalid_env_names_block(tmp_path):
    implementation_packet_json = _write_green_packet(tmp_path)

    report = operator_packet.build_operator_packet_report(
        implementation_packet_json=implementation_packet_json,
        source_url_env="source-url",
        target_url_env="target-url",
    )

    assert report["ready_for_operator_execution"] is False
    assert "source_url_env must be an uppercase shell environment variable name" in report["blockers"]
    assert "target_url_env must be an uppercase shell environment variable name" in report["blockers"]


def test_blocked_implementation_packet_blocks_operator_packet(tmp_path):
    implementation_packet_json = _write_green_packet(tmp_path)
    payload = json.loads(implementation_packet_json.read_text())
    payload["ready_for_claude_importer"] = False
    payload["ready_for_cutover"] = True
    payload["blockers"] = ["upstream missing"]
    _write_json(implementation_packet_json, payload)

    report = operator_packet.build_operator_packet_report(
        implementation_packet_json=implementation_packet_json,
    )

    assert report["ready_for_operator_execution"] is False
    assert "implementation packet must have ready_for_claude_importer=true" in report["blockers"]
    assert "implementation packet must have ready_for_cutover=false" in report["blockers"]
    assert "implementation packet must have no blockers" in report["blockers"]


def test_stale_upstream_artifact_blocks_operator_packet(tmp_path):
    implementation_packet_json = _write_green_packet(tmp_path)
    dry_run_path = tmp_path / "dry_run_json"
    payload = json.loads(dry_run_path.read_text())
    payload["ready_for_import"] = False
    payload["blockers"] = ["source drifted"]
    _write_json(dry_run_path, payload)

    report = operator_packet.build_operator_packet_report(
        implementation_packet_json=implementation_packet_json,
    )

    assert report["ready_for_operator_execution"] is False
    assert "fresh dry-run artifact must have ready_for_import=true" in report["blockers"]
    assert "fresh dry-run artifact must have no blockers" in report["blockers"]


def test_cli_writes_json_and_markdown(tmp_path):
    implementation_packet_json = _write_green_packet(tmp_path)
    output_json = tmp_path / "operator-packet.json"
    output_md = tmp_path / "operator-packet.md"

    exit_code = operator_packet.main(
        [
            "--implementation-packet-json",
            str(implementation_packet_json),
            "--artifact-prefix",
            "output/acme-prod",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--strict",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text())
    assert payload["ready_for_operator_execution"] is True
    markdown = output_md.read_text()
    assert "Tenant Import Rehearsal Operator Packet" in markdown
    assert "row_copy_rehearsal" in markdown
    assert "Ready for cutover: `false`" in markdown


def test_strict_cli_returns_one_when_blocked(tmp_path):
    implementation_packet_json = _write_green_packet(tmp_path)
    payload = json.loads(implementation_packet_json.read_text())
    payload["ready_for_claude_importer"] = False
    _write_json(implementation_packet_json, payload)
    output_json = tmp_path / "operator-packet.json"
    output_md = tmp_path / "operator-packet.md"

    exit_code = operator_packet.main(
        [
            "--implementation-packet-json",
            str(implementation_packet_json),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--strict",
        ]
    )

    assert exit_code == 1
    assert json.loads(output_json.read_text())["ready_for_operator_execution"] is False


def test_source_preserves_operator_packet_only_scope():
    source = Path(operator_packet.__file__).read_text()

    assert "create_engine" not in source
    assert "TENANCY_MODE" not in source
    assert "ready_for_cutover\": False" in source
