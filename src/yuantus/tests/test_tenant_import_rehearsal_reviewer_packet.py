from __future__ import annotations

import json
from pathlib import Path

from yuantus.scripts import tenant_import_rehearsal_evidence_handoff as handoff
from yuantus.scripts import tenant_import_rehearsal_evidence_intake as intake
from yuantus.scripts import tenant_import_rehearsal_reviewer_packet as reviewer


_TARGET_URL_REDACTED = "postgresql://user:***@example.com/rehearsal"


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _intake_payload(**overrides) -> dict:
    payload = {
        "schema_version": intake.SCHEMA_VERSION,
        "tenant_id": "Acme Prod",
        "target_schema": "yt_t_acme_prod",
        "target_url": _TARGET_URL_REDACTED,
        "artifact_count": 2,
        "redaction_artifact_count": 2,
        "redaction_ready": True,
        "ready_for_evidence_intake": True,
        "ready_for_cutover": False,
        "artifacts": [
            {
                "artifact": "rehearsal_json",
                "path": "output/rehearsal.json",
                "ready": True,
                "synthetic_drill": False,
            },
            {
                "artifact": "operator_evidence_md",
                "path": "output/operator-evidence.md",
                "ready": True,
                "synthetic_drill": False,
            },
        ],
        "blockers": [],
    }
    payload.update(overrides)
    return payload


def _handoff_payload(**overrides) -> dict:
    payload = {
        "schema_version": handoff.SCHEMA_VERSION,
        "tenant_id": "Acme Prod",
        "target_schema": "yt_t_acme_prod",
        "target_url": _TARGET_URL_REDACTED,
        "archive_artifact_count": 2,
        "redaction_artifact_count": 2,
        "ready_for_evidence_handoff": True,
        "ready_for_cutover": False,
        "archive_artifacts": [
            {
                "artifact": "rehearsal_json",
                "path": "output/rehearsal.json",
                "ready": True,
                "sha256": "a" * 64,
            },
            {
                "artifact": "operator_evidence_md",
                "path": "output/operator-evidence.md",
                "ready": True,
                "sha256": "b" * 64,
            },
        ],
        "blockers": [],
    }
    payload.update(overrides)
    return payload


def _green_reports(tmp_path: Path) -> tuple[Path, Path]:
    intake_json = _write_json(tmp_path / "intake.json", _intake_payload())
    handoff_json = _write_json(tmp_path / "handoff.json", _handoff_payload())
    return intake_json, handoff_json


def test_green_intake_and_handoff_build_reviewer_packet(tmp_path):
    intake_json, handoff_json = _green_reports(tmp_path)

    report = reviewer.build_reviewer_packet_report(
        evidence_intake_json=intake_json,
        evidence_handoff_json=handoff_json,
    )

    assert report["schema_version"] == reviewer.SCHEMA_VERSION
    assert report["ready_for_reviewer_packet"] is True
    assert report["ready_for_cutover"] is False
    assert report["tenant_id"] == "Acme Prod"
    assert report["intake_artifact_count"] == 2
    assert report["handoff_archive_artifact_count"] == 2
    assert report["blockers"] == []


def test_blocked_intake_blocks_reviewer_packet(tmp_path):
    intake_json = _write_json(
        tmp_path / "intake.json",
        _intake_payload(
            ready_for_evidence_intake=False,
            blockers=["intake blocker"],
        ),
    )
    handoff_json = _write_json(tmp_path / "handoff.json", _handoff_payload())

    report = reviewer.build_reviewer_packet_report(
        evidence_intake_json=intake_json,
        evidence_handoff_json=handoff_json,
    )

    assert report["ready_for_reviewer_packet"] is False
    assert "evidence intake must have ready_for_evidence_intake=true" in report["blockers"]
    assert "evidence intake must have no blockers" in report["blockers"]


def test_blocked_handoff_blocks_reviewer_packet(tmp_path):
    intake_json = _write_json(tmp_path / "intake.json", _intake_payload())
    handoff_json = _write_json(
        tmp_path / "handoff.json",
        _handoff_payload(
            ready_for_evidence_handoff=False,
            blockers=["handoff blocker"],
        ),
    )

    report = reviewer.build_reviewer_packet_report(
        evidence_intake_json=intake_json,
        evidence_handoff_json=handoff_json,
    )

    assert report["ready_for_reviewer_packet"] is False
    assert "evidence handoff must have ready_for_evidence_handoff=true" in report["blockers"]
    assert "evidence handoff must have no blockers" in report["blockers"]


def test_context_mismatch_blocks_reviewer_packet(tmp_path):
    intake_json = _write_json(tmp_path / "intake.json", _intake_payload())
    handoff_json = _write_json(
        tmp_path / "handoff.json",
        _handoff_payload(target_schema="yt_t_other"),
    )

    report = reviewer.build_reviewer_packet_report(
        evidence_intake_json=intake_json,
        evidence_handoff_json=handoff_json,
    )

    assert report["ready_for_reviewer_packet"] is False
    assert "target_schema must match between intake and handoff reports" in report["blockers"]


def test_cutover_true_in_upstream_reports_blocks_reviewer_packet(tmp_path):
    intake_json = _write_json(
        tmp_path / "intake.json",
        _intake_payload(ready_for_cutover=True),
    )
    handoff_json = _write_json(
        tmp_path / "handoff.json",
        _handoff_payload(ready_for_cutover=True),
    )

    report = reviewer.build_reviewer_packet_report(
        evidence_intake_json=intake_json,
        evidence_handoff_json=handoff_json,
    )

    assert report["ready_for_reviewer_packet"] is False
    assert "evidence intake must have ready_for_cutover=false" in report["blockers"]
    assert "evidence handoff must have ready_for_cutover=false" in report["blockers"]
    assert report["ready_for_cutover"] is False


def test_cli_writes_json_and_markdown_for_green_packet(tmp_path):
    intake_json, handoff_json = _green_reports(tmp_path)
    output_json = tmp_path / "reviewer-packet.json"
    output_md = tmp_path / "reviewer-packet.md"

    exit_code = reviewer.main(
        [
            "--evidence-intake-json",
            str(intake_json),
            "--evidence-handoff-json",
            str(handoff_json),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--strict",
        ]
    )

    assert exit_code == 0
    assert json.loads(output_json.read_text())["ready_for_reviewer_packet"] is True
    markdown = output_md.read_text()
    assert "Ready for reviewer packet: `true`" in markdown
    assert "Ready for cutover: `false`" in markdown


def test_cli_strict_returns_one_for_blocked_packet(tmp_path):
    intake_json = _write_json(
        tmp_path / "intake.json",
        _intake_payload(ready_for_evidence_intake=False),
    )
    handoff_json = _write_json(tmp_path / "handoff.json", _handoff_payload())

    exit_code = reviewer.main(
        [
            "--evidence-intake-json",
            str(intake_json),
            "--evidence-handoff-json",
            str(handoff_json),
            "--output-json",
            str(tmp_path / "reviewer-packet.json"),
            "--output-md",
            str(tmp_path / "reviewer-packet.md"),
            "--strict",
        ]
    )

    assert exit_code == 1


def test_source_preserves_reviewer_packet_only_scope():
    source = Path(reviewer.__file__).read_text()

    assert "TENANCY_MODE" not in source
    assert "create_engine" not in source
    assert "Session" not in source
    assert "build_rehearsal_evidence_archive_report" not in source
    assert "build_evidence_handoff_report" not in source
    assert '"ready_for_cutover": False' in source
