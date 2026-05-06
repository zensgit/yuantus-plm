from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "scripts").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root")


_REPO_ROOT = _find_repo_root(Path(__file__))
_DSN_LIKE_ARGUMENT = "--bad=postgresql://user:secret@example.com/source"
_SHELL_WRAPPERS = (
    "scripts/generate_tenant_import_rehearsal_env_template.sh",
    "scripts/precheck_tenant_import_rehearsal_operator.sh",
    "scripts/prepare_tenant_import_rehearsal_operator_commands.sh",
    "scripts/print_tenant_import_rehearsal_commands.sh",
    "scripts/run_tenant_import_operator_launchpack.sh",
    "scripts/run_tenant_import_rehearsal_operator_sequence.sh",
    "scripts/run_tenant_import_rehearsal_full_closeout.sh",
    "scripts/precheck_tenant_import_rehearsal_evidence.sh",
    "scripts/run_tenant_import_evidence_closeout.sh",
)


@pytest.mark.parametrize("script", _SHELL_WRAPPERS)
def test_shell_wrapper_unknown_argument_errors_do_not_echo_values(
    script: str,
) -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_REPO_ROOT / script), _DSN_LIKE_ARGUMENT],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    combined = cp.stdout + cp.stderr
    assert cp.returncode == 2
    assert "unknown argument" in combined
    assert "argument value hidden: true" in combined
    assert "postgresql://user" not in combined
    assert "secret@example.com" not in combined
