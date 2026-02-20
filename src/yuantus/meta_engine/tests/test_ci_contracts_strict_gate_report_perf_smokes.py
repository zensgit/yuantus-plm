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


def test_strict_gate_report_declares_perf_smoke_env_toggles_in_help_and_notes() -> None:
    repo_root = _find_repo_root(Path(__file__))
    report_script = repo_root / "scripts" / "strict_gate_report.sh"
    assert report_script.is_file(), f"Missing {report_script}"
    text = _read(report_script)

    for token in (
        "RUN_RELEASE_ORCH_PERF=1",
        "RUN_ESIGN_PERF=1",
        "RUN_REPORTS_PERF=1",
        r'- \`RUN_RELEASE_ORCH_PERF\`: \`${RUN_RELEASE_ORCH_PERF:-<unset>}\`',
        r'- \`RUN_ESIGN_PERF\`: \`${RUN_ESIGN_PERF:-<unset>}\`',
        r'- \`RUN_REPORTS_PERF\`: \`${RUN_REPORTS_PERF:-<unset>}\`',
    ):
        assert token in text, f"strict_gate_report.sh missing perf-smoke token: {token!r}"


def test_strict_gate_report_wires_perf_smokes_into_results_and_failure_tails() -> None:
    repo_root = _find_repo_root(Path(__file__))
    report_script = repo_root / "scripts" / "strict_gate_report.sh"
    assert report_script.is_file(), f"Missing {report_script}"
    text = _read(report_script)

    expected_tokens = (
        "status_release_orch_perf=\"SKIP\"",
        "status_esign_perf=\"SKIP\"",
        "status_reports_perf=\"SKIP\"",
        "log_release_orch_perf=",
        "log_esign_perf=",
        "log_reports_perf=",
        "env -u BASE_URL -u PORT OUT_DIR=\"${OUT_DIR}/verify-run-h-e2e\" bash \"${REPO_ROOT}/scripts/verify_run_h_e2e.sh\"",
        "env -u BASE_URL -u PORT OUT_DIR=\"${OUT_DIR}/verify-release-orchestration-perf\" bash \"${REPO_ROOT}/scripts/verify_release_orchestration_perf_smoke.sh\"",
        "env -u BASE_URL -u PORT OUT_DIR=\"${OUT_DIR}/verify-esign-perf\" bash \"${REPO_ROOT}/scripts/verify_esign_perf_smoke.sh\"",
        "env -u BASE_URL -u PORT OUT_DIR=\"${OUT_DIR}/verify-reports-perf\" bash \"${REPO_ROOT}/scripts/verify_reports_perf_smoke.sh\"",
        "verify_release_orchestration_perf_smoke",
        "verify_esign_perf_smoke",
        "verify_reports_perf_smoke",
        "RUN_RELEASE_ORCH_PERF not set",
        "RUN_ESIGN_PERF not set",
        "RUN_REPORTS_PERF not set",
        "| verify_release_orchestration_perf_smoke | $status_release_orch_perf |",
        "| verify_esign_perf_smoke | $status_esign_perf |",
        "| verify_reports_perf_smoke | $status_reports_perf |",
        "### verify_release_orchestration_perf_smoke",
        "### verify_esign_perf_smoke",
        "### verify_reports_perf_smoke",
    )
    for token in expected_tokens:
        assert token in text, f"strict_gate_report.sh missing perf-smoke wiring token: {token!r}"
