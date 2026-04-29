from __future__ import annotations

import json
from pathlib import Path

from yuantus.scripts import tenant_import_rehearsal_redaction_guard as redaction_guard


_REDACTED_URL = "postgresql://user:***@example.com/rehearsal"
_PLAINTEXT_URL = "postgresql://user:s3cr3t@example.com/rehearsal"


def test_redacted_postgres_urls_pass(tmp_path):
    artifact = tmp_path / "operator-evidence.md"
    artifact.write_text(
        "\n".join(
            [
                "# Operator Evidence",
                f"Non-production rehearsal DB: {_REDACTED_URL}",
            ]
        )
    )

    report = redaction_guard.build_redaction_guard_report(artifacts=[artifact])

    assert report["schema_version"] == redaction_guard.SCHEMA_VERSION
    assert report["ready_for_artifact_handoff"] is True
    assert report["ready_for_cutover"] is False
    assert report["blockers"] == []
    assert report["artifacts"][0]["postgres_url_count"] == 1
    assert report["artifacts"][0]["plaintext_password_count"] == 0


def test_plaintext_postgres_password_blocks_without_leaking_secret(tmp_path):
    artifact = tmp_path / "operator-evidence.md"
    artifact.write_text(
        "\n".join(
            [
                "# Operator Evidence",
                f"Non-production rehearsal DB: {_PLAINTEXT_URL}",
            ]
        )
    )

    report = redaction_guard.build_redaction_guard_report(artifacts=[artifact])

    assert report["ready_for_artifact_handoff"] is False
    assert report["ready_for_cutover"] is False
    assert report["artifacts"][0]["plaintext_password_count"] == 1
    assert "s3cr3t" not in json.dumps(report)
    assert "postgresql://user:***@example.com/rehearsal" in report["blockers"][0]


def test_missing_artifact_blocks(tmp_path):
    missing = tmp_path / "missing.md"

    report = redaction_guard.build_redaction_guard_report(artifacts=[missing])

    assert report["ready_for_artifact_handoff"] is False
    assert f"{missing} does not exist" in report["blockers"]
    assert report["artifacts"][0]["exists"] is False


def test_empty_artifact_list_blocks():
    report = redaction_guard.build_redaction_guard_report(artifacts=[])

    assert report["ready_for_artifact_handoff"] is False
    assert "at least one artifact path is required" in report["blockers"]


def test_cli_writes_json_and_markdown_for_clean_artifact(tmp_path):
    artifact = tmp_path / "external-status.json"
    artifact.write_text(json.dumps({"target_url": _REDACTED_URL}) + "\n")
    output_json = tmp_path / "redaction-guard.json"
    output_md = tmp_path / "redaction-guard.md"

    exit_code = redaction_guard.main(
        [
            "--artifact",
            str(artifact),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--strict",
        ]
    )

    assert exit_code == 0
    assert json.loads(output_json.read_text())["ready_for_artifact_handoff"] is True
    markdown = output_md.read_text()
    assert "Ready for artifact handoff: `true`" in markdown
    assert "Ready for cutover: `false`" in markdown


def test_cli_strict_returns_one_for_plaintext_secret(tmp_path):
    artifact = tmp_path / "operator-evidence.md"
    artifact.write_text(f"Non-production rehearsal DB: {_PLAINTEXT_URL}\n")

    exit_code = redaction_guard.main(
        [
            "--artifact",
            str(artifact),
            "--output-json",
            str(tmp_path / "redaction-guard.json"),
            "--output-md",
            str(tmp_path / "redaction-guard.md"),
            "--strict",
        ]
    )

    assert exit_code == 1


def test_source_preserves_redaction_guard_only_scope():
    source = Path(redaction_guard.__file__).read_text()

    assert "TENANCY_MODE" not in source
    assert "create_engine" not in source
    assert "Session" not in source
    assert '"ready_for_cutover": False' in source
