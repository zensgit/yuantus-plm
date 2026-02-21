from __future__ import annotations

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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_recent_perf_audit_regression_script_contracts() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_recent_perf_audit_regression.sh"
    assert script.is_file(), f"Missing script: {script}"
    text = _read(script)

    # CLI contract.
    for token in (
        "--workflow",
        "--ref",
        "--repo",
        "--poll-interval-sec",
        "--max-wait-sec",
        "--success-limit",
        "--success-max-run-age-days",
        "--success-conclusion",
        "--success-fail-if-no-metrics",
        "--summary-json",
        "--out-dir",
    ):
        assert token in text, f"regression script missing CLI token: {token}"

    # Behavior contract: invalid case fails + skips, valid case succeeds and uploads.
    for token in (
        "recent_perf_audit_limit=101",
        "Validate recent perf audit inputs",
        "Optional recent perf audit (download + trend)",
        "Upload strict gate recent perf audit",
        "assert_equals \"$invalid_conclusion\" \"failure\"",
        "assert_equals \"$invalid_optional\" \"skipped\"",
        "assert_equals \"$invalid_upload\" \"skipped\"",
        "assert_equals \"$valid_conclusion\" \"success\"",
        "assert_equals \"$valid_optional\" \"success\"",
        "assert_equals \"$valid_upload\" \"success\"",
        "recent_perf_fail_if_no_metrics=\"${SUCCESS_FAIL_IF_NO_METRICS}\"",
        "command -v rg",
        "grep -q \"ERROR: recent_perf_audit_limit must be <= 100\"",
        "set_failure",
        "trap 'on_error \"$LINENO\" \"$BASH_COMMAND\"' ERR",
    ):
        assert token in text, f"regression script missing behavior token: {token}"

    # Artifact contract: invalid run has zero artifacts; valid run includes full set.
    for token in (
        "invalid_artifact_count",
        "assert_equals \"$invalid_artifact_count\" \"0\"",
        "get_artifact_names",
        "strict-gate-report",
        "strict-gate-perf-summary",
        "strict-gate-perf-trend",
        "strict-gate-logs",
        "strict-gate-recent-perf-audit",
        "assert_contains \"$valid_artifact_names\"",
    ):
        assert token in text, f"regression script missing artifact token: {token}"

    # Evidence contract.
    for token in (
        "STRICT_GATE_RECENT_PERF_AUDIT_REGRESSION.md",
        "STRICT_GATE_RECENT_PERF_AUDIT_REGRESSION.json",
        "\"result\": os.environ[\"RUN_RESULT_VALUE\"]",
        "\"failure_reason\": os.environ[\"FAILURE_REASON_VALUE\"]",
        "requested recent_perf_fail_if_no_metrics",
        "summary_md=",
        "summary_json=",
    ):
        assert token in text, f"regression script missing evidence token: {token}"
