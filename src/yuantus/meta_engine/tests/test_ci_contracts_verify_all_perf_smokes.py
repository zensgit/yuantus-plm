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


def test_verify_all_includes_perf_smoke_env_toggles_and_summary_lines() -> None:
    repo_root = _find_repo_root(Path(__file__))
    verify_all = repo_root / "scripts" / "verify_all.sh"
    assert verify_all.is_file(), f"Missing {verify_all}"
    text = _read(verify_all)

    for token in (
        'RUN_RELEASE_ORCH_PERF="${RUN_RELEASE_ORCH_PERF:-0}"',
        'RUN_REPORTS_PERF="${RUN_REPORTS_PERF:-0}"',
        'RUN_ESIGN_PERF="${RUN_ESIGN_PERF:-0}"',
        'echo "RUN_RELEASE_ORCH_PERF: $RUN_RELEASE_ORCH_PERF"',
        'echo "RUN_REPORTS_PERF: $RUN_REPORTS_PERF"',
        'echo "RUN_ESIGN_PERF: $RUN_ESIGN_PERF"',
    ):
        assert token in text, f"verify_all.sh missing token: {token}"


def test_verify_all_wires_perf_smoke_scripts_as_optional_steps() -> None:
    repo_root = _find_repo_root(Path(__file__))
    verify_all = repo_root / "scripts" / "verify_all.sh"
    assert verify_all.is_file(), f"Missing {verify_all}"
    text = _read(verify_all)

    expected_tokens = (
        "$SCRIPT_DIR/verify_release_orchestration_perf_smoke.sh",
        "$SCRIPT_DIR/verify_reports_perf_smoke.sh",
        "$SCRIPT_DIR/verify_esign_perf_smoke.sh",
        'skip_test "Release Orchestration (Perf Smoke)" "RUN_RELEASE_ORCH_PERF=0"',
        'skip_test "Reports (Perf Smoke)" "RUN_REPORTS_PERF=0"',
        'skip_test "E-Sign (Perf Smoke)" "RUN_ESIGN_PERF=0"',
    )
    for token in expected_tokens:
        assert token in text, f"verify_all.sh missing perf-smoke wiring token: {token}"
