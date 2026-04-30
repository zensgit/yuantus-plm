from __future__ import annotations

import json
from pathlib import Path

from yuantus.scripts import tenant_import_rehearsal_synthetic_drill as drill


def test_synthetic_drill_writes_artifacts_and_redaction_report(tmp_path):
    report = drill.build_synthetic_drill_report(
        artifact_dir=tmp_path / "artifacts",
        artifact_prefix="sample",
    )

    assert report["schema_version"] == drill.SCHEMA_VERSION
    assert report["synthetic_drill"] is True
    assert report["real_rehearsal_evidence"] is False
    assert report["db_connection_attempted"] is False
    assert report["ready_for_synthetic_drill"] is True
    assert report["ready_for_operator_evidence"] is False
    assert report["ready_for_evidence_handoff"] is False
    assert report["ready_for_cutover"] is False
    assert report["blockers"] == []
    assert len(report["artifacts"]) == 3
    assert Path(report["redaction_guard_json"]).is_file()
    redaction_report = json.loads(Path(report["redaction_guard_json"]).read_text())
    assert redaction_report["ready_for_artifact_handoff"] is True
    assert redaction_report["ready_for_cutover"] is False


def test_synthetic_artifacts_are_marked_as_not_real_evidence(tmp_path):
    report = drill.build_synthetic_drill_report(artifact_dir=tmp_path)

    for item in report["artifacts"]:
        assert item["synthetic_drill"] is True
        assert item["real_rehearsal_evidence"] is False

    external_status = json.loads(
        (tmp_path / "tenant_import_rehearsal_synthetic_drill_external_status.json")
        .read_text()
    )
    assert external_status["synthetic_drill"] is True
    assert external_status["real_rehearsal_evidence"] is False
    assert external_status["ready_for_external_progress"] is False
    assert external_status["ready_for_cutover"] is False
    assert external_status["blockers"]


def test_plaintext_secret_blocks_without_leaking_secret(tmp_path):
    report = drill.build_synthetic_drill_report(
        artifact_dir=tmp_path,
        inject_plaintext_secret_for_test=True,
    )
    rendered = json.dumps(report, sort_keys=True) + drill.render_markdown_report(report)

    assert report["ready_for_synthetic_drill"] is False
    assert report["ready_for_cutover"] is False
    assert "not-a-real-secret" not in rendered
    assert "postgresql://synthetic:***@example.invalid/rehearsal" in rendered


def test_markdown_report_makes_non_evidence_boundary_explicit(tmp_path):
    report = drill.build_synthetic_drill_report(artifact_dir=tmp_path)

    markdown = drill.render_markdown_report(report)

    assert "## This Is Not Evidence" in markdown
    assert "Real rehearsal evidence: `false`" in markdown
    assert "Ready for evidence handoff: `false`" in markdown
    assert "Ready for cutover: `false`" in markdown


def test_cli_writes_json_and_markdown_for_clean_drill(tmp_path):
    output_json = tmp_path / "drill.json"
    output_md = tmp_path / "drill.md"

    exit_code = drill.main(
        [
            "--artifact-dir",
            str(tmp_path / "artifacts"),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--strict",
        ]
    )

    assert exit_code == 0
    assert json.loads(output_json.read_text())["ready_for_synthetic_drill"] is True
    assert "Ready for synthetic drill: `true`" in output_md.read_text()


def test_cli_strict_returns_one_for_injected_plaintext_secret(tmp_path):
    exit_code = drill.main(
        [
            "--artifact-dir",
            str(tmp_path / "artifacts"),
            "--output-json",
            str(tmp_path / "drill.json"),
            "--output-md",
            str(tmp_path / "drill.md"),
            "--inject-plaintext-secret-for-test",
            "--strict",
        ]
    )

    assert exit_code == 1


def test_source_preserves_synthetic_drill_only_scope():
    source = Path(drill.__file__).read_text()

    assert "TENANCY_MODE" not in source
    assert "create_engine" not in source
    assert "Session" not in source
    assert "tenant_import_rehearsal_evidence_handoff" not in source
    assert "tenant_import_rehearsal_evidence_archive" not in source
    assert '"ready_for_cutover": False' in source
