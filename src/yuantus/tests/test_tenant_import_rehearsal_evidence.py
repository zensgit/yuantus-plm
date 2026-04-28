from __future__ import annotations

import json
from pathlib import Path

from yuantus.scripts import tenant_import_rehearsal
from yuantus.scripts import tenant_import_rehearsal_evidence as evidence
from yuantus.scripts import tenant_import_rehearsal_handoff as handoff
from yuantus.scripts import tenant_import_rehearsal_implementation_packet as packet
from yuantus.scripts import tenant_import_rehearsal_next_action as next_action
from yuantus.scripts import tenant_import_rehearsal_plan as import_plan
from yuantus.scripts import tenant_import_rehearsal_readiness as readiness
from yuantus.scripts import tenant_import_rehearsal_source_preflight as source_preflight
from yuantus.scripts import tenant_import_rehearsal_target_preflight as target_preflight
from yuantus.scripts import tenant_migration_dry_run as dry_run


_TARGET_URL_REDACTED = "postgresql://user:***@example.com/rehearsal"
_TABLE_RESULTS = [
    {
        "table": "meta_items",
        "source_rows_expected": 2,
        "target_rows_inserted": 2,
        "row_count_matches": True,
    },
    {
        "table": "meta_files",
        "source_rows_expected": 3,
        "target_rows_inserted": 3,
        "row_count_matches": True,
    },
]


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _write_operator_evidence(path: Path, *, result: str = "pass") -> Path:
    path.write_text(
        f"""# Tenant Import Rehearsal Operator Evidence

## Rehearsal Evidence Sign-Off

```text
Pilot tenant: Acme Prod
Non-production rehearsal DB: {_TARGET_URL_REDACTED}
Backup/restore owner: Ops Owner
Rehearsal window: 2026-04-30T10:00:00Z/2026-04-30T12:00:00Z
Rehearsal executed by: Platform Operator
Rehearsal result: {result}
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
            "tenant_tables_in_import_order": ["meta_items", "meta_files"],
            "source_row_counts": {"meta_items": 2, "meta_files": 3},
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


def _write_green_artifacts(tmp_path: Path) -> dict[str, str]:
    paths: dict[str, str] = {}
    for key, payload in _artifact_payloads().items():
        paths[key] = str(_write_json(tmp_path / key, payload))
    return paths


def _write_green_packet(tmp_path: Path) -> Path:
    artifact_paths = _write_green_artifacts(tmp_path)
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
    report = packet.build_implementation_packet_report(
        next_action_json,
        output_md=tmp_path / "claude-task.md",
    )
    return _write_json(tmp_path / "implementation-packet.json", report)


def _write_green_rehearsal(tmp_path: Path) -> tuple[Path, Path]:
    packet_json = _write_green_packet(tmp_path)
    rehearsal_json = _write_json(
        tmp_path / "rehearsal.json",
        {
            "schema_version": tenant_import_rehearsal.SCHEMA_VERSION,
            "implementation_packet_json": str(packet_json),
            "implementation_packet_schema_version": packet.SCHEMA_VERSION,
            "ready_for_rehearsal_scaffold": True,
            "ready_for_import_execution": True,
            "ready_for_rehearsal_import": True,
            "import_executed": True,
            "db_connection_attempted": True,
            "ready_for_cutover": False,
            "tenant_id": "Acme Prod",
            "target_schema": "yt_t_acme_prod",
            "source_url": "sqlite:////tmp/source.db",
            "target_url": _TARGET_URL_REDACTED,
            "batch_size": 500,
            "next_action_json": str(tmp_path / "next-action.json"),
            "fresh_artifact_validations": [],
            "tables_planned": ["meta_items", "meta_files"],
            "table_results": _TABLE_RESULTS,
            "blockers": [],
        },
    )
    return packet_json, rehearsal_json


def _green_report(tmp_path: Path) -> dict:
    packet_json, rehearsal_json = _write_green_rehearsal(tmp_path)
    operator_md = _write_operator_evidence(tmp_path / "operator-evidence.md")
    return evidence.build_rehearsal_evidence_report(
        rehearsal_json=rehearsal_json,
        implementation_packet_json=packet_json,
        operator_evidence_md=operator_md,
    )


def test_green_rehearsal_evidence_passes_and_stays_not_cutover_ready(tmp_path):
    report = _green_report(tmp_path)

    assert report["schema_version"] == evidence.SCHEMA_VERSION
    assert report["ready_for_rehearsal_evidence"] is True
    assert report["operator_rehearsal_evidence_accepted"] is True
    assert report["ready_for_cutover"] is False
    assert report["blockers"] == []
    assert report["target_url"] == _TARGET_URL_REDACTED
    assert report["operator_sign_off"]["Non-production rehearsal DB"] == _TARGET_URL_REDACTED
    assert "secret" not in json.dumps(report)


def test_missing_operator_evidence_blocks(tmp_path):
    packet_json, rehearsal_json = _write_green_rehearsal(tmp_path)

    report = evidence.build_rehearsal_evidence_report(
        rehearsal_json=rehearsal_json,
        implementation_packet_json=packet_json,
        operator_evidence_md=tmp_path / "missing.md",
    )

    assert report["ready_for_rehearsal_evidence"] is False
    assert f"operator evidence {tmp_path / 'missing.md'} does not exist" in report["blockers"]


def test_operator_signoff_fields_are_required(tmp_path):
    packet_json, rehearsal_json = _write_green_rehearsal(tmp_path)
    operator_md = tmp_path / "operator-evidence.md"
    operator_md.write_text(
        """# Evidence

## Rehearsal Evidence Sign-Off

```text
Pilot tenant: TBD
Non-production rehearsal DB:
Backup/restore owner: Ops Owner
Rehearsal window: 2026-04-30T10:00:00Z/2026-04-30T12:00:00Z
Rehearsal executed by:
Rehearsal result: pending
Evidence reviewer:
Date:
```
"""
    )

    report = evidence.build_rehearsal_evidence_report(
        rehearsal_json=rehearsal_json,
        implementation_packet_json=packet_json,
        operator_evidence_md=operator_md,
    )

    assert report["ready_for_rehearsal_evidence"] is False
    assert "operator evidence missing Pilot tenant" in report["blockers"]
    assert "operator evidence missing Non-production rehearsal DB" in report["blockers"]
    assert "operator evidence missing Rehearsal executed by" in report["blockers"]
    assert "operator evidence Rehearsal result must be pass" in report["blockers"]


def test_operator_signoff_must_match_rehearsal_context(tmp_path):
    packet_json, rehearsal_json = _write_green_rehearsal(tmp_path)
    operator_md = tmp_path / "operator-evidence.md"
    operator_md.write_text(
        """# Evidence

## Rehearsal Evidence Sign-Off

```text
Pilot tenant: Other Tenant
Non-production rehearsal DB: postgresql://user:***@other.example.com/rehearsal
Backup/restore owner: Ops Owner
Rehearsal window: 2026-04-30T10:00:00Z/2026-04-30T12:00:00Z
Rehearsal executed by: Platform Operator
Rehearsal result: pass
Evidence reviewer: Platform Reviewer
Date: 2026-04-30
```
"""
    )

    report = evidence.build_rehearsal_evidence_report(
        rehearsal_json=rehearsal_json,
        implementation_packet_json=packet_json,
        operator_evidence_md=operator_md,
    )

    assert report["ready_for_rehearsal_evidence"] is False
    assert "operator evidence Pilot tenant must match rehearsal report" in report["blockers"]
    assert (
        "operator evidence Non-production rehearsal DB must match rehearsal target_url"
        in report["blockers"]
    )


def test_rehearsal_report_must_be_green(tmp_path):
    packet_json, rehearsal_json = _write_green_rehearsal(tmp_path)
    payload = json.loads(rehearsal_json.read_text())
    payload.update(
        {
            "ready_for_rehearsal_import": False,
            "import_executed": False,
            "db_connection_attempted": False,
            "ready_for_cutover": True,
            "blockers": ["copy failed"],
        }
    )
    _write_json(rehearsal_json, payload)
    operator_md = _write_operator_evidence(tmp_path / "operator-evidence.md")

    report = evidence.build_rehearsal_evidence_report(
        rehearsal_json=rehearsal_json,
        implementation_packet_json=packet_json,
        operator_evidence_md=operator_md,
    )

    assert report["ready_for_rehearsal_evidence"] is False
    assert "rehearsal report must have ready_for_rehearsal_import=true" in report["blockers"]
    assert "rehearsal report must have import_executed=true" in report["blockers"]
    assert "rehearsal report must have db_connection_attempted=true" in report["blockers"]
    assert "rehearsal report must have ready_for_cutover=false" in report["blockers"]
    assert "rehearsal report must have no blockers" in report["blockers"]


def test_table_results_must_match_and_exclude_global_tables(tmp_path):
    packet_json, rehearsal_json = _write_green_rehearsal(tmp_path)
    payload = json.loads(rehearsal_json.read_text())
    payload["table_results"] = [
        {
            "table": "auth_users",
            "source_rows_expected": 1,
            "target_rows_inserted": 2,
            "row_count_matches": False,
        }
    ]
    _write_json(rehearsal_json, payload)
    operator_md = _write_operator_evidence(tmp_path / "operator-evidence.md")

    report = evidence.build_rehearsal_evidence_report(
        rehearsal_json=rehearsal_json,
        implementation_packet_json=packet_json,
        operator_evidence_md=operator_md,
    )

    assert report["ready_for_rehearsal_evidence"] is False
    assert "table_results includes global/control-plane table auth_users" in report["blockers"]
    assert "auth_users row_count_matches must be true" in report["blockers"]
    assert "auth_users inserted 2 rows; expected 1" in report["blockers"]


def test_packet_must_match_rehearsal_context(tmp_path):
    packet_json, rehearsal_json = _write_green_rehearsal(tmp_path)
    packet_payload = json.loads(packet_json.read_text())
    packet_payload["target_schema"] = "yt_t_other"
    _write_json(packet_json, packet_payload)
    operator_md = _write_operator_evidence(tmp_path / "operator-evidence.md")

    report = evidence.build_rehearsal_evidence_report(
        rehearsal_json=rehearsal_json,
        implementation_packet_json=packet_json,
        operator_evidence_md=operator_md,
    )

    assert report["ready_for_rehearsal_evidence"] is False
    assert "implementation packet target_schema must match rehearsal report" in report["blockers"]


def test_stale_upstream_artifact_blocks(tmp_path):
    packet_json, rehearsal_json = _write_green_rehearsal(tmp_path)
    dry_run_path = tmp_path / "dry_run_json"
    payload = json.loads(dry_run_path.read_text())
    payload["ready_for_import"] = False
    payload["blockers"] = ["source drifted after rehearsal"]
    _write_json(dry_run_path, payload)
    operator_md = _write_operator_evidence(tmp_path / "operator-evidence.md")

    report = evidence.build_rehearsal_evidence_report(
        rehearsal_json=rehearsal_json,
        implementation_packet_json=packet_json,
        operator_evidence_md=operator_md,
    )

    assert report["ready_for_rehearsal_evidence"] is False
    assert "fresh dry-run artifact must have ready_for_import=true" in report["blockers"]
    assert "fresh dry-run artifact must have no blockers" in report["blockers"]


def test_cli_writes_json_and_markdown(tmp_path):
    packet_json, rehearsal_json = _write_green_rehearsal(tmp_path)
    operator_md = _write_operator_evidence(tmp_path / "operator-evidence.md")
    output_json = tmp_path / "evidence-report.json"
    output_md = tmp_path / "evidence-report.md"

    exit_code = evidence.main(
        [
            "--rehearsal-json",
            str(rehearsal_json),
            "--implementation-packet-json",
            str(packet_json),
            "--operator-evidence-md",
            str(operator_md),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--strict",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text())
    assert payload["ready_for_rehearsal_evidence"] is True
    markdown = output_md.read_text()
    assert "Tenant Import Rehearsal Evidence Report" in markdown
    assert "Ready for cutover: `false`" in markdown


def test_strict_cli_returns_one_when_blocked(tmp_path):
    packet_json, rehearsal_json = _write_green_rehearsal(tmp_path)
    output_json = tmp_path / "evidence-report.json"
    output_md = tmp_path / "evidence-report.md"

    exit_code = evidence.main(
        [
            "--rehearsal-json",
            str(rehearsal_json),
            "--implementation-packet-json",
            str(packet_json),
            "--operator-evidence-md",
            str(tmp_path / "missing.md"),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--strict",
        ]
    )

    assert exit_code == 1
    assert json.loads(output_json.read_text())["ready_for_rehearsal_evidence"] is False


def test_source_preserves_offline_scope():
    source = Path(evidence.__file__).read_text()

    assert "create_engine" not in source
    assert "TENANCY_MODE" not in source
    assert "ready_for_cutover\": False" in source
