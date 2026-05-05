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
_SCRIPT = _REPO_ROOT / "scripts" / "print_tenant_import_rehearsal_commands.sh"


def test_command_printer_is_syntax_valid() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", "-n", str(_SCRIPT)],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr


def test_command_printer_help_documents_print_only_scope() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--help"],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = cp.stdout
    assert "print_tenant_import_rehearsal_commands.sh" in out
    assert "prints commands only" in out
    assert "--env-file PATH" in out
    assert "does not execute them" in out
    assert "cutover" in out


def test_command_printer_outputs_full_operator_sequence_without_secret_values() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        [
            "bash",
            str(_SCRIPT),
            "--artifact-prefix",
            "output/tenant_acme",
            "--source-url-env",
            "SRC_DB_URL",
            "--target-url-env",
            "TGT_DB_URL",
        ],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = cp.stdout
    assert "scripts/generate_tenant_import_rehearsal_env_template.sh" in out
    assert "scripts/precheck_tenant_import_rehearsal_env_file.sh" in out
    assert 'set -a\n. "$HOME/.config/yuantus/tenant-import-rehearsal.env"\nset +a' in out
    assert "scripts/run_tenant_import_operator_launchpack.sh" in out
    assert "python -m yuantus.scripts.tenant_import_rehearsal" in out
    assert "python -m yuantus.scripts.tenant_import_rehearsal_evidence_template" in out
    assert "python -m yuantus.scripts.tenant_import_rehearsal_evidence" in out
    assert "scripts/run_tenant_import_evidence_closeout.sh" in out
    assert "--source-url \"$SRC_DB_URL\"" in out
    assert "--target-url \"$TGT_DB_URL\"" in out
    assert "postgresql://" not in out
    assert "password" not in out.lower()
    assert "ready_for_cutover=true" not in out


def test_command_printer_accepts_custom_env_file_path() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        [
            "bash",
            str(_SCRIPT),
            "--artifact-prefix",
            "output/tenant_acme",
            "--env-file",
            "/tmp/tenant-import.env",
        ],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = cp.stdout
    assert '--out "/tmp/tenant-import.env"' in out
    assert '--env-file "/tmp/tenant-import.env"' in out
    assert '. "/tmp/tenant-import.env"' in out


def test_command_printer_preserves_print_only_scope() -> None:
    source = _SCRIPT.read_text()

    assert "cat <<COMMANDS" in source
    assert "psql" not in source
    assert "TENANCY_MODE" not in source
    assert "gh " not in source
    assert "curl " not in source
