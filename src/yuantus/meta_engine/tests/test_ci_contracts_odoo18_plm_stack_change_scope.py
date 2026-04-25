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


def _extract_contract_checks_block(ci_workflow_text: str) -> str:
    lines = ci_workflow_text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "- name: Contract checks (perf workflows + delivery doc index)":
            start = i
            break
    assert start is not None, "Missing CI contracts step"

    end = len(lines)
    for j in range(start + 1, len(lines)):
        if re.match(r"^  [a-zA-Z0-9_-]+:\s*$", lines[j]):
            end = j
            break

    return "\n".join(lines[start:end])


def test_odoo18_plm_stack_workflow_and_script_changes_trigger_contracts() -> None:
    repo_root = _find_repo_root(Path(__file__))
    ci_text = _read(repo_root / ".github" / "workflows" / "ci.yml")

    for snippet in (
        ".github/workflows/*.yml|.github/workflows/*.yaml|configs/perf_gate.json)",
        'run_contracts="true"',
        'reason_contracts="${reason_contracts:-matched workflow/perf config: ${f}}"',
        "scripts/*.sh|scripts/*.py)",
        'reason_contracts="${reason_contracts:-matched scripts: ${f}}"',
    ):
        assert snippet in ci_text


def test_odoo18_plm_stack_contract_tests_are_in_ci_contracts_job() -> None:
    repo_root = _find_repo_root(Path(__file__))
    ci_text = _read(repo_root / ".github" / "workflows" / "ci.yml")
    block = _extract_contract_checks_block(ci_text)

    for test_path in (
        "src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_change_scope.py",
        "src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_workflow_input.py",
        "src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_discoverability.py",
        "src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py",
    ):
        assert test_path in block
