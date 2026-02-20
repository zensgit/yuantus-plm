from __future__ import annotations

import re
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


def _extract_dispatch_input_block(workflow_text: str, input_name: str) -> str:
    lines = workflow_text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line == f"      {input_name}:":
            start = i
            break
    assert start is not None, f"Missing workflow_dispatch input: {input_name}"

    end = len(lines)
    for j in range(start + 1, len(lines)):
        if re.match(r"^      [a-zA-Z0-9_-]+:\s*$", lines[j]):
            end = j
            break
        if re.match(r"^  [a-zA-Z0-9_-]+:\s*$", lines[j]):
            end = j
            break
    return "\n".join(lines[start:end])


def test_strict_gate_workflow_dispatch_input_type_matrix_is_stable() -> None:
    repo_root = _find_repo_root(Path(__file__))
    wf = repo_root / ".github" / "workflows" / "strict-gate.yml"
    assert wf.is_file(), f"Missing workflow: {wf}"
    wf_text = _read(wf)

    assert "workflow_dispatch:" in wf_text
    assert "inputs:" in wf_text

    boolean_inputs = (
        "run_demo",
        "run_perf_smokes",
        "run_recent_perf_audit",
        "recent_perf_fail_if_no_runs",
        "recent_perf_fail_if_skipped",
        "recent_perf_fail_if_none_downloaded",
        "recent_perf_fail_if_no_metrics",
    )
    for name in boolean_inputs:
        block = _extract_dispatch_input_block(wf_text, name)
        assert "type: boolean" in block, f"{name} must be boolean input"
        assert "required: false" in block, f"{name} must stay optional"

    for name in ("recent_perf_audit_limit", "recent_perf_max_run_age_days"):
        block = _extract_dispatch_input_block(wf_text, name)
        assert "type: string" in block, f"{name} must stay string input"
        assert "required: false" in block, f"{name} must stay optional"

    conclusion_block = _extract_dispatch_input_block(wf_text, "recent_perf_conclusion")
    assert "type: choice" in conclusion_block
    assert "options:" in conclusion_block
    assert "- any" in conclusion_block
    assert "- success" in conclusion_block
    assert "- failure" in conclusion_block
    assert 'default: "any"' in conclusion_block

    no_metrics_block = _extract_dispatch_input_block(wf_text, "recent_perf_fail_if_no_metrics")
    assert "default: true" in no_metrics_block
