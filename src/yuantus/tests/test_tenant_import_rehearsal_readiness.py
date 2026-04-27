from __future__ import annotations

import json
from pathlib import Path

from yuantus.scripts import tenant_import_rehearsal_readiness as readiness
from yuantus.scripts import tenant_migration_dry_run as dry_run


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _ready_dry_run() -> dict:
    return {
        "schema_version": dry_run.SCHEMA_VERSION,
        "tenant_id": "Acme Prod",
        "target_schema": "yt_t_acme_prod",
        "source_url": "sqlite:////tmp/source.db",
        "baseline_revision": dry_run.BASELINE_REVISION,
        "ready_for_import": True,
        "blockers": [],
    }


def _artifact(tmp_path: Path) -> Path:
    path = tmp_path / "TENANT_TABLE_CLASSIFICATION_20260427.md"
    path.write_text("# signed off\n")
    return path


def _ready_kwargs(tmp_path: Path) -> dict:
    return {
        "dry_run_json": _write_json(tmp_path / "dry-run.json", _ready_dry_run()),
        "tenant_id": "Acme Prod",
        "target_url": "postgresql://user:secret@example.com/rehearsal",
        "target_schema": "yt_t_acme_prod",
        "backup_restore_owner": "Ops Owner",
        "rehearsal_window": "2026-04-30T10:00:00Z/2026-04-30T12:00:00Z",
        "classification_artifact": _artifact(tmp_path),
        "classification_signed_off": True,
    }


def test_ready_inputs_pass_and_redact_target_url(tmp_path):
    report = readiness.build_readiness_report(**_ready_kwargs(tmp_path))

    assert report["schema_version"] == readiness.SCHEMA_VERSION
    assert report["ready_for_rehearsal"] is True
    assert report["blockers"] == []
    assert report["target_url"] == "postgresql://user:***@example.com/rehearsal"
    assert "secret" not in json.dumps(report)


def test_missing_external_inputs_block(tmp_path):
    kwargs = _ready_kwargs(tmp_path)
    kwargs.update(
        {
            "backup_restore_owner": "",
            "classification_signed_off": False,
            "target_url": "sqlite:///not-postgres.db",
            "classification_artifact": tmp_path / "missing.md",
        }
    )
    report = readiness.build_readiness_report(**kwargs)

    assert report["ready_for_rehearsal"] is False
    assert "missing backup/restore owner" in report["blockers"]
    assert "classification artifact must be signed off" in report["blockers"]
    assert "classification artifact is missing" in report["blockers"]
    assert "target_url must be a PostgreSQL URL" in report["blockers"]


def test_dry_run_mismatch_or_not_ready_blocks(tmp_path):
    dry_run_report = _ready_dry_run()
    dry_run_report.update(
        {
            "tenant_id": "Other Tenant",
            "target_schema": "yt_t_other",
            "ready_for_import": False,
            "blockers": ["Unknown source tables: stray_table"],
        }
    )
    kwargs = _ready_kwargs(tmp_path)
    kwargs["dry_run_json"] = _write_json(tmp_path / "dry-run.json", dry_run_report)

    report = readiness.build_readiness_report(**kwargs)

    assert report["ready_for_rehearsal"] is False
    assert "dry-run report must have ready_for_import=true" in report["blockers"]
    assert "dry-run report must have no blockers" in report["blockers"]
    assert "tenant_id must match dry-run tenant_id" in report["blockers"]
    assert "target_schema must match dry-run target_schema" in report["blockers"]


def test_cli_writes_json_and_markdown(tmp_path):
    kwargs = _ready_kwargs(tmp_path)
    output_json = tmp_path / "readiness.json"
    output_md = tmp_path / "readiness.md"

    result = readiness.main(
        [
            "--dry-run-json",
            str(kwargs["dry_run_json"]),
            "--tenant-id",
            kwargs["tenant_id"],
            "--target-url",
            kwargs["target_url"],
            "--target-schema",
            kwargs["target_schema"],
            "--backup-restore-owner",
            kwargs["backup_restore_owner"],
            "--rehearsal-window",
            kwargs["rehearsal_window"],
            "--classification-artifact",
            str(kwargs["classification_artifact"]),
            "--classification-signed-off",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ]
    )

    assert result == 0
    payload = json.loads(output_json.read_text())
    assert payload["schema_version"] == readiness.SCHEMA_VERSION
    assert payload["ready_for_rehearsal"] is True
    markdown = output_md.read_text()
    assert "# Tenant Import Rehearsal Readiness Report" in markdown
    assert "postgresql://user:***@example.com/rehearsal" in markdown


def test_cli_strict_exits_nonzero_when_blocked(tmp_path):
    kwargs = _ready_kwargs(tmp_path)

    result = readiness.main(
        [
            "--dry-run-json",
            str(kwargs["dry_run_json"]),
            "--tenant-id",
            kwargs["tenant_id"],
            "--target-url",
            kwargs["target_url"],
            "--target-schema",
            kwargs["target_schema"],
            "--backup-restore-owner",
            kwargs["backup_restore_owner"],
            "--rehearsal-window",
            kwargs["rehearsal_window"],
            "--classification-artifact",
            str(kwargs["classification_artifact"]),
            "--output-json",
            str(tmp_path / "readiness.json"),
            "--output-md",
            str(tmp_path / "readiness.md"),
            "--strict",
        ]
    )

    assert result == 1


def test_cli_invalid_json_exits_two(tmp_path):
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{")

    result = readiness.main(
        [
            "--dry-run-json",
            str(bad_json),
            "--tenant-id",
            "Acme Prod",
            "--target-url",
            "postgresql://user:secret@example.com/rehearsal",
            "--target-schema",
            "yt_t_acme_prod",
            "--backup-restore-owner",
            "Ops Owner",
            "--rehearsal-window",
            "2026-04-30T10:00:00Z/2026-04-30T12:00:00Z",
            "--classification-artifact",
            str(_artifact(tmp_path)),
            "--classification-signed-off",
            "--output-json",
            str(tmp_path / "readiness.json"),
            "--output-md",
            str(tmp_path / "readiness.md"),
        ]
    )

    assert result == 2


def test_readiness_source_does_not_connect_or_mutate_databases():
    source = Path(readiness.__file__).read_text()
    upper_source = source.upper()

    assert "CREATE_ENGINE" not in upper_source
    assert "CONNECT(" not in upper_source
    assert "CREATE SCHEMA" not in upper_source
    assert "DROP SCHEMA" not in upper_source
    assert "TENANCY_MODE" not in source
