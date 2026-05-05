from __future__ import annotations

import subprocess
from pathlib import Path


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
_SCRIPT = _REPO_ROOT / "scripts" / "validate_tenant_import_rehearsal_operator_commands.sh"
_PRINTER = _REPO_ROOT / "scripts" / "print_tenant_import_rehearsal_commands.sh"


def _write_generated_command_file(tmp_path: Path) -> Path:
    out = tmp_path / "operator_commands.sh"
    cp = subprocess.run(  # noqa: S603,S607
        [
            "bash",
            str(_PRINTER),
            "--artifact-prefix",
            str(tmp_path / "tenant_acme"),
            "--env-file",
            str(tmp_path / "tenant-import-rehearsal.env"),
        ],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out.write_text(cp.stdout)
    return out


def test_command_validator_shell_is_syntax_valid() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", "-n", str(_SCRIPT)],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr


def test_command_validator_help_documents_scope() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--help"],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = cp.stdout
    assert "validate_tenant_import_rehearsal_operator_commands.sh" in out
    assert "--command-file PATH" in out
    assert "without executing" in out
    assert "does not connect to databases" in out
    assert "does not print database URL values" in out


def test_command_validator_accepts_generated_command_file(tmp_path: Path) -> None:
    command_file = _write_generated_command_file(tmp_path)

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--command-file", str(command_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert "Ready for operator command execution: true" in cp.stdout
    assert "Ready for cutover: false" in cp.stdout
    assert "postgresql://" not in cp.stdout


def test_command_validator_rejects_missing_required_step(tmp_path: Path) -> None:
    command_file = _write_generated_command_file(tmp_path)
    text = command_file.read_text().replace(
        "scripts/precheck_tenant_import_rehearsal_env_file.sh",
        "scripts/missing_env_precheck.sh",
    )
    command_file.write_text(text)

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--command-file", str(command_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert "missing required command pattern" in cp.stdout
    assert "precheck_tenant_import_rehearsal_env_file.sh" in cp.stdout


def test_command_validator_rejects_database_url_literal(tmp_path: Path) -> None:
    command_file = _write_generated_command_file(tmp_path)
    command_file.write_text(
        command_file.read_text()
        + "\n# bad literal: postgresql://user:secret@example.com/source\n"
    )

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--command-file", str(command_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert "forbidden command pattern present: postgresql://" in cp.stdout
    assert "secret@example.com" not in cp.stdout


def test_command_validator_rejects_cutover_authorization(tmp_path: Path) -> None:
    command_file = _write_generated_command_file(tmp_path)
    command_file.write_text(command_file.read_text() + "\nready_for_cutover=true\n")

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--command-file", str(command_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert "forbidden command pattern present: ready_for_cutover=true" in cp.stdout


def test_command_validator_rejects_shell_syntax_error(tmp_path: Path) -> None:
    command_file = _write_generated_command_file(tmp_path)
    command_file.write_text(command_file.read_text() + "\nif true; then\n")

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--command-file", str(command_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert "shell syntax failed" in cp.stdout
