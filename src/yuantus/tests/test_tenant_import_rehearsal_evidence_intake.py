from __future__ import annotations

import json
from pathlib import Path

from yuantus.scripts import tenant_import_rehearsal
from yuantus.scripts import tenant_import_rehearsal_evidence as evidence
from yuantus.scripts import tenant_import_rehearsal_evidence_archive as archive
from yuantus.scripts import tenant_import_rehearsal_evidence_intake as intake
from yuantus.scripts import tenant_import_rehearsal_evidence_template as template
from yuantus.scripts import tenant_import_rehearsal_operator_packet as operator_packet


_TARGET_URL_REDACTED = "postgresql://user:***@example.com/rehearsal"
_TARGET_URL_PLAINTEXT = "postgresql://user:s3cr3t@example.com/rehearsal"


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _paths(tmp_path: Path) -> dict[str, str]:
    return {
        "rehearsal_json": str(tmp_path / "rehearsal.json"),
        "rehearsal_md": str(tmp_path / "rehearsal.md"),
        "operator_evidence_template_json": str(tmp_path / "template.json"),
        "operator_evidence_md": str(tmp_path / "operator-evidence.md"),
        "evidence_json": str(tmp_path / "evidence.json"),
        "evidence_md": str(tmp_path / "evidence.md"),
        "archive_json": str(tmp_path / "archive.json"),
        "archive_md": str(tmp_path / "archive.md"),
    }


def _write_operator_packet(tmp_path: Path, outputs: dict[str, str]) -> Path:
    return _write_json(
        tmp_path / "operator-packet.json",
        {
            "schema_version": operator_packet.SCHEMA_VERSION,
            "tenant_id": "Acme Prod",
            "target_schema": "yt_t_acme_prod",
            "target_url": _TARGET_URL_REDACTED,
            "ready_for_operator_execution": True,
            "ready_for_cutover": False,
            "outputs": outputs,
            "blockers": [],
        },
    )


def _write_green_artifacts(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    outputs = _paths(tmp_path)
    _write_json(
        Path(outputs["rehearsal_json"]),
        {
            "schema_version": tenant_import_rehearsal.SCHEMA_VERSION,
            "tenant_id": "Acme Prod",
            "target_schema": "yt_t_acme_prod",
            "target_url": _TARGET_URL_REDACTED,
            "ready_for_rehearsal_import": True,
            "import_executed": True,
            "db_connection_attempted": True,
            "ready_for_cutover": False,
            "blockers": [],
        },
    )
    _write_text(Path(outputs["rehearsal_md"]), "# Rehearsal\n")
    _write_json(
        Path(outputs["operator_evidence_template_json"]),
        {
            "schema_version": template.SCHEMA_VERSION,
            "tenant_id": "Acme Prod",
            "target_schema": "yt_t_acme_prod",
            "target_url": _TARGET_URL_REDACTED,
            "ready_for_operator_evidence_template": True,
            "ready_for_cutover": False,
            "blockers": [],
        },
    )
    _write_text(
        Path(outputs["operator_evidence_md"]),
        "\n".join(
            [
                "# Tenant Import Rehearsal Operator Evidence",
                "",
                "## Rehearsal Evidence Sign-Off",
                "",
                "```text",
                "Pilot tenant: Acme Prod",
                f"Non-production rehearsal DB: {_TARGET_URL_REDACTED}",
                "Backup/restore owner: Ops Owner",
                "Rehearsal window: 2026-04-30T10:00:00Z/2026-04-30T12:00:00Z",
                "Rehearsal executed by: Platform Operator",
                "Rehearsal result: pass",
                "Evidence reviewer: Platform Reviewer",
                "Date: 2026-04-30",
                "```",
                "",
            ]
        ),
    )
    _write_json(
        Path(outputs["evidence_json"]),
        {
            "schema_version": evidence.SCHEMA_VERSION,
            "tenant_id": "Acme Prod",
            "target_schema": "yt_t_acme_prod",
            "target_url": _TARGET_URL_REDACTED,
            "ready_for_rehearsal_evidence": True,
            "operator_rehearsal_evidence_accepted": True,
            "ready_for_cutover": False,
            "blockers": [],
        },
    )
    _write_text(Path(outputs["evidence_md"]), "# Evidence\n")
    _write_json(
        Path(outputs["archive_json"]),
        {
            "schema_version": archive.SCHEMA_VERSION,
            "tenant_id": "Acme Prod",
            "target_schema": "yt_t_acme_prod",
            "target_url": _TARGET_URL_REDACTED,
            "ready_for_archive": True,
            "ready_for_cutover": False,
            "artifacts": [],
            "blockers": [],
        },
    )
    _write_text(Path(outputs["archive_md"]), "# Archive\n")
    return _write_operator_packet(tmp_path, outputs), outputs


def test_green_evidence_artifact_set_is_intake_ready(tmp_path):
    operator_packet_json, _outputs = _write_green_artifacts(tmp_path)

    report = intake.build_evidence_intake_report(
        operator_packet_json=operator_packet_json,
    )

    assert report["schema_version"] == intake.SCHEMA_VERSION
    assert report["ready_for_evidence_intake"] is True
    assert report["ready_for_cutover"] is False
    assert report["redaction_ready"] is True
    assert report["artifact_count"] == 8
    assert report["blockers"] == []


def test_missing_required_artifact_blocks_intake(tmp_path):
    operator_packet_json, outputs = _write_green_artifacts(tmp_path)
    Path(outputs["archive_md"]).unlink()

    report = intake.build_evidence_intake_report(
        operator_packet_json=operator_packet_json,
    )

    assert report["ready_for_evidence_intake"] is False
    assert f"archive_md {outputs['archive_md']} does not exist" in report["blockers"]


def test_synthetic_json_artifact_blocks_intake(tmp_path):
    operator_packet_json, outputs = _write_green_artifacts(tmp_path)
    payload = json.loads(Path(outputs["evidence_json"]).read_text())
    payload["synthetic_drill"] = True
    payload["real_rehearsal_evidence"] = False
    _write_json(Path(outputs["evidence_json"]), payload)

    report = intake.build_evidence_intake_report(
        operator_packet_json=operator_packet_json,
    )

    assert report["ready_for_evidence_intake"] is False
    assert "evidence_json must not be synthetic drill output" in report["blockers"]
    assert any(
        item["artifact"] == "evidence_json" and item["synthetic_drill"] is True
        for item in report["artifacts"]
    )


def test_synthetic_markdown_artifact_blocks_intake(tmp_path):
    operator_packet_json, outputs = _write_green_artifacts(tmp_path)
    _write_text(
        Path(outputs["operator_evidence_md"]),
        "Synthetic drill: `true`\nReal rehearsal evidence: `false`\n",
    )

    report = intake.build_evidence_intake_report(
        operator_packet_json=operator_packet_json,
    )

    assert report["ready_for_evidence_intake"] is False
    assert "operator_evidence_md must not be synthetic drill output" in report["blockers"]


def test_plaintext_postgres_password_blocks_without_leaking_secret(tmp_path):
    operator_packet_json, outputs = _write_green_artifacts(tmp_path)
    _write_text(
        Path(outputs["operator_evidence_md"]),
        f"Non-production rehearsal DB: {_TARGET_URL_PLAINTEXT}\n",
    )

    report = intake.build_evidence_intake_report(
        operator_packet_json=operator_packet_json,
    )
    rendered = json.dumps(report, sort_keys=True) + intake.render_markdown_report(report)

    assert report["ready_for_evidence_intake"] is False
    assert "redaction scan must be clean before evidence intake" in report["blockers"]
    assert "s3cr3t" not in rendered
    assert _TARGET_URL_REDACTED in rendered


def test_cli_writes_json_and_markdown_for_green_intake(tmp_path):
    operator_packet_json, _outputs = _write_green_artifacts(tmp_path)
    output_json = tmp_path / "intake.json"
    output_md = tmp_path / "intake.md"

    exit_code = intake.main(
        [
            "--operator-packet-json",
            str(operator_packet_json),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--strict",
        ]
    )

    assert exit_code == 0
    assert json.loads(output_json.read_text())["ready_for_evidence_intake"] is True
    assert "Ready for evidence intake: `true`" in output_md.read_text()


def test_cli_strict_returns_one_for_blocked_intake(tmp_path):
    operator_packet_json, outputs = _write_green_artifacts(tmp_path)
    Path(outputs["archive_json"]).unlink()

    exit_code = intake.main(
        [
            "--operator-packet-json",
            str(operator_packet_json),
            "--output-json",
            str(tmp_path / "intake.json"),
            "--output-md",
            str(tmp_path / "intake.md"),
            "--strict",
        ]
    )

    assert exit_code == 1


def test_source_preserves_db_free_intake_only_scope():
    source = Path(intake.__file__).read_text()

    assert "TENANCY_MODE" not in source
    assert "create_engine" not in source
    assert "Session" not in source
    assert "build_evidence_handoff_report" not in source
    assert "build_rehearsal_evidence_archive_report" not in source
    assert '"ready_for_cutover": False' in source
