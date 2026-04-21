from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "scripts").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_suite_fixture(root: Path) -> None:
    _write_json(root / "suite_validation.json", {"ok": True, "errors": []})
    _write_json(
        root / "01-dry-run-preflight" / "validation.json",
        {
            "ok": True,
            "errors": [],
            "job_count_before": 1,
            "job_count_after": 1,
            "would_enqueue_count": 2,
        },
    )
    _write_json(
        root / "01-dry-run-preflight" / "scheduler_dry_run.json",
        {
            "enqueued": [],
            "would_enqueue": [
                {"task_type": "eco_approval_escalation"},
                {"task_type": "audit_retention_prune"},
            ],
            "disabled": [],
            "skipped": [],
        },
    )
    _write_json(root / "02-audit-retention-activation" / "validation.json", {"ok": True, "errors": []})
    _write_json(
        root / "02-audit-retention-activation" / "scheduler_tick.json",
        {"enqueued": [{"job_id": "job-audit", "task_type": "audit_retention_prune"}]},
    )
    _write_json(
        root / "02-audit-retention-activation" / "post_worker_summary.json",
        {
            "audit_count_after": 1,
            "audit_paths_after": ["/scheduler-smoke/new-c"],
            "jobs": [
                {
                    "status": "completed",
                    "worker_id": "scheduler-audit-retention-smoke",
                    "payload_result": {"deleted": 2},
                }
            ],
        },
    )
    _write_json(root / "03-eco-escalation-activation" / "validation.json", {"ok": True, "errors": []})
    _write_json(
        root / "03-eco-escalation-activation" / "scheduler_tick.json",
        {"enqueued": [{"job_id": "job-eco", "task_type": "eco_approval_escalation"}]},
    )
    _write_json(
        root / "03-eco-escalation-activation" / "before_summary.json",
        {"pending_count": 1, "overdue_count": 2, "escalated_count": 0},
    )
    _write_json(
        root / "03-eco-escalation-activation" / "after_summary.json",
        {"pending_count": 1, "overdue_count": 3, "escalated_count": 1},
    )
    _write_json(
        root / "03-eco-escalation-activation" / "before_anomalies.json",
        {"overdue_not_escalated": [{}, {}], "escalated_unresolved": []},
    )
    _write_json(
        root / "03-eco-escalation-activation" / "after_anomalies.json",
        {"overdue_not_escalated": [{}], "escalated_unresolved": [{}]},
    )
    _write_json(
        root / "03-eco-escalation-activation" / "post_worker_summary.json",
        {
            "admin_escalation_approval_count": 1,
            "approval_request_count": 2,
            "jobs": [
                {
                    "status": "completed",
                    "worker_id": "scheduler-eco-escalation-smoke",
                    "payload_result": {"escalated": 1},
                }
            ]
        },
    )


def test_scheduler_local_activation_suite_renderer_contract(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "render_scheduler_local_activation_suite.py"

    assert script.is_file(), f"Missing script: {script}"

    help_run = subprocess.run(  # noqa: S603,S607
        [str(script), "--help"],
        text=True,
        capture_output=True,
    )
    assert help_run.returncode == 0, help_run.stdout + "\n" + help_run.stderr
    assert "SCHEDULER_LOCAL_ACTIVATION_SUITE_REPORT.md" in help_run.stdout

    suite_dir = tmp_path / "suite"
    _write_suite_fixture(suite_dir)
    render_run = subprocess.run(  # noqa: S603,S607
        [str(script), str(suite_dir)],
        text=True,
        capture_output=True,
    )
    assert render_run.returncode == 0, render_run.stdout + "\n" + render_run.stderr

    report_md = suite_dir / "SCHEDULER_LOCAL_ACTIVATION_SUITE_REPORT.md"
    report_json = suite_dir / "scheduler_local_activation_suite_report.json"
    assert report_md.is_file()
    assert report_json.is_file()

    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["audit_retention"]["deleted"] == 2
    assert payload["eco_escalation"]["escalated"] == 1
    assert payload["eco_escalation"]["admin_escalation_approval_count"] == 1
    assert payload["eco_escalation"]["approval_request_count"] == 2
    assert payload["eco_escalation"]["before_overdue_not_escalated"] == 2
    assert payload["eco_escalation"]["after_overdue_not_escalated"] == 1

    md = report_md.read_text(encoding="utf-8")
    for token in (
        "verdict: `PASS`",
        "Dry-run Preflight",
        "Audit Retention Activation",
        "ECO Escalation Activation",
        "overdue_not_escalated: `2 -> 1`",
        "It does not enable scheduler on shared-dev 142 or production.",
    ):
        assert token in md


def test_scheduler_local_activation_suite_report_doc_and_script_indexes() -> None:
    repo_root = _find_repo_root(Path(__file__))
    doc = (
        repo_root
        / "docs"
        / "DEV_AND_VERIFICATION_SCHEDULER_LOCAL_ACTIVATION_SUITE_REPORT_20260421.md"
    )
    delivery_doc_index = repo_root / "docs" / "DELIVERY_DOC_INDEX.md"
    delivery_scripts_index = repo_root / "docs" / "DELIVERY_SCRIPTS_INDEX_20260202.md"

    assert doc.is_file(), f"Missing doc: {doc}"
    assert doc.name in delivery_doc_index.read_text(encoding="utf-8")
    assert "render_scheduler_local_activation_suite.py" in delivery_scripts_index.read_text(encoding="utf-8")

    doc_text = doc.read_text(encoding="utf-8")
    for token in (
        "scripts/render_scheduler_local_activation_suite.py",
        "SCHEDULER_LOCAL_ACTIVATION_SUITE_REPORT.md",
        "scheduler_local_activation_suite_report.json",
        "shared-dev 142",
        "production",
    ):
        assert token in doc_text
