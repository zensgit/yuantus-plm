from __future__ import annotations

import json
from pathlib import Path

from yuantus.scripts import tenant_import_rehearsal_handoff as handoff
from yuantus.scripts import tenant_import_rehearsal_next_action as next_action
from yuantus.scripts import tenant_import_rehearsal_readiness as readiness
from yuantus.scripts import tenant_migration_dry_run as dry_run


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _dry_run_ready() -> dict:
    return {
        "schema_version": dry_run.SCHEMA_VERSION,
        "tenant_id": "Acme Prod",
        "target_schema": "yt_t_acme_prod",
        "ready_for_import": True,
        "blockers": [],
    }


def _readiness_ready() -> dict:
    return {
        "schema_version": readiness.SCHEMA_VERSION,
        "tenant_id": "Acme Prod",
        "target_schema": "yt_t_acme_prod",
        "target_url": "postgresql://user:***@example.com/rehearsal",
        "dry_run_schema_version": dry_run.SCHEMA_VERSION,
        "ready_for_import": True,
        "ready_for_rehearsal": True,
        "checks": {
            "dry_run_json": "output/tenant_acme_dry_run.json",
        },
        "blockers": [],
    }


def _handoff_ready() -> dict:
    return {
        "schema_version": handoff.SCHEMA_VERSION,
        "tenant_id": "Acme Prod",
        "target_schema": "yt_t_acme_prod",
        "target_url": "postgresql://user:***@example.com/rehearsal",
        "readiness_json": "output/tenant_acme_readiness.json",
        "dry_run_json": "output/tenant_acme_dry_run.json",
        "handoff_json": "output/tenant_acme_handoff.json",
        "ready_for_claude": True,
        "blockers": [],
    }


def test_missing_dry_run_points_to_dry_run(tmp_path):
    report = next_action.build_next_action_report()

    assert report["claude_required"] is False
    assert report["next_action"] == "run_p3_4_1_dry_run"
    assert "missing P3.4.1 dry-run report" in report["blockers"]


def test_dry_run_not_ready_points_to_dry_run_blockers(tmp_path):
    payload = _dry_run_ready()
    payload.update({"ready_for_import": False, "blockers": ["Unknown source tables"]})
    dry_run_json = _write_json(tmp_path / "dry-run.json", payload)

    report = next_action.build_next_action_report(dry_run_json=dry_run_json)

    assert report["claude_required"] is False
    assert report["next_action"] == "fix_dry_run_blockers"
    assert "Unknown source tables" in report["blockers"]


def test_ready_dry_run_without_readiness_points_to_stop_gate(tmp_path):
    dry_run_json = _write_json(tmp_path / "dry-run.json", _dry_run_ready())

    report = next_action.build_next_action_report(dry_run_json=dry_run_json)

    assert report["claude_required"] is False
    assert report["next_action"] == "collect_stop_gate_inputs_and_run_readiness"


def test_ready_readiness_without_handoff_points_to_handoff(tmp_path):
    dry_run_json = _write_json(tmp_path / "dry-run.json", _dry_run_ready())
    readiness_json = _write_json(tmp_path / "readiness.json", _readiness_ready())

    report = next_action.build_next_action_report(
        dry_run_json=dry_run_json,
        readiness_json=readiness_json,
    )

    assert report["claude_required"] is False
    assert report["next_action"] == "run_claude_handoff"


def test_ready_handoff_requires_claude(tmp_path):
    dry_run_json = _write_json(tmp_path / "dry-run.json", _dry_run_ready())
    readiness_json = _write_json(tmp_path / "readiness.json", _readiness_ready())
    handoff_json = _write_json(tmp_path / "handoff.json", _handoff_ready())

    report = next_action.build_next_action_report(
        dry_run_json=dry_run_json,
        readiness_json=readiness_json,
        handoff_json=handoff_json,
    )

    assert report["claude_required"] is True
    assert report["next_action"] == "ask_claude_to_implement_importer"
    assert report["blockers"] == []


def test_cli_writes_next_action_reports(tmp_path):
    dry_run_json = _write_json(tmp_path / "dry-run.json", _dry_run_ready())
    output_json = tmp_path / "next-action.json"
    output_md = tmp_path / "next-action.md"

    result = next_action.main(
        [
            "--dry-run-json",
            str(dry_run_json),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ]
    )

    assert result == 0
    payload = json.loads(output_json.read_text())
    markdown = output_md.read_text()
    assert payload["next_action"] == "collect_stop_gate_inputs_and_run_readiness"
    assert "Claude required: `false`" in markdown


def test_cli_strict_exits_one_until_claude_is_required(tmp_path):
    dry_run_json = _write_json(tmp_path / "dry-run.json", _dry_run_ready())

    result = next_action.main(
        [
            "--dry-run-json",
            str(dry_run_json),
            "--output-json",
            str(tmp_path / "next-action.json"),
            "--output-md",
            str(tmp_path / "next-action.md"),
            "--strict",
        ]
    )

    assert result == 1


def test_cli_strict_exits_zero_when_claude_is_required(tmp_path):
    dry_run_json = _write_json(tmp_path / "dry-run.json", _dry_run_ready())
    readiness_json = _write_json(tmp_path / "readiness.json", _readiness_ready())
    handoff_json = _write_json(tmp_path / "handoff.json", _handoff_ready())

    result = next_action.main(
        [
            "--dry-run-json",
            str(dry_run_json),
            "--readiness-json",
            str(readiness_json),
            "--handoff-json",
            str(handoff_json),
            "--output-json",
            str(tmp_path / "next-action.json"),
            "--output-md",
            str(tmp_path / "next-action.md"),
            "--strict",
        ]
    )

    assert result == 0


def test_next_action_source_does_not_connect_or_mutate_databases():
    source = Path(next_action.__file__).read_text()
    upper_source = source.upper()

    assert "CREATE_ENGINE" not in upper_source
    assert "CONNECT(" not in upper_source
    assert "CREATE SCHEMA" not in upper_source
    assert "DROP SCHEMA" not in upper_source
    assert "os.environ" not in source
