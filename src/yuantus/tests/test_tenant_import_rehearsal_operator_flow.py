from __future__ import annotations

import json
from pathlib import Path

from yuantus.scripts import tenant_import_rehearsal_external_status as external_status
from yuantus.scripts import tenant_import_rehearsal_operator_bundle as operator_bundle
from yuantus.scripts import tenant_import_rehearsal_operator_flow as flow
from yuantus.scripts import tenant_import_rehearsal_operator_packet as operator_packet
from yuantus.scripts import tenant_import_rehearsal_operator_request as operator_request
from yuantus.tests.test_tenant_import_rehearsal_external_status import (
    _write_operator_packet,
)


def test_green_operator_packet_builds_status_request_and_bundle(tmp_path):
    operator_packet_json, _operator_report = _write_operator_packet(tmp_path)

    report = flow.build_operator_flow_report(
        operator_packet_json=operator_packet_json,
        artifact_prefix=tmp_path / "tenant_acme_flow",
    )

    assert report["schema_version"] == flow.SCHEMA_VERSION
    assert report["ready_for_operator_flow"] is True
    assert report["ready_for_cutover"] is False
    assert report["current_stage"] == "awaiting_row_copy_rehearsal"
    assert report["next_command_name"] == "row_copy_rehearsal"
    outputs = report["outputs"]
    status_payload = json.loads(Path(outputs["external_status_json"]).read_text())
    request_payload = json.loads(Path(outputs["operator_request_json"]).read_text())
    bundle_payload = json.loads(Path(outputs["operator_bundle_json"]).read_text())
    assert status_payload["schema_version"] == external_status.SCHEMA_VERSION
    assert request_payload["schema_version"] == operator_request.SCHEMA_VERSION
    assert bundle_payload["schema_version"] == operator_bundle.SCHEMA_VERSION
    assert bundle_payload["ready_for_operator_bundle"] is True


def test_blocked_operator_packet_writes_all_outputs_and_returns_blocked(tmp_path):
    operator_packet_json, _operator_report = _write_operator_packet(tmp_path)
    payload = json.loads(operator_packet_json.read_text())
    payload["ready_for_operator_execution"] = False
    payload["blockers"] = ["operator packet not ready"]
    operator_packet_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    report = flow.build_operator_flow_report(
        operator_packet_json=operator_packet_json,
        artifact_prefix=tmp_path / "tenant_acme_flow",
    )

    assert report["ready_for_operator_flow"] is False
    assert report["ready_for_cutover"] is False
    assert "external status must have ready_for_external_progress=true" in report["blockers"]
    assert "operator request must have ready_for_operator_request=true" in report["blockers"]
    assert "operator bundle must have ready_for_operator_bundle=true" in report["blockers"]
    for path in report["outputs"].values():
        assert Path(path).is_file()


def test_cli_writes_summary_json_and_markdown(tmp_path):
    operator_packet_json, _operator_report = _write_operator_packet(tmp_path)
    output_json = tmp_path / "flow.json"
    output_md = tmp_path / "flow.md"

    exit_code = flow.main(
        [
            "--operator-packet-json",
            str(operator_packet_json),
            "--artifact-prefix",
            str(tmp_path / "tenant_acme_flow"),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--strict",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text())
    assert payload["ready_for_operator_flow"] is True
    markdown = output_md.read_text()
    assert "Ready for operator flow: `true`" in markdown
    assert "Ready for cutover: `false`" in markdown
    assert "operator_bundle_md" in markdown


def test_cli_strict_returns_one_for_blocked_flow(tmp_path):
    operator_packet_json, _operator_report = _write_operator_packet(tmp_path)
    payload = json.loads(operator_packet_json.read_text())
    payload["schema_version"] = "wrong"
    operator_packet_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    exit_code = flow.main(
        [
            "--operator-packet-json",
            str(operator_packet_json),
            "--artifact-prefix",
            str(tmp_path / "tenant_acme_flow"),
            "--output-json",
            str(tmp_path / "flow.json"),
            "--output-md",
            str(tmp_path / "flow.md"),
            "--strict",
        ]
    )

    assert exit_code == 1


def test_source_preserves_operator_flow_only_scope():
    source = Path(flow.__file__).read_text()

    assert "TENANCY_MODE" not in source
    assert "create_engine" not in source
    assert "Session" not in source
    assert "subprocess" not in source
    assert "tenant_import_rehearsal import" not in source
    assert '"ready_for_cutover": False' in source
    assert operator_packet.SCHEMA_VERSION
