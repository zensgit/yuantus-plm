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


def test_odoo18_plm_stack_workflow_runtime_is_pinned_for_reproducibility() -> None:
    repo_root = _find_repo_root(Path(__file__))
    text = _workflow_text(repo_root)

    for snippet in (
        "runs-on: ubuntu-latest",
        "timeout-minutes: 30",
        "uses: actions/setup-python@v6",
        'python-version: "3.11"',
        'cache: "pip"',
        "python -m pip install --upgrade pip",
        'pip install -e ".[dev]"',
        "PYTHONPYCACHEPREFIX: /tmp/yuantus-pyc",
    ):
        assert snippet in text


def test_odoo18_plm_stack_workflow_uses_read_only_permissions_and_serial_concurrency() -> None:
    repo_root = _find_repo_root(Path(__file__))
    text = _workflow_text(repo_root)

    for snippet in (
        "permissions:\n  actions: read\n  contents: read",
        "concurrency:\n  group: ${{ github.workflow }}-${{ github.ref }}\n  cancel-in-progress: true",
    ):
        assert snippet in text
