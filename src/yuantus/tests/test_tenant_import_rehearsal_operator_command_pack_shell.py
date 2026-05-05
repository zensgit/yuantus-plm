from __future__ import annotations

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
_SCRIPT = _REPO_ROOT / "scripts" / "prepare_tenant_import_rehearsal_operator_commands.sh"


def test_operator_command_pack_shell_is_syntax_valid() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", "-n", str(_SCRIPT)],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr


def test_operator_command_pack_help_documents_db_free_scope() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--help"],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = cp.stdout
    assert "prepare_tenant_import_rehearsal_operator_commands.sh" in out
    assert "only if the precheck passes" in out
    assert "--env-file" in out
    assert "does not print database URL values" in out
    assert "authorize cutover" in out


def test_operator_command_pack_writes_commands_after_green_precheck(tmp_path: Path) -> None:
    implementation_packet_json = _write_green_packet(tmp_path)
    artifact_prefix = tmp_path / "tenant_acme"
    implementation_packet_json.rename(
        tmp_path / "tenant_acme_importer_implementation_packet.json"
    )
    output_path = tmp_path / "operator" / "commands.sh"
    env = os.environ.copy()
    env["SRC_DB_URL"] = "postgresql://user:secret@example.com/source"
    env["TGT_DB_URL"] = "postgresql://user:secret@example.com/target"

    cp = subprocess.run(  # noqa: S603,S607
        [
            "bash",
            str(_SCRIPT),
            "--artifact-prefix",
            str(artifact_prefix),
            "--output",
            str(output_path),
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
    assert output_path.is_file()
    commands = output_path.read_text()
    assert "scripts/generate_tenant_import_rehearsal_env_template.sh" in commands
    assert "scripts/precheck_tenant_import_rehearsal_env_file.sh" in commands
    assert "scripts/run_tenant_import_operator_launchpack.sh" in commands
    assert "python -m yuantus.scripts.tenant_import_rehearsal" in commands
    assert "--source-url \"$SRC_DB_URL\"" in commands
    assert "--target-url \"$TGT_DB_URL\"" in commands
    assert "postgresql://" not in cp.stdout
    assert "secret" not in cp.stdout
    assert "postgresql://" not in commands
    assert "user:secret@example.com" not in commands
    assert "Ready for cutover: false" in cp.stdout


def test_operator_command_pack_accepts_env_file_without_preexported_dsn_vars(
    tmp_path: Path,
) -> None:
    implementation_packet_json = _write_green_packet(tmp_path)
    artifact_prefix = tmp_path / "tenant_acme"
    implementation_packet_json.rename(
        tmp_path / "tenant_acme_importer_implementation_packet.json"
    )
    output_path = tmp_path / "operator" / "commands.sh"
    env_file = tmp_path / "tenant-import-rehearsal.env"
    env_file.write_text(
        "\n".join(
            [
                "SOURCE_DATABASE_URL='postgresql://user:secret@example.com/source'",
                "TARGET_DATABASE_URL='postgresql://user:secret@example.com/target'",
                "",
            ]
        )
    )
    env = os.environ.copy()
    env.pop("SOURCE_DATABASE_URL", None)
    env.pop("TARGET_DATABASE_URL", None)

    cp = subprocess.run(  # noqa: S603,S607
        [
            "bash",
            str(_SCRIPT),
            "--artifact-prefix",
            str(artifact_prefix),
            "--output",
            str(output_path),
            "--env-file",
            str(env_file),
        ],
        cwd=_REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    commands = output_path.read_text()
    assert f'--env-file "{env_file}"' in commands
    assert f'. "{env_file}"' in commands
    assert "postgresql://" not in cp.stdout
    assert "secret" not in cp.stdout
    assert "postgresql://" not in commands
    assert "user:secret@example.com" not in commands


def test_operator_command_pack_does_not_write_commands_when_precheck_fails(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "operator" / "commands.sh"
    env = os.environ.copy()
    env.pop("SRC_DB_URL", None)
    env.pop("TGT_DB_URL", None)

    cp = subprocess.run(  # noqa: S603,S607
        [
            "bash",
            str(_SCRIPT),
            "--artifact-prefix",
            str(tmp_path / "tenant_acme"),
            "--output",
            str(output_path),
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

    assert cp.returncode == 2
    assert not output_path.exists()
    assert "SRC_DB_URL is not set" in cp.stderr


def test_operator_command_pack_preserves_db_free_scope() -> None:
    source = _SCRIPT.read_text()

    assert "precheck_tenant_import_rehearsal_operator.sh" in source
    assert "print_tenant_import_rehearsal_commands.sh" in source
    assert "psql" not in source
    assert "TENANCY_MODE" not in source
    assert "curl " not in source
    assert "gh " not in source
