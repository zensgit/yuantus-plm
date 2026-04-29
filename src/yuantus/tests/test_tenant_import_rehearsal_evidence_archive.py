from __future__ import annotations

import json
from pathlib import Path

from yuantus.scripts import tenant_import_rehearsal
from yuantus.scripts import tenant_import_rehearsal_evidence as evidence
from yuantus.scripts import tenant_import_rehearsal_evidence_archive as archive
from yuantus.scripts import tenant_import_rehearsal_evidence_template as template
from yuantus.scripts import tenant_import_rehearsal_handoff as handoff
from yuantus.scripts import tenant_import_rehearsal_implementation_packet as packet
from yuantus.scripts import tenant_import_rehearsal_next_action as next_action
from yuantus.scripts import tenant_import_rehearsal_plan as import_plan
from yuantus.scripts import tenant_import_rehearsal_readiness as readiness
from yuantus.scripts import tenant_import_rehearsal_source_preflight as source_preflight
from yuantus.scripts import tenant_import_rehearsal_target_preflight as target_preflight
from yuantus.scripts import tenant_migration_dry_run as dry_run


_TARGET_URL_REDACTED = "postgresql://user:***@example.com/rehearsal"


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _write_operator_evidence(path: Path) -> Path:
    path.write_text(
        f"""# Tenant Import Rehearsal Operator Evidence

## Rehearsal Evidence Sign-Off

```text
Pilot tenant: Acme Prod
Non-production rehearsal DB: {_TARGET_URL_REDACTED}
Backup/restore owner: Ops Owner
Rehearsal window: 2026-04-30T10:00:00Z/2026-04-30T12:00:00Z
Rehearsal executed by: Platform Operator
Rehearsal result: pass
Evidence reviewer: Platform Reviewer
Date: 2026-04-30
```
"""
    )
    return path


def _artifact_payloads() -> dict[str, dict]:
    return {
        "dry_run_json": {
            "schema_version": dry_run.SCHEMA_VERSION,
            "tenant_id": "Acme Prod",
            "target_schema": "yt_t_acme_prod",
            "ready_for_import": True,
            "blockers": [],
        },
        "readiness_json": {
            "schema_version": readiness.SCHEMA_VERSION,
            "tenant_id": "Acme Prod",
            "target_schema": "yt_t_acme_prod",
            "target_url": _TARGET_URL_REDACTED,
            "ready_for_rehearsal": True,
            "blockers": [],
        },
        "handoff_json": {
            "schema_version": handoff.SCHEMA_VERSION,
            "tenant_id": "Acme Prod",
            "target_schema": "yt_t_acme_prod",
            "target_url": _TARGET_URL_REDACTED,
            "ready_for_claude": True,
            "blockers": [],
        },
        "plan_json": {
            "schema_version": import_plan.SCHEMA_VERSION,
            "tenant_id": "Acme Prod",
            "target_schema": "yt_t_acme_prod",
            "source_url": "sqlite:////tmp/source.db",
            "target_url": _TARGET_URL_REDACTED,
            "baseline_revision": dry_run.BASELINE_REVISION,
            "tenant_tables_in_import_order": ["meta_items"],
            "source_row_counts": {"meta_items": 2},
            "ready_for_importer": True,
            "ready_for_cutover": False,
            "blockers": [],
        },
        "source_preflight_json": {
            "schema_version": source_preflight.SCHEMA_VERSION,
            "tenant_id": "Acme Prod",
            "target_schema": "yt_t_acme_prod",
            "ready_for_importer_source": True,
            "ready_for_cutover": False,
            "blockers": [],
        },
        "target_preflight_json": {
            "schema_version": target_preflight.SCHEMA_VERSION,
            "tenant_id": "Acme Prod",
            "target_schema": "yt_t_acme_prod",
            "target_url": _TARGET_URL_REDACTED,
            "ready_for_importer_target": True,
            "ready_for_cutover": False,
            "blockers": [],
        },
    }


def _write_green_chain(tmp_path: Path) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    artifact_paths: dict[str, str] = {}
    for key, payload in _artifact_payloads().items():
        path = _write_json(tmp_path / key, payload)
        paths[key] = path
        artifact_paths[key] = str(path)

    next_action_json = _write_json(
        tmp_path / "next-action.json",
        {
            "schema_version": next_action.SCHEMA_VERSION,
            "next_action": packet.FINAL_NEXT_ACTION,
            "claude_required": True,
            "context": {
                "tenant_id": "Acme Prod",
                "target_schema": "yt_t_acme_prod",
                "target_url": _TARGET_URL_REDACTED,
                **artifact_paths,
            },
            "inputs": {},
            "blockers": [],
        },
    )
    paths["next_action_json"] = next_action_json
    packet_report = packet.build_implementation_packet_report(
        next_action_json,
        output_md=tmp_path / "claude-task.md",
    )
    implementation_packet_json = _write_json(
        tmp_path / "implementation-packet.json",
        packet_report,
    )
    paths["implementation_packet_json"] = implementation_packet_json

    rehearsal_json = _write_json(
        tmp_path / "rehearsal.json",
        {
            "schema_version": tenant_import_rehearsal.SCHEMA_VERSION,
            "implementation_packet_json": str(implementation_packet_json),
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
    paths["rehearsal_json"] = rehearsal_json

    operator_evidence_md = _write_operator_evidence(tmp_path / "operator-evidence.md")
    paths["operator_evidence_md"] = operator_evidence_md
    evidence_report = evidence.build_rehearsal_evidence_report(
        rehearsal_json=rehearsal_json,
        implementation_packet_json=implementation_packet_json,
        operator_evidence_md=operator_evidence_md,
    )
    evidence_json = _write_json(tmp_path / "evidence.json", evidence_report)
    paths["evidence_json"] = evidence_json

    template_report = template.build_operator_evidence_template_report(
        rehearsal_json=rehearsal_json,
        backup_restore_owner="Ops Owner",
        rehearsal_window="2026-04-30T10:00:00Z/2026-04-30T12:00:00Z",
        rehearsal_executed_by="Platform Operator",
        rehearsal_result="pass",
        evidence_reviewer="Platform Reviewer",
        evidence_date="2026-04-30",
        output_md=operator_evidence_md,
    )
    template_json = _write_json(tmp_path / "template.json", template_report)
    paths["operator_evidence_template_json"] = template_json
    return paths


def test_green_chain_builds_archive_manifest_with_hashes(tmp_path):
    paths = _write_green_chain(tmp_path)

    report = archive.build_rehearsal_evidence_archive_report(
        evidence_json=paths["evidence_json"],
        operator_evidence_template_json=paths["operator_evidence_template_json"],
    )

    assert report["schema_version"] == archive.SCHEMA_VERSION
    assert report["ready_for_archive"] is True
    assert report["ready_for_cutover"] is False
    assert report["blockers"] == []
    assert report["artifact_count"] == 12
    assert {item["artifact"] for item in report["artifacts"]} >= {
        "evidence_json",
        "rehearsal_json",
        "implementation_packet_json",
        "operator_evidence_md",
        "operator_evidence_template_json",
    }
    for item in report["artifacts"]:
        assert item["exists"] is True
        assert item["bytes"] > 0
        assert len(item["sha256"]) == 64


def test_archive_can_omit_template_json_when_operator_handwrites_evidence(tmp_path):
    paths = _write_green_chain(tmp_path)

    report = archive.build_rehearsal_evidence_archive_report(
        evidence_json=paths["evidence_json"],
    )

    assert report["ready_for_archive"] is True
    assert report["artifact_count"] == 11
    assert "operator_evidence_template_json" not in {
        item["artifact"] for item in report["artifacts"]
    }


def test_blocked_evidence_report_blocks_archive(tmp_path):
    paths = _write_green_chain(tmp_path)
    payload = json.loads(paths["evidence_json"].read_text())
    payload["ready_for_rehearsal_evidence"] = False
    payload["operator_rehearsal_evidence_accepted"] = False
    payload["ready_for_cutover"] = True
    payload["blockers"] = ["operator evidence missing Date"]
    _write_json(paths["evidence_json"], payload)

    report = archive.build_rehearsal_evidence_archive_report(
        evidence_json=paths["evidence_json"],
        operator_evidence_template_json=paths["operator_evidence_template_json"],
    )

    assert report["ready_for_archive"] is False
    assert "evidence report must have ready_for_rehearsal_evidence=true" in report["blockers"]
    assert "evidence report must have operator_rehearsal_evidence_accepted=true" in report["blockers"]
    assert "evidence report must have ready_for_cutover=false" in report["blockers"]
    assert "evidence report must have no blockers" in report["blockers"]


def test_missing_artifact_blocks_archive(tmp_path):
    paths = _write_green_chain(tmp_path)
    paths["target_preflight_json"].unlink()

    report = archive.build_rehearsal_evidence_archive_report(
        evidence_json=paths["evidence_json"],
        operator_evidence_template_json=paths["operator_evidence_template_json"],
    )

    assert report["ready_for_archive"] is False
    assert any("target_preflight_json" in blocker for blocker in report["blockers"])


def test_artifact_schema_and_ready_fields_are_checked(tmp_path):
    paths = _write_green_chain(tmp_path)
    payload = json.loads(paths["plan_json"].read_text())
    payload["schema_version"] = "wrong"
    payload["ready_for_importer"] = False
    payload["ready_for_cutover"] = True
    payload["blockers"] = ["not ready"]
    _write_json(paths["plan_json"], payload)

    report = archive.build_rehearsal_evidence_archive_report(
        evidence_json=paths["evidence_json"],
        operator_evidence_template_json=paths["operator_evidence_template_json"],
    )

    assert report["ready_for_archive"] is False
    assert f"plan_json schema_version must be {import_plan.SCHEMA_VERSION}" in report["blockers"]
    assert "plan_json must have ready_for_importer=true" in report["blockers"]
    assert "plan_json must have no blockers" in report["blockers"]
    assert "plan_json must have ready_for_cutover=false" in report["blockers"]


def test_template_output_md_must_match_operator_evidence_md(tmp_path):
    paths = _write_green_chain(tmp_path)
    payload = json.loads(paths["operator_evidence_template_json"].read_text())
    payload["output_md"] = str(tmp_path / "other-evidence.md")
    _write_json(paths["operator_evidence_template_json"], payload)

    report = archive.build_rehearsal_evidence_archive_report(
        evidence_json=paths["evidence_json"],
        operator_evidence_template_json=paths["operator_evidence_template_json"],
    )

    assert report["ready_for_archive"] is False
    assert (
        "operator_evidence_template_json output_md must match operator_evidence_md"
        in report["blockers"]
    )


def test_cli_writes_json_and_markdown(tmp_path):
    paths = _write_green_chain(tmp_path)
    output_json = tmp_path / "archive.json"
    output_md = tmp_path / "archive.md"

    exit_code = archive.main(
        [
            "--evidence-json",
            str(paths["evidence_json"]),
            "--operator-evidence-template-json",
            str(paths["operator_evidence_template_json"]),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--strict",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text())
    assert payload["ready_for_archive"] is True
    markdown = output_md.read_text()
    assert "Tenant Import Rehearsal Evidence Archive Manifest" in markdown
    assert "Ready for cutover: `false`" in markdown


def test_strict_cli_returns_one_when_blocked(tmp_path):
    paths = _write_green_chain(tmp_path)
    paths["operator_evidence_md"].unlink()
    output_json = tmp_path / "archive.json"
    output_md = tmp_path / "archive.md"

    exit_code = archive.main(
        [
            "--evidence-json",
            str(paths["evidence_json"]),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--strict",
        ]
    )

    assert exit_code == 1
    assert json.loads(output_json.read_text())["ready_for_archive"] is False


def test_source_preserves_archive_only_scope():
    source = Path(archive.__file__).read_text()

    assert "create_engine" not in source
    assert "TENANCY_MODE" not in source
    assert "ready_for_cutover\": False" in source
