from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from yuantus.tests.test_tenant_import_rehearsal_operator_packet import _write_green_packet


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
_SCRIPT = _REPO_ROOT / "scripts" / "precheck_tenant_import_rehearsal_operator.sh"


def test_operator_precheck_shell_is_syntax_valid() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", "-n", str(_SCRIPT)],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr


def test_operator_precheck_help_documents_db_free_scope() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--help"],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = cp.stdout
    assert "precheck_tenant_import_rehearsal_operator.sh" in out
    assert "does not print secret DSN values" in out
    assert "open database connections" in out
    assert "authorize cutover" in out


def test_operator_precheck_passes_with_green_packet_and_env(tmp_path: Path) -> None:
    implementation_packet_json = _write_green_packet(tmp_path)
    artifact_prefix = tmp_path / "tenant_acme"
    implementation_packet_json.rename(
        tmp_path / "tenant_acme_importer_implementation_packet.json"
    )
    env = os.environ.copy()
    env["SRC_DB_URL"] = "postgresql://user:secret@example.com/source"
    env["TGT_DB_URL"] = "postgresql://user:secret@example.com/target"

    cp = subprocess.run(  # noqa: S603,S607
        [
            "bash",
            str(_SCRIPT),
            "--artifact-prefix",
            str(artifact_prefix),
            "--source-url-env",
            "SRC_DB_URL",
            "--target-url-env",
            "TGT_DB_URL",
        ],
        cwd=_REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert "Ready for operator command execution: true" in cp.stdout
    assert "Ready for cutover: false" in cp.stdout
    assert "secret" not in cp.stdout
    assert "postgresql://" not in cp.stdout


def test_operator_precheck_blocks_missing_env_without_printing_values(tmp_path: Path) -> None:
    implementation_packet_json = _write_green_packet(tmp_path)
    artifact_prefix = tmp_path / "tenant_acme"
    implementation_packet_json.rename(
        tmp_path / "tenant_acme_importer_implementation_packet.json"
    )
    env = os.environ.copy()
    env.pop("SRC_DB_URL", None)
    env.pop("TGT_DB_URL", None)

    cp = subprocess.run(  # noqa: S603,S607
        [
            "bash",
            str(_SCRIPT),
            "--artifact-prefix",
            str(artifact_prefix),
            "--source-url-env",
            "SRC_DB_URL",
            "--target-url-env",
            "TGT_DB_URL",
        ],
        cwd=_REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert "missing environment variable: SRC_DB_URL" in cp.stdout
    assert "missing environment variable: TGT_DB_URL" in cp.stdout
    assert "Ready for cutover: false" in cp.stdout


def test_operator_precheck_blocks_non_green_packet(tmp_path: Path) -> None:
    implementation_packet_json = _write_green_packet(tmp_path)
    payload = json.loads(implementation_packet_json.read_text())
    payload["ready_for_claude_importer"] = False
    payload["ready_for_cutover"] = True
    payload["blockers"] = ["source drifted"]
    target = tmp_path / "tenant_acme_importer_implementation_packet.json"
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    artifact_prefix = tmp_path / "tenant_acme"
    env = os.environ.copy()
    env["SOURCE_DATABASE_URL"] = "postgresql://user:secret@example.com/source"
    env["TARGET_DATABASE_URL"] = "postgresql://user:secret@example.com/target"

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--artifact-prefix", str(artifact_prefix)],
        cwd=_REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert "implementation packet must have ready_for_claude_importer=true" in cp.stdout
    assert "implementation packet must have ready_for_cutover=false" in cp.stdout
    assert "implementation packet must have no blockers" in cp.stdout
    assert "secret" not in cp.stdout
