from __future__ import annotations

import json
from pathlib import Path

from yuantus.scripts import tenant_import_rehearsal_external_status as external_status
from yuantus.scripts import tenant_import_rehearsal_operator_request as operator_request


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _status_payload(**overrides) -> dict:
    payload = {
        "schema_version": external_status.SCHEMA_VERSION,
        "operator_packet_json": "output/tenant_acme_operator_execution_packet.json",
        "tenant_id": "Acme Prod",
        "target_schema": "yt_t_acme_prod",
        "target_url": "postgresql://user:***@example.com/rehearsal",
        "current_stage": "awaiting_row_copy_rehearsal",
        "next_action": "run_row_copy_rehearsal",
        "next_command_name": "row_copy_rehearsal",
        "next_command": (
            "PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal\n"
            "  --confirm-rehearsal"
        ),
        "ready_for_external_progress": True,
        "ready_for_cutover": False,
        "artifacts": [
            {
                "artifact": "rehearsal_json",
                "path": "output/tenant_acme_import_rehearsal.json",
                "exists": False,
                "ready": False,
            }
        ],
        "blockers": [],
    }
    payload.update(overrides)
    return payload


def test_row_copy_stage_generates_operator_request_with_env_inputs(tmp_path):
    status_json = _write_json(tmp_path / "external-status.json", _status_payload())

    report = operator_request.build_operator_request_report(
        external_status_json=status_json,
    )

    assert report["schema_version"] == operator_request.SCHEMA_VERSION
    assert report["ready_for_operator_request"] is True
    assert report["ready_for_cutover"] is False
    assert report["current_stage"] == "awaiting_row_copy_rehearsal"
    assert report["next_command_name"] == "row_copy_rehearsal"
    assert "SOURCE_DATABASE_URL environment variable" in report["required_operator_inputs"]
    assert "TARGET_DATABASE_URL environment variable" in report["required_operator_inputs"]
    assert report["artifacts"][0]["artifact"] == "rehearsal_json"


def test_blocked_external_status_blocks_operator_request(tmp_path):
    status_json = _write_json(
        tmp_path / "external-status.json",
        _status_payload(
            current_stage="blocked_external_status",
            next_action="fix_blockers",
            next_command_name="",
            next_command="",
            ready_for_external_progress=False,
            blockers=["rehearsal_json must have ready_for_rehearsal_import=true"],
        ),
    )

    report = operator_request.build_operator_request_report(
        external_status_json=status_json,
    )

    assert report["ready_for_operator_request"] is False
    assert "external status must have ready_for_external_progress=true" in report["blockers"]
    assert "external status must have no blockers" in report["blockers"]
    assert (
        "external status current_stage is unsupported: blocked_external_status"
        in report["blockers"]
    )


def test_archive_ready_stage_requests_review_without_command(tmp_path):
    status_json = _write_json(
        tmp_path / "external-status.json",
        _status_payload(
            current_stage="rehearsal_archive_ready",
            next_action="review_archive_and_hold_cutover_gate",
            next_command_name="",
            next_command="",
            artifacts=[
                {
                    "artifact": "archive_json",
                    "path": "output/tenant_acme_import_rehearsal_evidence_archive.json",
                    "exists": True,
                    "ready": True,
                }
            ],
        ),
    )

    report = operator_request.build_operator_request_report(
        external_status_json=status_json,
    )

    assert report["ready_for_operator_request"] is True
    assert report["ready_for_cutover"] is False
    assert report["next_command"] == ""
    assert "hold production cutover gate" in report["required_operator_inputs"]


def test_invalid_schema_blocks_request(tmp_path):
    status_json = _write_json(
        tmp_path / "external-status.json",
        _status_payload(schema_version="wrong"),
    )

    report = operator_request.build_operator_request_report(
        external_status_json=status_json,
    )

    assert report["ready_for_operator_request"] is False
    assert (
        f"external status schema_version must be {external_status.SCHEMA_VERSION}"
        in report["blockers"]
    )


def test_cli_writes_json_and_markdown_for_green_status(tmp_path):
    status_json = _write_json(tmp_path / "external-status.json", _status_payload())
    output_json = tmp_path / "operator-request.json"
    output_md = tmp_path / "operator-request.md"

    exit_code = operator_request.main(
        [
            "--external-status-json",
            str(status_json),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--strict",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text())
    assert payload["ready_for_operator_request"] is True
    markdown = output_md.read_text()
    assert "Ready for operator request: `true`" in markdown
    assert "Ready for cutover: `false`" in markdown
    assert "tenant_import_rehearsal" in markdown


def test_cli_strict_returns_one_for_blocked_status(tmp_path):
    status_json = _write_json(
        tmp_path / "external-status.json",
        _status_payload(ready_for_external_progress=False),
    )

    exit_code = operator_request.main(
        [
            "--external-status-json",
            str(status_json),
            "--output-json",
            str(tmp_path / "operator-request.json"),
            "--output-md",
            str(tmp_path / "operator-request.md"),
            "--strict",
        ]
    )

    assert exit_code == 1


def test_source_preserves_operator_request_only_scope():
    source = Path(operator_request.__file__).read_text()

    assert "TENANCY_MODE" not in source
    assert "create_engine" not in source
    assert "Session" not in source
    assert '"ready_for_cutover": False' in source
