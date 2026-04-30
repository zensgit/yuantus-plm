from __future__ import annotations

import json
from pathlib import Path

from yuantus.scripts import tenant_import_rehearsal_operator_flow as operator_flow
from yuantus.scripts import tenant_import_rehearsal_operator_launchpack as launchpack
from yuantus.scripts import tenant_import_rehearsal_operator_packet as operator_packet
from yuantus.tests.test_tenant_import_rehearsal_operator_packet import (
    _write_green_packet,
)


def test_green_implementation_packet_builds_launchpack(tmp_path):
    implementation_packet_json = _write_green_packet(tmp_path)

    report = launchpack.build_operator_launchpack_report(
        implementation_packet_json=implementation_packet_json,
        artifact_prefix=str(tmp_path / "tenant_acme"),
        operator_packet_json=tmp_path / "tenant_acme_operator_execution_packet.json",
        operator_packet_md=tmp_path / "tenant_acme_operator_execution_packet.md",
        flow_artifact_prefix=tmp_path / "tenant_acme_operator_flow",
    )

    assert report["schema_version"] == launchpack.SCHEMA_VERSION
    assert report["ready_for_operator_launchpack"] is True
    assert report["ready_for_cutover"] is False
    assert report["ready_for_operator_packet"] is True
    assert report["ready_for_operator_flow"] is True
    assert report["current_stage"] == "awaiting_row_copy_rehearsal"
    assert report["next_command_name"] == "row_copy_rehearsal"
    outputs = report["outputs"]
    assert json.loads(Path(outputs["operator_packet_json"]).read_text())[
        "schema_version"
    ] == operator_packet.SCHEMA_VERSION
    assert json.loads(Path(outputs["operator_bundle_json"]).read_text())[
        "ready_for_operator_bundle"
    ] is True


def test_blocked_implementation_packet_writes_packet_and_blocks_launchpack(tmp_path):
    implementation_packet_json = _write_green_packet(tmp_path)
    payload = json.loads(implementation_packet_json.read_text())
    payload["ready_for_claude_importer"] = False
    payload["blockers"] = ["source drifted"]
    implementation_packet_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    report = launchpack.build_operator_launchpack_report(
        implementation_packet_json=implementation_packet_json,
        artifact_prefix=str(tmp_path / "tenant_acme"),
        operator_packet_json=tmp_path / "tenant_acme_operator_execution_packet.json",
        operator_packet_md=tmp_path / "tenant_acme_operator_execution_packet.md",
        flow_artifact_prefix=tmp_path / "tenant_acme_operator_flow",
    )

    assert report["ready_for_operator_launchpack"] is False
    assert report["ready_for_cutover"] is False
    assert "operator packet must have ready_for_operator_execution=true" in report["blockers"]
    assert "operator flow must have ready_for_operator_flow=true" in report["blockers"]
    assert Path(report["outputs"]["operator_packet_json"]).is_file()
    assert Path(report["outputs"]["operator_bundle_json"]).is_file()


def test_cli_writes_summary_and_all_handoff_artifacts(tmp_path):
    implementation_packet_json = _write_green_packet(tmp_path)
    output_json = tmp_path / "tenant_acme_operator_launchpack.json"
    output_md = tmp_path / "tenant_acme_operator_launchpack.md"

    exit_code = launchpack.main(
        [
            "--implementation-packet-json",
            str(implementation_packet_json),
            "--artifact-prefix",
            str(tmp_path / "tenant_acme"),
            "--operator-packet-json",
            str(tmp_path / "tenant_acme_operator_execution_packet.json"),
            "--operator-packet-md",
            str(tmp_path / "tenant_acme_operator_execution_packet.md"),
            "--flow-artifact-prefix",
            str(tmp_path / "tenant_acme_operator_flow"),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--strict",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text())
    assert payload["ready_for_operator_launchpack"] is True
    assert payload["ready_for_cutover"] is False
    markdown = output_md.read_text()
    assert "Ready for operator launchpack: `true`" in markdown
    assert "operator_bundle_md" in markdown
    assert Path(payload["outputs"]["operator_packet_md"]).is_file()


def test_cli_strict_returns_one_for_blocked_launchpack(tmp_path):
    implementation_packet_json = _write_green_packet(tmp_path)
    payload = json.loads(implementation_packet_json.read_text())
    payload["schema_version"] = "wrong"
    implementation_packet_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    exit_code = launchpack.main(
        [
            "--implementation-packet-json",
            str(implementation_packet_json),
            "--artifact-prefix",
            str(tmp_path / "tenant_acme"),
            "--operator-packet-json",
            str(tmp_path / "tenant_acme_operator_execution_packet.json"),
            "--operator-packet-md",
            str(tmp_path / "tenant_acme_operator_execution_packet.md"),
            "--output-json",
            str(tmp_path / "tenant_acme_operator_launchpack.json"),
            "--output-md",
            str(tmp_path / "tenant_acme_operator_launchpack.md"),
            "--strict",
        ]
    )

    assert exit_code == 1


def test_source_preserves_operator_launchpack_only_scope():
    source = Path(launchpack.__file__).read_text()

    assert "TENANCY_MODE" not in source
    assert "create_engine" not in source
    assert "Session" not in source
    assert "subprocess" not in source
    assert "tenant_import_rehearsal import" not in source
    assert '"ready_for_cutover": False' in source
    assert operator_flow.SCHEMA_VERSION
