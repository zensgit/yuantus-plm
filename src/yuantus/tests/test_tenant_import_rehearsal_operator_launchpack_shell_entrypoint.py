from __future__ import annotations

import json
import subprocess
from pathlib import Path

from yuantus.tests.tenant_import_shell_test_env import shell_test_env
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
_SCRIPT = _REPO_ROOT / "scripts" / "run_tenant_import_operator_launchpack.sh"


def _env() -> dict[str, str]:
    return shell_test_env(_REPO_ROOT)


def test_shell_entrypoint_is_syntax_valid() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", "-n", str(_SCRIPT)],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr


def test_shell_entrypoint_help_documents_db_free_scope() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--help"],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = cp.stdout
    assert "run_tenant_import_operator_launchpack.sh" in out
    assert "DB-free P3.4 tenant import operator launchpack" in out
    assert "does not open database connections" in out
    assert "never authorizes production cutover" in out


def test_shell_entrypoint_builds_launchpack_with_default_outputs(tmp_path: Path) -> None:
    implementation_packet_json = _write_green_packet(tmp_path)
    artifact_prefix = tmp_path / "tenant_acme"

    cp = subprocess.run(  # noqa: S603,S607
        [
            "bash",
            str(_SCRIPT),
            "--implementation-packet-json",
            str(implementation_packet_json),
            "--artifact-prefix",
            str(artifact_prefix),
        ],
        cwd=_REPO_ROOT,
        env=_env(),
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    output_json = tmp_path / "tenant_acme_operator_launchpack.json"
    output_md = tmp_path / "tenant_acme_operator_launchpack.md"
    payload = json.loads(output_json.read_text())
    assert payload["ready_for_operator_launchpack"] is True
    assert payload["ready_for_cutover"] is False
    assert payload["outputs"]["operator_packet_json"] == str(
        tmp_path / "tenant_acme_operator_execution_packet.json"
    )
    assert Path(payload["outputs"]["operator_bundle_md"]).is_file()
    assert "Ready for cutover: `false`" in output_md.read_text()


def test_shell_entrypoint_rejects_invalid_variable_name_before_python(
    tmp_path: Path,
) -> None:
    implementation_packet_json = _write_green_packet(tmp_path)
    marker = tmp_path / "python-invoked"
    fake_python = tmp_path / "python"
    fake_python.write_text(f"#!/usr/bin/env bash\ntouch {marker}\n")
    fake_python.chmod(0o755)
    env = _env()
    env["PYTHON"] = str(fake_python)

    cp = subprocess.run(  # noqa: S603,S607
        [
            "bash",
            str(_SCRIPT),
            "--implementation-packet-json",
            str(implementation_packet_json),
            "--artifact-prefix",
            str(tmp_path / "tenant_acme"),
            "--target-url-env",
            "TARGET-DATABASE-URL",
        ],
        cwd=_REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 2
    assert "--target-url-env must be an uppercase shell environment variable name" in cp.stderr
    assert not marker.exists()


def test_shell_entrypoint_preserves_launchpack_only_scope() -> None:
    source = _SCRIPT.read_text()

    assert "tenant_import_rehearsal_operator_launchpack" in source
    assert "tenant_import_rehearsal " not in source
    assert "tenant_import_rehearsal.py" not in source
    assert "psql" not in source
    assert "TENANCY_MODE" not in source
    assert "confirm-rehearsal" not in source
