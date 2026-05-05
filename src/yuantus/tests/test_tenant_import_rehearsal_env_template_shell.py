from __future__ import annotations

import os
import stat
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
_SCRIPT = _REPO_ROOT / "scripts" / "generate_tenant_import_rehearsal_env_template.sh"


def test_env_template_shell_is_syntax_valid() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", "-n", str(_SCRIPT)],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr


def test_env_template_help_documents_scope() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--help"],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = cp.stdout
    assert "generate_tenant_import_rehearsal_env_template.sh" in out
    assert "--out PATH" in out
    assert "--force" in out
    assert "placeholders only" in out
    assert "does not print database URL values" in out


def test_env_template_generates_0600_repo_external_placeholder_file(tmp_path: Path) -> None:
    out = tmp_path / "tenant-import-rehearsal.env"

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--out", str(out)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    text = out.read_text()
    assert "SOURCE_DATABASE_URL='postgresql://source-user:REPLACE_ME@source-host/source-db'" in text
    assert "TARGET_DATABASE_URL='postgresql://target-user:REPLACE_ME@target-host/target-db'" in text
    assert "Do not commit" in text
    assert stat.S_IMODE(out.stat().st_mode) == 0o600
    assert "postgresql://" not in cp.stdout
    assert "REPLACE_ME" in cp.stdout


def test_env_template_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    out = tmp_path / "tenant-import-rehearsal.env"
    out.write_text("SOURCE_DATABASE_URL='keep-me'\n")

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--out", str(out)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 2
    assert "output already exists" in cp.stderr
    assert out.read_text() == "SOURCE_DATABASE_URL='keep-me'\n"


def test_env_template_force_overwrites_existing_file(tmp_path: Path) -> None:
    out = tmp_path / "tenant-import-rehearsal.env"
    out.write_text("SOURCE_DATABASE_URL='old'\n")
    os.chmod(out, 0o644)

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--out", str(out), "--force"],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    text = out.read_text()
    assert "SOURCE_DATABASE_URL='old'" not in text
    assert "SOURCE_DATABASE_URL='postgresql://source-user:REPLACE_ME@source-host/source-db'" in text
    assert stat.S_IMODE(out.stat().st_mode) == 0o600
