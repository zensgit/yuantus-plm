from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "src").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root")


_REPO_ROOT = _find_repo_root(Path(__file__))
_DSN_LIKE_ARGUMENT = "--bad=postgresql://user:secret@example.com/source"
_TENANT_IMPORT_CLI_MODULES = (
    "tenant_import_rehearsal",
    "tenant_import_rehearsal_evidence",
    "tenant_import_rehearsal_evidence_archive",
    "tenant_import_rehearsal_evidence_handoff",
    "tenant_import_rehearsal_evidence_intake",
    "tenant_import_rehearsal_evidence_template",
    "tenant_import_rehearsal_external_status",
    "tenant_import_rehearsal_handoff",
    "tenant_import_rehearsal_implementation_packet",
    "tenant_import_rehearsal_next_action",
    "tenant_import_rehearsal_operator_bundle",
    "tenant_import_rehearsal_operator_flow",
    "tenant_import_rehearsal_operator_launchpack",
    "tenant_import_rehearsal_operator_packet",
    "tenant_import_rehearsal_operator_request",
    "tenant_import_rehearsal_plan",
    "tenant_import_rehearsal_readiness",
    "tenant_import_rehearsal_redaction_guard",
    "tenant_import_rehearsal_reviewer_packet",
    "tenant_import_rehearsal_source_preflight",
    "tenant_import_rehearsal_synthetic_drill",
    "tenant_import_rehearsal_target_preflight",
)


@pytest.mark.parametrize("module", _TENANT_IMPORT_CLI_MODULES)
def test_python_cli_unknown_argument_errors_do_not_echo_values(
    module: str,
) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(_REPO_ROOT / "src")

    cp = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            f"yuantus.scripts.{module}",
            _DSN_LIKE_ARGUMENT,
        ],
        cwd=_REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    combined = cp.stdout + cp.stderr
    assert cp.returncode == 2
    assert "CLI parse failed" in combined
    assert "argument value hidden: true" in combined
    assert "postgresql://user" not in combined
    assert "secret@example.com" not in combined
