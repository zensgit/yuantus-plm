from __future__ import annotations

import json
from pathlib import Path

from yuantus.scripts import tenant_import_rehearsal
from yuantus.scripts import tenant_import_rehearsal_evidence as evidence
from yuantus.scripts import tenant_import_rehearsal_evidence_template as template


_TARGET_URL_REDACTED = "postgresql://user:***@example.com/rehearsal"


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _green_rehearsal(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": tenant_import_rehearsal.SCHEMA_VERSION,
            "ready_for_rehearsal_scaffold": True,
            "ready_for_import_execution": True,
            "ready_for_rehearsal_import": True,
            "import_executed": True,
            "db_connection_attempted": True,
            "ready_for_cutover": False,
            "tenant_id": "Acme Prod",
            "target_schema": "yt_t_acme_prod",
            "target_url": _TARGET_URL_REDACTED,
            "table_results": [
                {
                    "table": "meta_items",
                    "source_rows_expected": 2,
                    "target_rows_inserted": 2,
                    "row_count_matches": True,
                }
            ],
            "blockers": [],
        },
    )


def _complete_kwargs(tmp_path: Path) -> dict:
    return {
        "rehearsal_json": _green_rehearsal(tmp_path / "rehearsal.json"),
        "backup_restore_owner": "Ops Owner",
        "rehearsal_window": "2026-04-30T10:00:00Z/2026-04-30T12:00:00Z",
        "rehearsal_executed_by": "Platform Operator",
        "rehearsal_result": "pass",
        "evidence_reviewer": "Platform Reviewer",
        "evidence_date": "2026-04-30",
        "output_md": tmp_path / "operator-evidence.md",
    }


def test_complete_template_is_ready_and_parseable_by_evidence_gate(tmp_path):
    report = template.build_operator_evidence_template_report(**_complete_kwargs(tmp_path))
    markdown = template.render_operator_evidence_markdown(report)
    output_md = tmp_path / "operator-evidence.md"
    output_md.write_text(markdown)

    assert report["schema_version"] == template.SCHEMA_VERSION
    assert report["ready_for_operator_evidence_template"] is True
    assert report["ready_for_cutover"] is False
    assert report["blockers"] == []
    assert report["target_url"] == _TARGET_URL_REDACTED
    assert "secret" not in json.dumps(report)
    parsed = evidence.parse_operator_sign_off(output_md)
    assert parsed["Pilot tenant"] == "Acme Prod"
    assert parsed["Non-production rehearsal DB"] == _TARGET_URL_REDACTED
    assert parsed["Rehearsal result"] == "pass"


def test_missing_operator_fields_blocks_and_renders_placeholders(tmp_path):
    rehearsal_json = _green_rehearsal(tmp_path / "rehearsal.json")

    report = template.build_operator_evidence_template_report(
        rehearsal_json=rehearsal_json,
        output_md=tmp_path / "operator-evidence.md",
    )
    markdown = template.render_operator_evidence_markdown(report)

    assert report["ready_for_operator_evidence_template"] is False
    assert "operator evidence template missing Backup/restore owner" in report["blockers"]
    assert "operator evidence template missing Evidence reviewer" in report["blockers"]
    assert template.PLACEHOLDER in markdown


def test_rehearsal_report_must_be_green(tmp_path):
    rehearsal_json = _green_rehearsal(tmp_path / "rehearsal.json")
    payload = json.loads(rehearsal_json.read_text())
    payload.update(
        {
            "ready_for_rehearsal_import": False,
            "import_executed": False,
            "db_connection_attempted": False,
            "ready_for_cutover": True,
            "blockers": ["row count mismatch"],
        }
    )
    _write_json(rehearsal_json, payload)

    report = template.build_operator_evidence_template_report(
        rehearsal_json=rehearsal_json,
        backup_restore_owner="Ops Owner",
        rehearsal_window="2026-04-30T10:00:00Z/2026-04-30T12:00:00Z",
        rehearsal_executed_by="Platform Operator",
        rehearsal_result="pass",
        evidence_reviewer="Platform Reviewer",
        evidence_date="2026-04-30",
        output_md=tmp_path / "operator-evidence.md",
    )

    assert report["ready_for_operator_evidence_template"] is False
    assert "rehearsal report must have ready_for_rehearsal_import=true" in report["blockers"]
    assert "rehearsal report must have import_executed=true" in report["blockers"]
    assert "rehearsal report must have db_connection_attempted=true" in report["blockers"]
    assert "rehearsal report must have ready_for_cutover=false" in report["blockers"]
    assert "rehearsal report must have no blockers" in report["blockers"]


def test_rehearsal_result_must_be_pass(tmp_path):
    kwargs = _complete_kwargs(tmp_path)
    kwargs["rehearsal_result"] = "failed"

    report = template.build_operator_evidence_template_report(**kwargs)

    assert report["ready_for_operator_evidence_template"] is False
    assert "operator evidence template Rehearsal result must be pass" in report["blockers"]


def test_cli_writes_json_and_markdown(tmp_path):
    kwargs = _complete_kwargs(tmp_path)
    output_json = tmp_path / "template-report.json"
    output_md = tmp_path / "operator-evidence.md"

    exit_code = template.main(
        [
            "--rehearsal-json",
            str(kwargs["rehearsal_json"]),
            "--backup-restore-owner",
            kwargs["backup_restore_owner"],
            "--rehearsal-window",
            kwargs["rehearsal_window"],
            "--rehearsal-executed-by",
            kwargs["rehearsal_executed_by"],
            "--rehearsal-result",
            kwargs["rehearsal_result"],
            "--evidence-reviewer",
            kwargs["evidence_reviewer"],
            "--date",
            kwargs["evidence_date"],
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--strict",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text())
    assert payload["ready_for_operator_evidence_template"] is True
    markdown = output_md.read_text()
    assert "Rehearsal Evidence Sign-Off" in markdown
    assert "Ready for cutover: `false`" in markdown


def test_strict_cli_returns_one_when_incomplete(tmp_path):
    rehearsal_json = _green_rehearsal(tmp_path / "rehearsal.json")
    output_json = tmp_path / "template-report.json"
    output_md = tmp_path / "operator-evidence.md"

    exit_code = template.main(
        [
            "--rehearsal-json",
            str(rehearsal_json),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--strict",
        ]
    )

    assert exit_code == 1
    assert json.loads(output_json.read_text())["ready_for_operator_evidence_template"] is False


def test_source_preserves_template_only_scope():
    source = Path(template.__file__).read_text()

    assert "create_engine" not in source
    assert "TENANCY_MODE" not in source
    assert "ready_for_cutover\": False" in source
