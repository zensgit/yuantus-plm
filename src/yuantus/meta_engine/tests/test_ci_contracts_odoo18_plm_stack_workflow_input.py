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


def _workflow_text(repo_root: Path) -> str:
    workflow = repo_root / ".github" / "workflows" / "odoo18-plm-stack-regression.yml"
    assert workflow.is_file(), "Missing Odoo18 PLM stack regression workflow"
    return workflow.read_text(encoding="utf-8", errors="replace")


def test_odoo18_plm_stack_workflow_mode_input_is_choice_limited() -> None:
    repo_root = _find_repo_root(Path(__file__))
    text = _workflow_text(repo_root)

    for snippet in (
        "workflow_dispatch:",
        "inputs:",
        "mode:",
        'description: "Regression mode"',
        "required: false",
        'default: "full"',
        "type: choice",
        "options:\n          - smoke\n          - full",
    ):
        assert snippet in text


def test_odoo18_plm_stack_workflow_invokes_verifier_with_single_mode_arg() -> None:
    repo_root = _find_repo_root(Path(__file__))
    text = _workflow_text(repo_root)

    script_lines = [
        line.strip()
        for line in text.splitlines()
        if "scripts/verify_odoo18_plm_stack.sh" in line
    ]

    assert "chmod +x scripts/verify_odoo18_plm_stack.sh" in script_lines
    assert [
        line
        for line in script_lines
        if line.startswith("scripts/verify_odoo18_plm_stack.sh")
    ] == [
        'scripts/verify_odoo18_plm_stack.sh "${{ github.event.inputs.mode || \'full\' }}"'
    ]
