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


def _assert_has_concurrency(*, name: str, text: str) -> None:
    # We use string checks (not YAML parsing) to keep this test dependency-free.
    assert "concurrency:" in text, f"{name}: missing concurrency"
    assert "cancel-in-progress: true" in text, f"{name}: concurrency must cancel in-progress runs"
    assert "github.ref" in text, f"{name}: concurrency group should include github.ref"


def test_key_workflows_define_concurrency_to_avoid_wasted_ci_minutes() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = repo_root / ".github" / "workflows"

    ci = workflows / "ci.yml"
    strict_gate = workflows / "strict-gate.yml"
    strict_gate_recent_perf_regression = workflows / "strict-gate-recent-perf-regression.yml"
    regression = workflows / "regression.yml"
    perf_p5 = workflows / "perf-p5-reports.yml"
    perf_roadmap = workflows / "perf-roadmap-9-3.yml"

    _assert_has_concurrency(name=str(ci), text=_read(ci))
    _assert_has_concurrency(name=str(strict_gate), text=_read(strict_gate))
    _assert_has_concurrency(
        name=str(strict_gate_recent_perf_regression),
        text=_read(strict_gate_recent_perf_regression),
    )
    _assert_has_concurrency(name=str(regression), text=_read(regression))
    _assert_has_concurrency(name=str(perf_p5), text=_read(perf_p5))
    _assert_has_concurrency(name=str(perf_roadmap), text=_read(perf_roadmap))
