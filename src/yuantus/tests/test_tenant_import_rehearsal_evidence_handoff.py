from __future__ import annotations

import json
from pathlib import Path

from yuantus.scripts import tenant_import_rehearsal_evidence_archive as archive
from yuantus.scripts import tenant_import_rehearsal_evidence_handoff as handoff
from yuantus.scripts import tenant_import_rehearsal_redaction_guard as redaction_guard


_TARGET_URL_REDACTED = "postgresql://user:***@example.com/rehearsal"


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _artifact_files(tmp_path: Path) -> list[Path]:
    paths = [
        tmp_path / "evidence.json",
        tmp_path / "rehearsal.json",
        tmp_path / "operator-evidence.md",
    ]
    for path in paths:
        path.write_text(f"{path.name}\n")
    return paths


def _archive_payload(paths: list[Path], **overrides) -> dict:
    payload = {
        "schema_version": archive.SCHEMA_VERSION,
        "evidence_json": str(paths[0]),
        "operator_evidence_template_json": "",
        "tenant_id": "Acme Prod",
        "target_schema": "yt_t_acme_prod",
        "target_url": _TARGET_URL_REDACTED,
        "ready_for_archive": True,
        "ready_for_cutover": False,
        "artifact_count": len(paths),
        "artifacts": [
            {
                "artifact": path.stem,
                "path": str(path),
                "exists": True,
                "bytes": path.stat().st_size,
                "sha256": "a" * 64,
                "schema_version": "",
                "ready_field": "",
                "ready": True,
            }
            for path in paths
        ],
        "blockers": [],
    }
    payload.update(overrides)
    return payload


def _redaction_payload(paths: list[Path], **overrides) -> dict:
    payload = {
        "schema_version": redaction_guard.SCHEMA_VERSION,
        "artifact_count": len(paths),
        "artifacts": [
            {
                "path": str(path),
                "exists": True,
                "readable": True,
                "postgres_url_count": 0,
                "plaintext_password_count": 0,
                "ready": True,
            }
            for path in paths
        ],
        "ready_for_artifact_handoff": True,
        "ready_for_cutover": False,
        "blockers": [],
    }
    payload.update(overrides)
    return payload


def test_green_archive_and_redaction_guard_allow_evidence_handoff(tmp_path):
    artifacts = _artifact_files(tmp_path)
    archive_json = _write_json(tmp_path / "archive.json", _archive_payload(artifacts))
    redaction_json = _write_json(
        tmp_path / "redaction.json",
        _redaction_payload(artifacts),
    )

    report = handoff.build_evidence_handoff_report(
        archive_json=archive_json,
        redaction_guard_json=redaction_json,
    )

    assert report["schema_version"] == handoff.SCHEMA_VERSION
    assert report["ready_for_evidence_handoff"] is True
    assert report["ready_for_cutover"] is False
    assert report["archive_artifact_count"] == len(artifacts)
    assert report["redaction_artifact_count"] == len(artifacts)
    assert report["blockers"] == []


def test_missing_redaction_coverage_blocks_handoff(tmp_path):
    artifacts = _artifact_files(tmp_path)
    archive_json = _write_json(tmp_path / "archive.json", _archive_payload(artifacts))
    redaction_json = _write_json(
        tmp_path / "redaction.json",
        _redaction_payload(artifacts[:-1]),
    )

    report = handoff.build_evidence_handoff_report(
        archive_json=archive_json,
        redaction_guard_json=redaction_json,
    )

    assert report["ready_for_evidence_handoff"] is False
    assert f"redaction guard missing archive artifact {artifacts[-1]}" in report["blockers"]


def test_blocked_archive_and_redaction_guard_block_handoff(tmp_path):
    artifacts = _artifact_files(tmp_path)
    archive_json = _write_json(
        tmp_path / "archive.json",
        _archive_payload(
            artifacts,
            ready_for_archive=False,
            ready_for_cutover=True,
            blockers=["archive blocker"],
        ),
    )
    redaction_json = _write_json(
        tmp_path / "redaction.json",
        _redaction_payload(
            artifacts,
            ready_for_artifact_handoff=False,
            ready_for_cutover=True,
            blockers=["redaction blocker"],
        ),
    )

    report = handoff.build_evidence_handoff_report(
        archive_json=archive_json,
        redaction_guard_json=redaction_json,
    )

    assert report["ready_for_evidence_handoff"] is False
    assert "archive manifest must have ready_for_archive=true" in report["blockers"]
    assert "archive manifest must have ready_for_cutover=false" in report["blockers"]
    assert "archive manifest must have no blockers" in report["blockers"]
    assert "redaction guard must have ready_for_artifact_handoff=true" in report["blockers"]
    assert "redaction guard must have ready_for_cutover=false" in report["blockers"]
    assert "redaction guard must have no blockers" in report["blockers"]


def test_cli_writes_json_and_markdown_for_green_handoff(tmp_path):
    artifacts = _artifact_files(tmp_path)
    archive_json = _write_json(tmp_path / "archive.json", _archive_payload(artifacts))
    redaction_json = _write_json(
        tmp_path / "redaction.json",
        _redaction_payload(artifacts),
    )
    output_json = tmp_path / "handoff.json"
    output_md = tmp_path / "handoff.md"

    exit_code = handoff.main(
        [
            "--archive-json",
            str(archive_json),
            "--redaction-guard-json",
            str(redaction_json),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--strict",
        ]
    )

    assert exit_code == 0
    assert json.loads(output_json.read_text())["ready_for_evidence_handoff"] is True
    markdown = output_md.read_text()
    assert "Ready for evidence handoff: `true`" in markdown
    assert "Ready for cutover: `false`" in markdown


def test_cli_strict_returns_one_when_redaction_coverage_is_missing(tmp_path):
    artifacts = _artifact_files(tmp_path)
    archive_json = _write_json(tmp_path / "archive.json", _archive_payload(artifacts))
    redaction_json = _write_json(
        tmp_path / "redaction.json",
        _redaction_payload(artifacts[:-1]),
    )

    exit_code = handoff.main(
        [
            "--archive-json",
            str(archive_json),
            "--redaction-guard-json",
            str(redaction_json),
            "--output-json",
            str(tmp_path / "handoff.json"),
            "--output-md",
            str(tmp_path / "handoff.md"),
            "--strict",
        ]
    )

    assert exit_code == 1


def test_source_preserves_handoff_only_scope():
    source = Path(handoff.__file__).read_text()

    assert "TENANCY_MODE" not in source
    assert "create_engine" not in source
    assert "Session" not in source
    assert '"ready_for_cutover": False' in source
