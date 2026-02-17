from __future__ import annotations

from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / ".github").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + .github/)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_strict_gate_workflow_wiring_and_runbook_are_stable() -> None:
    repo_root = _find_repo_root(Path(__file__))

    wf = repo_root / ".github" / "workflows" / "strict-gate.yml"
    assert wf.is_file(), f"Missing workflow: {wf}"
    wf_text = _read(wf)

    # Triggers (ops contract).
    assert "workflow_dispatch:" in wf_text
    assert "schedule:" in wf_text
    assert 'cron: "0 3 * * *"' in wf_text
    assert 'cron: "0 4 * * 1"' in wf_text
    assert "run_demo:" in wf_text
    assert "run_perf_smokes:" in wf_text
    assert 'default: "false"' in wf_text

    # Concurrency contract (must cancel in-progress runs on same ref).
    assert "concurrency:" in wf_text
    assert "group: ${{ github.workflow }}-${{ github.ref }}" in wf_text
    assert "cancel-in-progress: true" in wf_text

    # Evidence output wiring (report path + logs dir + artifacts).
    assert "bash scripts/strict_gate_report.sh" in wf_text
    assert "python3 scripts/strict_gate_perf_summary.py" in wf_text
    assert "python3 scripts/strict_gate_perf_trend.py" in wf_text
    assert "OUT_DIR: tmp/strict-gate/STRICT_GATE_CI_${{ github.run_id }}" in wf_text
    assert "REPORT_PATH: docs/DAILY_REPORTS/STRICT_GATE_CI_${{ github.run_id }}.md" in wf_text
    assert "PERF_SUMMARY_PATH: docs/DAILY_REPORTS/STRICT_GATE_CI_${{ github.run_id }}_PERF.md" in wf_text
    assert "PERF_TREND_PATH: docs/DAILY_REPORTS/STRICT_GATE_CI_${{ github.run_id }}_PERF_TREND.md" in wf_text
    assert "github.event.inputs.run_perf_smokes" in wf_text
    assert "github.event.schedule" in wf_text
    assert "export RUN_RELEASE_ORCH_PERF=1" in wf_text
    assert "export RUN_ESIGN_PERF=1" in wf_text
    assert "export RUN_REPORTS_PERF=1" in wf_text
    assert "weekly_schedule_perf" in wf_text

    for needle in (
        "name: strict-gate-report",
        "path: docs/DAILY_REPORTS/STRICT_GATE_CI_${{ github.run_id }}.md",
        "name: strict-gate-perf-summary",
        "path: docs/DAILY_REPORTS/STRICT_GATE_CI_${{ github.run_id }}_PERF.md",
        "name: strict-gate-perf-trend",
        "path: docs/DAILY_REPORTS/STRICT_GATE_CI_${{ github.run_id }}_PERF_TREND.md",
        "name: strict-gate-logs",
        "path: tmp/strict-gate/STRICT_GATE_CI_${{ github.run_id }}",
    ):
        assert needle in wf_text, f"strict-gate workflow missing: {needle!r}"

    # Job summary should include copy/paste download hints.
    assert "gh run download" in wf_text
    assert "tmp/strict-gate-artifacts" in wf_text

    # Runbook must document how to run + download artifacts.
    runbook = repo_root / "docs" / "RUNBOOK_STRICT_GATE.md"
    assert runbook.is_file(), f"Missing runbook: {runbook}"
    runbook_text = _read(runbook)

    for token in (
        "gh workflow run strict-gate",
        "gh run list --workflow strict-gate",
        "gh run download",
        "strict-gate-report",
        "strict-gate-perf-summary",
        "strict-gate-perf-trend",
        "strict-gate-logs",
        "verify_release_orchestration_perf_smoke",
        "verify_esign_perf_smoke",
        "verify_reports_perf_smoke",
        "RUN_RELEASE_ORCH_PERF=1",
        "RUN_ESIGN_PERF=1",
        "RUN_REPORTS_PERF=1",
        "run_perf_smokes=true",
        "每周一 `04:00 UTC`",
        "strict_gate_perf_summary.py",
        "strict_gate_perf_trend.py",
        "strict_gate_perf_download_and_trend.sh",
        "STRICT_GATE_PERF_TREND.md",
    ):
        assert token in runbook_text, f"strict-gate runbook missing: {token!r}"
