from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "scripts").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + scripts/)")


def test_strict_gate_perf_summary_renders_table_from_metrics_files(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_perf_summary.py"
    assert script.is_file(), f"Missing script: {script}"

    logs_dir = tmp_path / "strict-gate" / "STRICT_GATE_CI_TEST"
    rel_orch_dir = logs_dir / "verify-release-orchestration-perf"
    rel_orch_dir.mkdir(parents=True, exist_ok=True)

    (rel_orch_dir / "metrics_summary.json").write_text(
        json.dumps(
            {
                "release_orchestration": {
                    "plan": {"p95_ms": 120.5, "threshold_ms": 1800.0, "samples": 5},
                    "execute_dry_run": {"p95_ms": 2400.0, "threshold_ms": 2200.0, "samples": 5},
                }
            }
        ),
        encoding="utf-8",
    )

    out_path = tmp_path / "strict-gate-perf-summary.md"
    cp = subprocess.run(  # noqa: S603
        [
            sys.executable,
            str(script),
            "--logs-dir",
            str(logs_dir),
            "--out",
            str(out_path),
        ],
        text=True,
        capture_output=True,
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = out_path.read_text(encoding="utf-8", errors="replace")

    assert "## Perf Smoke Summary" in out
    assert "| Metric | Status | p95 (ms) | Threshold (ms) | Samples | Source |" in out
    assert "| release_orchestration.plan | PASS | 120.500 | 1800.000 | 5 |" in out
    assert "| release_orchestration.execute_dry_run | FAIL | 2400.000 | 2200.000 | 5 |" in out


def test_strict_gate_perf_summary_reports_missing_metrics(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_perf_summary.py"
    assert script.is_file(), f"Missing script: {script}"

    logs_dir = tmp_path / "strict-gate" / "STRICT_GATE_CI_EMPTY"
    logs_dir.mkdir(parents=True, exist_ok=True)
    out_path = tmp_path / "strict-gate-perf-summary-empty.md"

    cp = subprocess.run(  # noqa: S603
        [
            sys.executable,
            str(script),
            "--logs-dir",
            str(logs_dir),
            "--out",
            str(out_path),
        ],
        text=True,
        capture_output=True,
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = out_path.read_text(encoding="utf-8", errors="replace")
    assert "No perf metrics found" in out
