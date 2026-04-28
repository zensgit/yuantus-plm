from __future__ import annotations

import json
from pathlib import Path

from yuantus.scripts import tenant_import_rehearsal_handoff as handoff
from yuantus.scripts import tenant_import_rehearsal_readiness as readiness
from yuantus.scripts import tenant_migration_dry_run as dry_run


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _ready_report() -> dict:
    return {
        "schema_version": readiness.SCHEMA_VERSION,
        "tenant_id": "Acme Prod",
        "target_schema": "yt_t_acme_prod",
        "target_url": "postgresql://user:***@example.com/rehearsal",
        "dry_run_schema_version": dry_run.SCHEMA_VERSION,
        "ready_for_import": True,
        "ready_for_rehearsal": True,
        "checks": {
            "backup_restore_owner": "Ops Owner",
            "rehearsal_window": "2026-04-30T10:00:00Z/2026-04-30T12:00:00Z",
            "classification_artifact": "docs/TENANT_TABLE_CLASSIFICATION_20260427.md",
            "classification_signed_off": True,
            "dry_run_json": "output/tenant_acme_dry_run.json",
            "dry_run_blocker_count": 0,
            "baseline_revision": dry_run.BASELINE_REVISION,
        },
        "blockers": [],
    }


def test_ready_readiness_report_generates_claude_handoff(tmp_path):
    readiness_json = _write_json(tmp_path / "readiness.json", _ready_report())

    report = handoff.build_handoff_report(
        readiness_json, tmp_path / "claude-task.md"
    )

    assert report["schema_version"] == handoff.SCHEMA_VERSION
    assert report["ready_for_claude"] is True
    assert report["blockers"] == []
    assert report["tenant_id"] == "Acme Prod"
    assert report["target_url"] == "postgresql://user:***@example.com/rehearsal"


def test_not_ready_readiness_report_blocks_claude(tmp_path):
    payload = _ready_report()
    payload.update(
        {
            "ready_for_rehearsal": False,
            "blockers": ["classification sign-off missing Reviewer"],
        }
    )
    readiness_json = _write_json(tmp_path / "readiness.json", payload)

    report = handoff.build_handoff_report(
        readiness_json, tmp_path / "claude-task.md"
    )

    assert report["ready_for_claude"] is False
    assert "readiness report must have ready_for_rehearsal=true" in report["blockers"]
    assert "readiness report must have no blockers" in report["blockers"]


def test_schema_mismatch_blocks_claude(tmp_path):
    payload = _ready_report()
    payload["schema_version"] = "unexpected"
    payload["dry_run_schema_version"] = "unexpected"
    readiness_json = _write_json(tmp_path / "readiness.json", payload)

    report = handoff.build_handoff_report(
        readiness_json, tmp_path / "claude-task.md"
    )

    assert report["ready_for_claude"] is False
    assert (
        f"readiness schema_version must be {readiness.SCHEMA_VERSION}"
        in report["blockers"]
    )
    assert (
        f"dry_run_schema_version must be {dry_run.SCHEMA_VERSION}"
        in report["blockers"]
    )


def test_cli_writes_json_and_markdown_without_plaintext_secret(tmp_path):
    payload = _ready_report()
    readiness_json = _write_json(tmp_path / "readiness.json", payload)
    output_json = tmp_path / "handoff.json"
    output_md = tmp_path / "claude-task.md"

    result = handoff.main(
        [
            "--readiness-json",
            str(readiness_json),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--strict",
        ]
    )

    assert result == 0
    report = json.loads(output_json.read_text())
    markdown = output_md.read_text()
    assert report["ready_for_claude"] is True
    assert "Claude can start: `true`" in markdown
    assert "tenant_import_rehearsal" in markdown
    assert "secret" not in json.dumps(report)
    assert "secret" not in markdown


def test_cli_strict_exits_one_when_blocked(tmp_path):
    payload = _ready_report()
    payload["ready_for_import"] = False
    readiness_json = _write_json(tmp_path / "readiness.json", payload)

    result = handoff.main(
        [
            "--readiness-json",
            str(readiness_json),
            "--output-json",
            str(tmp_path / "handoff.json"),
            "--output-md",
            str(tmp_path / "claude-task.md"),
            "--strict",
        ]
    )

    assert result == 1


def test_handoff_source_does_not_connect_or_mutate_databases():
    source = Path(handoff.__file__).read_text()
    upper_source = source.upper()

    assert "CREATE_ENGINE" not in upper_source
    assert "CONNECT(" not in upper_source
    assert "CREATE SCHEMA" not in upper_source
    assert "DROP SCHEMA" not in upper_source
    assert "os.environ" not in source
    assert "settings.tenancy_mode" not in source
