from __future__ import annotations

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


def test_strict_gate_perf_trend_builds_table_and_sorts_latest_first(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_perf_trend.py"
    assert script.is_file(), f"Missing script: {script}"

    report_dir = tmp_path / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "STRICT_GATE_CI_100_PERF.md").write_text(
        "\n".join(
            [
                "## Perf Smoke Summary",
                "",
                "| Metric | Status | p95 (ms) | Threshold (ms) | Samples | Source |",
                "| --- | --- | --- | --- | --- | --- |",
                "| release_orchestration.plan | PASS | 100.000 | 1800.000 | 5 | `a` |",
                "| reports.search | PASS | 300.000 | 1600.000 | 5 | `b` |",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (report_dir / "STRICT_GATE_CI_200_PERF.md").write_text(
        "\n".join(
            [
                "## Perf Smoke Summary",
                "",
                "| Metric | Status | p95 (ms) | Threshold (ms) | Samples | Source |",
                "| --- | --- | --- | --- | --- | --- |",
                "| release_orchestration.plan | FAIL | 1900.000 | 1800.000 | 5 | `a` |",
                "| reports.search | PASS | 350.000 | 1600.000 | 5 | `b` |",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    out_path = tmp_path / "STRICT_GATE_PERF_TREND.md"
    cp = subprocess.run(  # noqa: S603
        [
            sys.executable,
            str(script),
            "--dir",
            str(report_dir),
            "--out",
            str(out_path),
            "--limit",
            "10",
        ],
        text=True,
        capture_output=True,
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = out_path.read_text(encoding="utf-8", errors="replace")

    assert "# Strict Gate Perf Smoke Trend" in out
    # Run 200 should appear before run 100 (latest CI run id first).
    assert out.index("`STRICT_GATE_CI_200`") < out.index("`STRICT_GATE_CI_100`")
    assert "| `STRICT_GATE_CI_200` | FAIL |" in out
    assert "FAIL 1900.000/1800.000" in out
    assert "PASS 300.000/1600.000" in out


def test_strict_gate_perf_trend_handles_empty_runs_flag(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_perf_trend.py"
    assert script.is_file(), f"Missing script: {script}"

    report_dir = tmp_path / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "STRICT_GATE_CI_300_PERF.md").write_text(
        "## Perf Smoke Summary\n\n- No perf metrics found (perf-smokes skipped or failed before metrics output).\n",
        encoding="utf-8",
    )

    out_path_default = tmp_path / "trend_default.md"
    cp_default = subprocess.run(  # noqa: S603
        [
            sys.executable,
            str(script),
            "--dir",
            str(report_dir),
            "--out",
            str(out_path_default),
        ],
        text=True,
        capture_output=True,
    )
    assert cp_default.returncode == 0, cp_default.stdout + "\n" + cp_default.stderr
    out_default = out_path_default.read_text(encoding="utf-8", errors="replace")
    assert "No perf summary runs found." in out_default

    out_path_include = tmp_path / "trend_include.md"
    cp_include = subprocess.run(  # noqa: S603
        [
            sys.executable,
            str(script),
            "--dir",
            str(report_dir),
            "--out",
            str(out_path_include),
            "--include-empty",
        ],
        text=True,
        capture_output=True,
    )
    assert cp_include.returncode == 0, cp_include.stdout + "\n" + cp_include.stderr
    out_include = out_path_include.read_text(encoding="utf-8", errors="replace")
    assert "| `STRICT_GATE_CI_300` | NO_METRICS |" in out_include
