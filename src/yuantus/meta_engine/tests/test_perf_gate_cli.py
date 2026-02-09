from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_min_report(
    path: Path,
    *,
    started: str,
    git: str,
    db: str,
    scenario: str = "Scenario A",
    measured: str = "100.0ms",
    status: str = "PASS",
) -> None:
    # Keep this aligned with scripts/perf_gate.py table parsing:
    # - header line must match exactly
    # - separator row starts with "| ---"
    # - the first 5 columns are used: Scenario / Target / Measured / Status / Notes
    text = "\n".join(
        [
            "# Perf Report",
            "",
            f"- Started: `{started}`",
            f"- Git: `{git}`",
            f"- DB: `{db}`",
            "",
            "## Results",
            "",
            "| Scenario | Target | Measured | Status | Notes |",
            "| --- | --- | --- | --- | --- |",
            f"| {scenario} | < 1s | {measured} | {status} | - |",
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")


def _run_gate(*args: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "scripts/perf_gate.py", *args]
    return subprocess.run(cmd, text=True, capture_output=True)


def test_perf_gate_filters_baselines_by_db_label(tmp_path: Path) -> None:
    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir(parents=True, exist_ok=True)

    _write_min_report(
        baseline_dir / "baseline_sqlite.md",
        started="2026-01-01T00:00:00Z",
        git="aaaaaaa",
        db="sqlite:////tmp/test.db",
        measured="100.0ms",
    )
    _write_min_report(
        baseline_dir / "baseline_pg.md",
        started="2026-01-02T00:00:00Z",
        git="bbbbbbb",
        db="postgresql+psycopg://u:p@localhost:5432/db",
        measured="200.0ms",
    )

    cand = tmp_path / "candidate_pg.md"
    _write_min_report(
        cand,
        started="2026-01-03T00:00:00Z",
        git="ccccccc",
        db="postgresql+psycopg://u:p@localhost:5432/db",
        measured="190.0ms",
    )

    cp = _run_gate(
        "--candidate",
        str(cand),
        "--baseline-dir",
        str(baseline_dir),
        "--baseline-glob",
        "*.md",
        "--window",
        "5",
        "--pct",
        "0.30",
        "--abs-ms",
        "10",
        "--baseline-stat",
        "max",
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    # Ensure only postgres baselines were considered: window should be 1 (only baseline_pg.md).
    assert "db=postgres window=1" in cp.stdout


def test_perf_gate_db_overrides_can_relax_threshold(tmp_path: Path) -> None:
    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir(parents=True, exist_ok=True)

    _write_min_report(
        baseline_dir / "baseline_pg.md",
        started="2026-01-01T00:00:00Z",
        git="aaaaaaa",
        db="postgresql+psycopg://u:p@localhost:5432/db",
        measured="100.0ms",
    )

    cand = tmp_path / "candidate_pg.md"
    _write_min_report(
        cand,
        started="2026-01-02T00:00:00Z",
        git="bbbbbbb",
        db="postgresql+psycopg://u:p@localhost:5432/db",
        measured="140.0ms",
    )

    cp = _run_gate(
        "--candidate",
        str(cand),
        "--baseline-dir",
        str(baseline_dir),
        "--baseline-glob",
        "*.md",
        "--window",
        "5",
        "--pct",
        "0.30",
        "--abs-ms",
        "10",
        "--db-pct",
        "postgres=0.50",
        "--baseline-stat",
        "max",
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert "pct=0.50" in cp.stdout


def test_perf_gate_fails_on_regression(tmp_path: Path) -> None:
    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir(parents=True, exist_ok=True)

    _write_min_report(
        baseline_dir / "baseline_sqlite.md",
        started="2026-01-01T00:00:00Z",
        git="aaaaaaa",
        db="sqlite:////tmp/test.db",
        measured="100.0ms",
    )

    cand = tmp_path / "candidate_sqlite.md"
    _write_min_report(
        cand,
        started="2026-01-02T00:00:00Z",
        git="bbbbbbb",
        db="sqlite:////tmp/test.db",
        measured="200.0ms",
    )

    cp = _run_gate(
        "--candidate",
        str(cand),
        "--baseline-dir",
        str(baseline_dir),
        "--baseline-glob",
        "*.md",
        "--window",
        "5",
        "--pct",
        "0.30",
        "--abs-ms",
        "10",
        "--baseline-stat",
        "max",
    )
    assert cp.returncode == 1
    assert "[gate] FAIL" in cp.stdout


def test_perf_gate_can_use_config_profile_for_glob_window_and_stat(tmp_path: Path) -> None:
    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir(parents=True, exist_ok=True)

    # The profile's baseline_glob should exclude this file. If it is mistakenly included,
    # it will dominate the window and change the baseline stat outcome.
    _write_min_report(
        baseline_dir / "ignore.md",
        started="2026-01-04T00:00:00Z",
        git="zzzzzzz",
        db="postgresql+psycopg://u:p@localhost:5432/db",
        measured="1000.0ms",
    )

    _write_min_report(
        baseline_dir / "baseline_1.md",
        started="2026-01-01T00:00:00Z",
        git="aaaaaaa",
        db="postgresql+psycopg://u:p@localhost:5432/db",
        measured="100.0ms",
    )
    _write_min_report(
        baseline_dir / "baseline_2.md",
        started="2026-01-02T00:00:00Z",
        git="bbbbbbb",
        db="postgresql+psycopg://u:p@localhost:5432/db",
        measured="200.0ms",
    )
    _write_min_report(
        baseline_dir / "baseline_3.md",
        started="2026-01-03T00:00:00Z",
        git="ccccccc",
        db="postgresql+psycopg://u:p@localhost:5432/db",
        measured="300.0ms",
    )

    cand = tmp_path / "candidate_pg.md"
    _write_min_report(
        cand,
        started="2026-01-05T00:00:00Z",
        git="ddddddd",
        db="postgresql+psycopg://u:p@localhost:5432/db",
        measured="260.0ms",
    )

    cfg = {
        "version": 1,
        "defaults": {"window": 2, "baseline_stat": "median", "pct": 0.0, "abs_ms": 0},
        "profiles": {"p": {"baseline_glob": "baseline_*.md"}},
    }
    cfg_path = tmp_path / "perf_gate.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    cp = _run_gate(
        "--config",
        str(cfg_path),
        "--profile",
        "p",
        "--candidate",
        str(cand),
        "--baseline-dir",
        str(baseline_dir),
    )
    # With baseline_glob=baseline_*.md and window=2, the window is: 300ms + 200ms.
    # median(300,200)=250ms, and candidate=260ms should fail (pct=0, abs_ms=0).
    assert cp.returncode == 1, cp.stdout + "\n" + cp.stderr
    assert "db=postgres window=2" in cp.stdout
    assert "stat=median" in cp.stdout
    assert "baseline=250.0ms" in cp.stdout


def test_perf_gate_config_db_overrides_applied_and_cli_can_override(tmp_path: Path) -> None:
    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir(parents=True, exist_ok=True)

    _write_min_report(
        baseline_dir / "baseline_pg.md",
        started="2026-01-01T00:00:00Z",
        git="aaaaaaa",
        db="postgresql+psycopg://u:p@localhost:5432/db",
        measured="100.0ms",
    )

    cand = tmp_path / "candidate_pg.md"
    _write_min_report(
        cand,
        started="2026-01-02T00:00:00Z",
        git="bbbbbbb",
        db="postgresql+psycopg://u:p@localhost:5432/db",
        measured="140.0ms",
    )

    cfg = {
        "version": 1,
        "defaults": {"window": 5, "baseline_stat": "max", "pct": 0.30, "abs_ms": 10},
        "db_overrides": {"postgres": {"pct": 0.50, "abs_ms": 15}},
        "profiles": {"p": {"baseline_glob": "*.md"}},
    }
    cfg_path = tmp_path / "perf_gate.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    cp = _run_gate(
        "--config",
        str(cfg_path),
        "--profile",
        "p",
        "--candidate",
        str(cand),
        "--baseline-dir",
        str(baseline_dir),
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert "pct=0.50" in cp.stdout
    assert "abs=15.0ms" in cp.stdout

    # CLI overrides should take precedence over config db_overrides.
    cp2 = _run_gate(
        "--config",
        str(cfg_path),
        "--profile",
        "p",
        "--candidate",
        str(cand),
        "--baseline-dir",
        str(baseline_dir),
        "--db-pct",
        "postgres=0.10",
        "--db-abs-ms",
        "postgres=5",
    )
    assert cp2.returncode == 1, cp2.stdout + "\n" + cp2.stderr
    assert "pct=0.10" in cp2.stdout
    assert "abs=5.0ms" in cp2.stdout
