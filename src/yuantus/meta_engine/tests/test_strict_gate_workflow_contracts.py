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
    assert "run_recent_perf_audit:" in wf_text
    assert "recent_perf_audit_limit:" in wf_text
    assert "recent_perf_max_run_age_days:" in wf_text
    assert "recent_perf_conclusion:" in wf_text
    assert "recent_perf_fail_if_no_runs:" in wf_text
    assert "recent_perf_fail_if_skipped:" in wf_text
    assert "recent_perf_fail_if_none_downloaded:" in wf_text
    assert "recent_perf_fail_if_no_metrics:" in wf_text
    assert "type: boolean" in wf_text
    assert "type: choice" in wf_text
    assert "type: string" in wf_text
    assert "options:" in wf_text
    assert "\n          - any\n          - success\n          - failure\n" in wf_text
    assert "run_demo:\n        description:" in wf_text and "\n        type: boolean\n        required: false\n        default: false\n" in wf_text
    assert "recent_perf_fail_if_no_metrics:\n        description:" in wf_text and "\n        type: boolean\n        required: false\n        default: true\n" in wf_text

    # Concurrency contract (must cancel in-progress runs on same ref).
    assert "concurrency:" in wf_text
    assert "group: ${{ github.workflow }}-${{ github.ref }}" in wf_text
    assert "cancel-in-progress: true" in wf_text

    # Evidence output wiring (report path + logs dir + artifacts).
    assert "name: Validate recent perf audit inputs" in wf_text
    assert "id: validate_recent_perf_inputs" in wf_text
    assert "id: strict_gate_report" in wf_text
    assert "recent_perf_conclusion must be one of any|success|failure" in wf_text
    assert "recent_perf_audit_limit must be a positive integer" in wf_text
    assert "recent_perf_audit_limit must be <= 100" in wf_text
    assert "recent_perf_max_run_age_days must be a non-negative integer" in wf_text
    assert "recent_perf_max_run_age_days must be <= 100" in wf_text
    assert "bash scripts/strict_gate_report.sh" in wf_text
    assert "python3 scripts/strict_gate_perf_summary.py" in wf_text
    assert "python3 scripts/strict_gate_perf_trend.py" in wf_text
    assert "bash scripts/strict_gate_perf_download_and_trend.sh" in wf_text
    assert "--fail-if-no-metrics" in wf_text
    assert "--conclusion" in wf_text
    assert "--max-run-age-days" in wf_text
    assert "python -m pip install -e . pytest" in wf_text
    assert "OUT_DIR: tmp/strict-gate/STRICT_GATE_CI_${{ github.run_id }}" in wf_text
    assert "REPORT_PATH: docs/DAILY_REPORTS/STRICT_GATE_CI_${{ github.run_id }}.md" in wf_text
    assert "PERF_SUMMARY_PATH: docs/DAILY_REPORTS/STRICT_GATE_CI_${{ github.run_id }}_PERF.md" in wf_text
    assert "PERF_TREND_PATH: docs/DAILY_REPORTS/STRICT_GATE_CI_${{ github.run_id }}_PERF_TREND.md" in wf_text
    assert "steps.validate_recent_perf_inputs.outcome == 'success'" in wf_text
    assert wf_text.count("steps.validate_recent_perf_inputs.outcome == 'success'") >= 2
    assert "steps.strict_gate_report.outcome != 'skipped'" in wf_text
    assert wf_text.count("steps.strict_gate_report.outcome != 'skipped'") >= 7
    assert "Recent perf audit skipped reason" in wf_text
    assert "Validate recent perf audit inputs=${RECENT_PERF_VALIDATE_OUTCOME}" in wf_text
    assert "Artifact availability: report/perf-summary/perf-trend/logs=" in wf_text
    assert "strict-gate report/perf/log artifacts not generated (report step skipped)" in wf_text
    assert "strict-gate-recent-perf-audit artifact not generated" in wf_text
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
        "name: strict-gate-recent-perf-audit",
        "path: tmp/strict-gate-artifacts/recent-perf-audit/${{ github.run_id }}",
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
        "run_recent_perf_audit=true",
        "recent_perf_max_run_age_days=",
        "recent_perf_conclusion=",
        "recent_perf_fail_if_no_metrics=true",
        "每周一 `04:00 UTC`",
        "strict_gate_perf_summary.py",
        "strict_gate_perf_trend.py",
        "strict_gate_perf_download_and_trend.sh",
        "strict_gate_recent_perf_audit_regression.sh",
        "strict-gate-recent-perf-regression.yml",
        "strict-gate-recent-perf-regression",
        "strict-gate-recent-perf-regression-raw",
        "每周二 `05:00 UTC`",
        "--fail-if-no-metrics",
        "--conclusion",
        "--max-run-age-days",
        "--run-id <run_id>",
        "strict_gate_perf_download.json",
        "STRICT_GATE_PERF_TREND.md",
        "STRICT_GATE_RECENT_PERF_AUDIT_REGRESSION.md",
        "STRICT_GATE_RECENT_PERF_AUDIT_REGRESSION.json",
        "Recent perf audit skipped reason",
        "strict-gate-recent-perf-audit",
    ):
        assert token in runbook_text, f"strict-gate runbook missing: {token!r}"
