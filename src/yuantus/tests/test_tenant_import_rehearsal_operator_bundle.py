from __future__ import annotations

import json
from pathlib import Path

from yuantus.scripts import tenant_import_rehearsal_operator_bundle as bundle
from yuantus.scripts import tenant_import_rehearsal_operator_request as operator_request


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _request_payload(**overrides) -> dict:
    payload = {
        "schema_version": operator_request.SCHEMA_VERSION,
        "external_status_json": "output/tenant_acme_external_status.json",
        "external_status_schema_version": "p3.4.2-tenant-import-rehearsal-external-status-v1",
        "tenant_id": "Acme Prod",
        "target_schema": "yt_t_acme_prod",
        "target_url": "postgresql://user:***@example.com/rehearsal",
        "current_stage": "awaiting_row_copy_rehearsal",
        "next_action": "run_row_copy_rehearsal",
        "next_command_name": "row_copy_rehearsal",
        "next_command": (
            "PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal\n"
            "  --source-url \"${SOURCE_DATABASE_URL}\"\n"
            "  --target-url \"${TARGET_DATABASE_URL}\"\n"
            "  --confirm-rehearsal"
        ),
        "required_operator_inputs": [
            "SOURCE_DATABASE_URL environment variable",
            "TARGET_DATABASE_URL environment variable",
            "operator confirmation that the target is non-production",
        ],
        "artifacts": [
            {
                "artifact": "rehearsal_json",
                "path": "output/tenant_acme_import_rehearsal.json",
                "exists": False,
                "ready": False,
            }
        ],
        "ready_for_operator_request": True,
        "ready_for_cutover": False,
        "blockers": [],
    }
    payload.update(overrides)
    return payload


def test_green_operator_request_builds_db_free_bundle(tmp_path):
    request_json = _write_json(tmp_path / "operator-request.json", _request_payload())

    report = bundle.build_operator_bundle_report(operator_request_json=request_json)

    assert report["schema_version"] == bundle.SCHEMA_VERSION
    assert report["ready_for_operator_bundle"] is True
    assert report["ready_for_cutover"] is False
    assert report["current_stage"] == "awaiting_row_copy_rehearsal"
    assert [command["name"] for command in report["commands"]] == [
        "safety_readme",
        "env_check_1",
        "env_check_2",
        "row_copy_rehearsal",
    ]
    commands = "\n".join(command["command"] for command in report["commands"])
    assert 'test -n "${SOURCE_DATABASE_URL:-}"' in commands
    assert 'test -n "${TARGET_DATABASE_URL:-}"' in commands
    assert "tenant_import_rehearsal" in commands
    assert "secret" not in json.dumps(report)


def test_archive_ready_stage_builds_manual_review_bundle(tmp_path):
    request_json = _write_json(
        tmp_path / "operator-request.json",
        _request_payload(
            current_stage="rehearsal_archive_ready",
            next_action="review_archive_and_hold_cutover_gate",
            next_command_name="",
            next_command="",
            required_operator_inputs=[
                "operator review of archive manifest",
                "hold production cutover gate",
            ],
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

    report = bundle.build_operator_bundle_report(operator_request_json=request_json)

    assert report["ready_for_operator_bundle"] is True
    assert report["ready_for_cutover"] is False
    assert report["commands"][-1]["name"] == "manual_review"
    assert "No command is required" in report["commands"][-1]["command"]


def test_blocked_operator_request_blocks_bundle(tmp_path):
    request_json = _write_json(
        tmp_path / "operator-request.json",
        _request_payload(
            ready_for_operator_request=False,
            blockers=["external status must have no blockers"],
        ),
    )

    report = bundle.build_operator_bundle_report(operator_request_json=request_json)

    assert report["ready_for_operator_bundle"] is False
    assert "operator request must have ready_for_operator_request=true" in report["blockers"]
    assert "operator request must have no blockers" in report["blockers"]
    assert report["ready_for_cutover"] is False


def test_invalid_schema_blocks_bundle(tmp_path):
    request_json = _write_json(
        tmp_path / "operator-request.json",
        _request_payload(schema_version="wrong"),
    )

    report = bundle.build_operator_bundle_report(operator_request_json=request_json)

    assert report["ready_for_operator_bundle"] is False
    assert (
        f"operator request schema_version must be {operator_request.SCHEMA_VERSION}"
        in report["blockers"]
    )


def test_cli_writes_json_and_markdown_for_green_request(tmp_path):
    request_json = _write_json(tmp_path / "operator-request.json", _request_payload())
    output_json = tmp_path / "operator-bundle.json"
    output_md = tmp_path / "operator-bundle.md"

    exit_code = bundle.main(
        [
            "--operator-request-json",
            str(request_json),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--strict",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text())
    assert payload["ready_for_operator_bundle"] is True
    markdown = output_md.read_text()
    assert "Ready for operator bundle: `true`" in markdown
    assert "Ready for cutover: `false`" in markdown
    assert "row_copy_rehearsal" in markdown


def test_cli_strict_returns_one_for_blocked_bundle(tmp_path):
    request_json = _write_json(
        tmp_path / "operator-request.json",
        _request_payload(ready_for_operator_request=False),
    )

    exit_code = bundle.main(
        [
            "--operator-request-json",
            str(request_json),
            "--output-json",
            str(tmp_path / "operator-bundle.json"),
            "--output-md",
            str(tmp_path / "operator-bundle.md"),
            "--strict",
        ]
    )

    assert exit_code == 1


def test_source_preserves_operator_bundle_only_scope():
    source = Path(bundle.__file__).read_text()

    assert "TENANCY_MODE" not in source
    assert "create_engine" not in source
    assert "Session" not in source
    assert "subprocess" not in source
    assert "tenant_import_rehearsal import" not in source
    assert '"ready_for_cutover": False' in source
