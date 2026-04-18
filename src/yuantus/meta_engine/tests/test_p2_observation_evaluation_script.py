from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


def _write_result_dir(
    target: Path,
    *,
    summary: dict,
    items: list[dict],
    anomalies: dict,
) -> Path:
    target.mkdir(parents=True, exist_ok=True)
    export_columns = [
        "eco_id",
        "eco_name",
        "eco_state",
        "stage_id",
        "stage_name",
        "approval_id",
        "assignee_id",
        "assignee_username",
        "approval_type",
        "required_role",
        "is_overdue",
        "is_escalated",
        "approval_deadline",
        "hours_overdue",
    ]

    (target / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (target / "items.json").write_text(json.dumps(items), encoding="utf-8")
    (target / "export.json").write_text(json.dumps(items), encoding="utf-8")
    (target / "anomalies.json").write_text(json.dumps(anomalies), encoding="utf-8")

    with (target / "export.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=export_columns)
        writer.writeheader()
        for item in items:
            writer.writerow({column: item.get(column) for column in export_columns})

    return target


def _run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(script), *args],
        text=True,
        capture_output=True,
        cwd=script.parents[2],
    )


def test_p2_observation_evaluator_current_only_passes(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script = repo_root / "scripts" / "evaluate_p2_observation_results.py"
    current = _write_result_dir(
        tmp_path / "current",
        summary={"pending_count": 1, "overdue_count": 2, "escalated_count": 0},
        items=[
            {"eco_id": "a", "is_overdue": True, "is_escalated": False},
            {"eco_id": "b", "is_overdue": True, "is_escalated": False},
            {"eco_id": "c", "is_overdue": False, "is_escalated": False},
        ],
        anomalies={
            "no_candidates": [],
            "escalated_unresolved": [],
            "overdue_not_escalated": [{"eco_id": "a"}, {"eco_id": "b"}],
            "total_anomalies": 2,
        },
    )

    cp = _run(script, str(current), "--mode", "current-only")

    assert cp.returncode == 0, cp.stderr
    report = current / "OBSERVATION_EVAL.md"
    assert report.is_file(), "expected evaluation report to be created"
    text = report.read_text(encoding="utf-8")
    assert "- verdict: PASS" in text
    assert "summary matches items for pending_count" in text


def test_p2_observation_evaluator_readonly_passes_on_stable_metrics(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script = repo_root / "scripts" / "evaluate_p2_observation_results.py"

    baseline = _write_result_dir(
        tmp_path / "baseline",
        summary={"pending_count": 1, "overdue_count": 2, "escalated_count": 0},
        items=[
            {"eco_id": "a", "is_overdue": True, "is_escalated": False},
            {"eco_id": "b", "is_overdue": True, "is_escalated": False},
            {"eco_id": "c", "is_overdue": False, "is_escalated": False},
        ],
        anomalies={
            "no_candidates": [],
            "escalated_unresolved": [],
            "overdue_not_escalated": [{"eco_id": "a"}, {"eco_id": "b"}],
            "total_anomalies": 2,
        },
    )
    current = _write_result_dir(
        tmp_path / "current",
        summary={"pending_count": 1, "overdue_count": 2, "escalated_count": 0},
        items=[
            {"eco_id": "a", "is_overdue": True, "is_escalated": False},
            {"eco_id": "b", "is_overdue": True, "is_escalated": False},
            {"eco_id": "c", "is_overdue": False, "is_escalated": False},
        ],
        anomalies={
            "no_candidates": [],
            "escalated_unresolved": [],
            "overdue_not_escalated": [{"eco_id": "a"}, {"eco_id": "b"}],
            "total_anomalies": 2,
        },
    )

    cp = _run(
        script,
        str(current),
        "--mode",
        "readonly",
        "--baseline-dir",
        str(baseline),
    )

    assert cp.returncode == 0, cp.stderr
    assert "- verdict: PASS" in (current / "OBSERVATION_EVAL.md").read_text(encoding="utf-8")


def test_p2_observation_evaluator_state_change_passes_with_expected_deltas(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script = repo_root / "scripts" / "evaluate_p2_observation_results.py"

    baseline = _write_result_dir(
        tmp_path / "baseline",
        summary={"pending_count": 1, "overdue_count": 2, "escalated_count": 0},
        items=[
            {"eco_id": "a", "is_overdue": True, "is_escalated": False},
            {"eco_id": "b", "is_overdue": True, "is_escalated": False},
            {"eco_id": "c", "is_overdue": False, "is_escalated": False},
        ],
        anomalies={
            "no_candidates": [],
            "escalated_unresolved": [],
            "overdue_not_escalated": [{"eco_id": "a"}, {"eco_id": "b"}],
            "total_anomalies": 2,
        },
    )
    current = _write_result_dir(
        tmp_path / "current",
        summary={"pending_count": 1, "overdue_count": 3, "escalated_count": 1},
        items=[
            {"eco_id": "a", "is_overdue": True, "is_escalated": False},
            {"eco_id": "b", "is_overdue": True, "is_escalated": False},
            {"eco_id": "b-admin", "is_overdue": True, "is_escalated": True},
            {"eco_id": "c", "is_overdue": False, "is_escalated": False},
        ],
        anomalies={
            "no_candidates": [],
            "escalated_unresolved": [{"eco_id": "b"}],
            "overdue_not_escalated": [{"eco_id": "a"}],
            "total_anomalies": 2,
        },
    )

    cp = _run(
        script,
        str(current),
        "--mode",
        "state-change",
        "--baseline-dir",
        str(baseline),
        "--expect-delta",
        "overdue_count=1",
        "--expect-delta",
        "escalated_count=1",
        "--expect-delta",
        "items_count=1",
        "--expect-delta",
        "export_json_count=1",
        "--expect-delta",
        "export_csv_rows=1",
        "--expect-delta",
        "escalated_unresolved=1",
        "--expect-delta",
        "overdue_not_escalated=-1",
    )

    assert cp.returncode == 0, cp.stderr
    text = (current / "OBSERVATION_EVAL.md").read_text(encoding="utf-8")
    assert "- verdict: PASS" in text
    assert "state-change delta for overdue_count" in text


def test_p2_observation_evaluator_state_change_fails_on_unexpected_delta(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script = repo_root / "scripts" / "evaluate_p2_observation_results.py"

    baseline = _write_result_dir(
        tmp_path / "baseline",
        summary={"pending_count": 1, "overdue_count": 2, "escalated_count": 0},
        items=[
            {"eco_id": "a", "is_overdue": True, "is_escalated": False},
            {"eco_id": "b", "is_overdue": True, "is_escalated": False},
            {"eco_id": "c", "is_overdue": False, "is_escalated": False},
        ],
        anomalies={
            "no_candidates": [],
            "escalated_unresolved": [],
            "overdue_not_escalated": [{"eco_id": "a"}, {"eco_id": "b"}],
            "total_anomalies": 2,
        },
    )
    current = _write_result_dir(
        tmp_path / "current",
        summary={"pending_count": 1, "overdue_count": 3, "escalated_count": 1},
        items=[
            {"eco_id": "a", "is_overdue": True, "is_escalated": False},
            {"eco_id": "b", "is_overdue": True, "is_escalated": False},
            {"eco_id": "b-admin", "is_overdue": True, "is_escalated": True},
            {"eco_id": "c", "is_overdue": False, "is_escalated": False},
        ],
        anomalies={
            "no_candidates": [],
            "escalated_unresolved": [{"eco_id": "b"}],
            "overdue_not_escalated": [{"eco_id": "a"}],
            "total_anomalies": 2,
        },
    )

    cp = _run(
        script,
        str(current),
        "--mode",
        "state-change",
        "--baseline-dir",
        str(baseline),
        "--expect-delta",
        "overdue_count=0",
    )

    assert cp.returncode == 1
    text = (current / "OBSERVATION_EVAL.md").read_text(encoding="utf-8")
    assert "- verdict: FAIL" in text
    assert "actual_delta=1, expected_delta=0" in text
