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


def test_strict_gate_recent_perf_regression_workflow_contracts() -> None:
    repo_root = _find_repo_root(Path(__file__))
    wf = repo_root / ".github" / "workflows" / "strict-gate-recent-perf-regression.yml"
    assert wf.is_file(), f"Missing workflow: {wf}"
    wf_text = _read(wf)

    for token in (
        "name: strict-gate-recent-perf-regression",
        "workflow_dispatch:",
        "schedule:",
        'cron: "0 5 * * 2"',
        "permissions:",
        "actions: write",
        "contents: read",
        "concurrency:",
        "cancel-in-progress: true",
        "github.ref",
    ):
        assert token in wf_text, f"workflow missing token: {token}"

    # Dispatch input contract.
    for token in (
        "ref:",
        "poll_interval_sec:",
        "max_wait_sec:",
        "regression_attempts:",
        "regression_retry_delay_sec:",
        "success_fail_if_no_metrics:",
        "type: string",
        "default: \"main\"",
        "default: \"8\"",
        "default: \"1800\"",
        "default: \"2\"",
        "default: \"15\"",
        "default: \"false\"",
    ):
        assert token in wf_text, f"workflow missing dispatch input token: {token}"

    # Script execution + summary output contract.
    for token in (
        "Run strict-gate recent perf audit regression",
        "scripts/strict_gate_recent_perf_audit_regression.sh",
        "--workflow strict-gate.yml",
        "--repo \"${{ github.repository }}\"",
        "--summary-json",
        "attempt-${attempt}",
        "seq 1 \"${attempts}\"",
        "regression_attempts must be an integer in [1,3]",
        "regression_retry_delay_sec must be a non-negative integer",
        "success_fail_if_no_metrics must be true|false",
        "strict-gate recent perf regression failed after ${attempts} attempts",
        "sleep \"${retry_delay_sec}\"",
        "REGRESSION_RUN_CONTEXT.txt",
        "success_fail_if_no_metrics=${success_fail_if_no_metrics}",
        "--success-fail-if-no-metrics \"${success_fail_if_no_metrics}\"",
        "attempt_rc=0",
        "if [[ -f \"${attempt_dir}/STRICT_GATE_RECENT_PERF_AUDIT_REGRESSION.md\" ]]",
        "if [[ -f \"${attempt_dir}/STRICT_GATE_RECENT_PERF_AUDIT_REGRESSION.json\" ]]",
        "cp -f \"${attempt_dir}/STRICT_GATE_RECENT_PERF_AUDIT_REGRESSION.md\"",
        "cp -f \"${attempt_dir}/STRICT_GATE_RECENT_PERF_AUDIT_REGRESSION.json\"",
        "Write regression summary to job summary",
        "STRICT_GATE_RECENT_PERF_AUDIT_REGRESSION.md",
        "STRICT_GATE_RECENT_PERF_AUDIT_REGRESSION.json",
        "JSON summary:",
    ):
        assert token in wf_text, f"workflow missing execution/summary token: {token}"

    # Artifact contract.
    for token in (
        "Upload strict-gate recent perf regression evidence",
        "name: strict-gate-recent-perf-regression",
        "Upload strict-gate recent perf regression raw outputs",
        "name: strict-gate-recent-perf-regression-raw",
        "tmp/strict-gate-artifacts/recent-perf-regression/${{ github.run_id }}",
    ):
        assert token in wf_text, f"workflow missing artifact token: {token}"
