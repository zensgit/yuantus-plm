from __future__ import annotations

import json
import subprocess
from pathlib import Path

from yuantus.tests.tenant_import_shell_test_env import shell_test_env
from yuantus.tests.test_tenant_import_rehearsal_evidence import (
    _write_green_rehearsal,
    _write_operator_evidence,
)


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
_SCRIPT = _REPO_ROOT / "scripts" / "precheck_tenant_import_rehearsal_evidence.sh"


def _env() -> dict[str, str]:
    return shell_test_env(_REPO_ROOT)


def test_evidence_precheck_shell_is_syntax_valid() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", "-n", str(_SCRIPT)],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr


def test_evidence_precheck_help_documents_db_free_scope() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--help"],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = cp.stdout
    assert "precheck_tenant_import_rehearsal_evidence.sh" in out
    assert "operator-evidence precheck" in out
    assert "does not print database URL values" in out
    assert "authorize cutover" in out


def test_evidence_precheck_writes_evidence_reports_when_green(tmp_path: Path) -> None:
    packet_json, rehearsal_json = _write_green_rehearsal(tmp_path)
    operator_md = _write_operator_evidence(tmp_path / "operator-evidence.md")
    artifact_prefix = tmp_path / "tenant_acme"

    cp = subprocess.run(  # noqa: S603,S607
        [
            "bash",
            str(_SCRIPT),
            "--rehearsal-json",
            str(rehearsal_json),
            "--implementation-packet-json",
            str(packet_json),
            "--operator-evidence-md",
            str(operator_md),
            "--artifact-prefix",
            str(artifact_prefix),
        ],
        cwd=_REPO_ROOT,
        env=_env(),
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    evidence_json = tmp_path / "tenant_acme_import_rehearsal_evidence.json"
    evidence_md = tmp_path / "tenant_acme_import_rehearsal_evidence.md"
    assert evidence_json.is_file()
    assert evidence_md.is_file()
    payload = json.loads(evidence_json.read_text())
    assert payload["ready_for_rehearsal_evidence"] is True
    assert payload["ready_for_cutover"] is False
    assert "Ready for evidence closeout: true" in cp.stdout
    assert "Ready for cutover: false" in cp.stdout
    assert "postgresql://" not in cp.stdout
    assert "secret" not in cp.stdout


def test_evidence_precheck_fails_closed_for_missing_operator_evidence(
    tmp_path: Path,
) -> None:
    packet_json, rehearsal_json = _write_green_rehearsal(tmp_path)
    artifact_prefix = tmp_path / "tenant_acme"

    cp = subprocess.run(  # noqa: S603,S607
        [
            "bash",
            str(_SCRIPT),
            "--rehearsal-json",
            str(rehearsal_json),
            "--implementation-packet-json",
            str(packet_json),
            "--operator-evidence-md",
            str(tmp_path / "missing.md"),
            "--artifact-prefix",
            str(artifact_prefix),
        ],
        cwd=_REPO_ROOT,
        env=_env(),
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    evidence_json = tmp_path / "tenant_acme_import_rehearsal_evidence.json"
    evidence_md = tmp_path / "tenant_acme_import_rehearsal_evidence.md"
    assert evidence_json.is_file()
    assert evidence_md.is_file()
    payload = json.loads(evidence_json.read_text())
    assert payload["ready_for_rehearsal_evidence"] is False
    assert payload["ready_for_cutover"] is False
    assert f"operator evidence {tmp_path / 'missing.md'} does not exist" in payload["blockers"]


def test_evidence_precheck_preserves_db_free_scope() -> None:
    source = _SCRIPT.read_text()

    assert "tenant_import_rehearsal_evidence" in source
    assert "tenant_import_rehearsal --" not in source
    assert "confirm-rehearsal" not in source
    assert "psql" not in source
    assert "TENANCY_MODE" not in source
    assert "curl " not in source
    assert "gh " not in source
