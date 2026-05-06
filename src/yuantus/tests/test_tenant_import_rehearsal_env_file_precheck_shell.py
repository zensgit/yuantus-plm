from __future__ import annotations

import os
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
_SCRIPT = _REPO_ROOT / "scripts" / "precheck_tenant_import_rehearsal_env_file.sh"


def test_env_file_precheck_shell_is_syntax_valid() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", "-n", str(_SCRIPT)],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr


def test_env_file_precheck_help_documents_scope() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--help"],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = cp.stdout
    assert "precheck_tenant_import_rehearsal_env_file.sh" in out
    assert "--env-file PATH" in out
    assert "--source-url-env NAME" in out
    assert "--target-url-env NAME" in out
    assert "static assignments for the selected" in out
    normalized_out = " ".join(out.split())
    assert "does not connect to any database" in normalized_out
    assert "does not print database URL values" in normalized_out


def test_env_file_precheck_rejects_unknown_cli_argument_without_echoing_value() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        [
            "bash",
            str(_SCRIPT),
            "--bad=postgresql://user:secret@example.com/source",
        ],
        text=True,
        capture_output=True,
    )

    combined = cp.stdout + cp.stderr
    assert cp.returncode == 2
    assert "unknown argument" in combined
    assert "argument value hidden: true" in combined
    assert "postgresql://user" not in combined
    assert "secret@example.com" not in combined


def test_env_file_precheck_rejects_missing_env_file_without_echoing_path(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "postgresql:" / "user:secret@example.com" / "source.env"

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--env-file", str(missing)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    combined = cp.stdout + cp.stderr
    assert cp.returncode == 2
    assert "--env-file does not exist" in combined
    assert "env-file path hidden: true" in combined
    assert "postgresql:" not in combined
    assert "secret" not in combined


def test_env_file_precheck_passes_without_printing_values(tmp_path: Path) -> None:
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

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--env-file", str(env_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert "P3.4 tenant import rehearsal env precheck passed" in cp.stdout
    assert "Source variable: SOURCE_DATABASE_URL" in cp.stdout
    assert "Target variable: TARGET_DATABASE_URL" in cp.stdout
    assert "Ready for row-copy command: true" in cp.stdout
    assert "Ready for cutover: false" in cp.stdout
    assert "postgresql://" not in cp.stdout
    assert "secret" not in cp.stdout


def test_env_file_precheck_fails_missing_env_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.env"

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--env-file", str(missing)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 2
    assert "--env-file does not exist" in cp.stderr


def test_env_file_precheck_fails_placeholders_without_printing_values(tmp_path: Path) -> None:
    env_file = tmp_path / "tenant-import-rehearsal.env"
    env_file.write_text(
        "\n".join(
            [
                "SOURCE_DATABASE_URL='postgresql://source-user:REPLACE_ME@source-host/source-db'",
                "TARGET_DATABASE_URL='postgresql://user:secret@example.com/target'",
                "",
            ]
        )
    )

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--env-file", str(env_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 2
    assert "SOURCE_DATABASE_URL still contains a placeholder value" in cp.stderr
    assert "postgresql://" not in cp.stdout
    assert "postgresql://" not in cp.stderr
    assert "secret" not in cp.stdout
    assert "secret" not in cp.stderr


def test_env_file_precheck_fails_missing_target_variable(tmp_path: Path) -> None:
    env_file = tmp_path / "tenant-import-rehearsal.env"
    env_file.write_text("SOURCE_DATABASE_URL='postgresql://user:secret@example.com/source'\n")

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--env-file", str(env_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 2
    assert "TARGET_DATABASE_URL is not set" in cp.stderr
    assert "secret" not in cp.stderr


def test_env_file_precheck_rejects_command_substitution_without_executing(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "command-substitution-executed"
    env_file = tmp_path / "tenant-import-rehearsal.env"
    env_file.write_text(
        "\n".join(
            [
                "SOURCE_DATABASE_URL='postgresql://user:secret@example.com/source'",
                f"TARGET_DATABASE_URL=$(touch {marker})",
                "",
            ]
        )
    )

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--env-file", str(env_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 2
    assert "env-file line 2 contains shell expansion syntax" in cp.stderr
    assert not marker.exists()
    assert "postgresql://" not in cp.stdout
    assert "postgresql://" not in cp.stderr
    assert "secret" not in cp.stdout
    assert "secret" not in cp.stderr


def test_env_file_precheck_rejects_non_assignment_lines_without_executing(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "bare-command-executed"
    env_file = tmp_path / "tenant-import-rehearsal.env"
    env_file.write_text(
        "\n".join(
            [
                "SOURCE_DATABASE_URL='postgresql://user:secret@example.com/source'",
                f"touch {marker}",
                "TARGET_DATABASE_URL='postgresql://user:secret@example.com/target'",
                "",
            ]
        )
    )

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--env-file", str(env_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 2
    assert "env-file line 2 must be a static uppercase KEY=VALUE assignment" in cp.stderr
    assert not marker.exists()
    assert "secret" not in cp.stdout
    assert "secret" not in cp.stderr


def test_env_file_precheck_rejects_double_quoted_values(tmp_path: Path) -> None:
    env_file = tmp_path / "tenant-import-rehearsal.env"
    env_file.write_text(
        "\n".join(
            [
                'SOURCE_DATABASE_URL="postgresql://user:secret@example.com/source"',
                "TARGET_DATABASE_URL='postgresql://user:secret@example.com/target'",
                "",
            ]
        )
    )

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--env-file", str(env_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 2
    assert "must use single quotes for values that require quoting" in cp.stderr
    assert "secret" not in cp.stdout
    assert "secret" not in cp.stderr


def test_env_file_precheck_supports_custom_variable_names(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["TENANT_SOURCE_URL"] = "postgresql://user:secret@example.com/source"
    env["TENANT_TARGET_URL"] = "postgresql://user:secret@example.com/target"

    cp = subprocess.run(  # noqa: S603,S607
        [
            "bash",
            str(_SCRIPT),
            "--source-url-env",
            "TENANT_SOURCE_URL",
            "--target-url-env",
            "TENANT_TARGET_URL",
        ],
        cwd=_REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert "Source variable: TENANT_SOURCE_URL" in cp.stdout
    assert "Target variable: TENANT_TARGET_URL" in cp.stdout
    assert "postgresql://" not in cp.stdout
    assert "secret" not in cp.stdout


def test_env_file_precheck_loads_custom_variable_names_from_env_file(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "tenant-import-rehearsal.env"
    env_file.write_text(
        "\n".join(
            [
                "TENANT_SOURCE_URL='postgresql://user:secret@example.com/source'",
                "TENANT_TARGET_URL='postgresql://user:secret@example.com/target'",
                "",
            ]
        )
    )
    env = os.environ.copy()
    env.pop("TENANT_SOURCE_URL", None)
    env.pop("TENANT_TARGET_URL", None)

    cp = subprocess.run(  # noqa: S603,S607
        [
            "bash",
            str(_SCRIPT),
            "--env-file",
            str(env_file),
            "--source-url-env",
            "TENANT_SOURCE_URL",
            "--target-url-env",
            "TENANT_TARGET_URL",
        ],
        cwd=_REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert "Source variable: TENANT_SOURCE_URL" in cp.stdout
    assert "Target variable: TENANT_TARGET_URL" in cp.stdout
    assert "postgresql://" not in cp.stdout
    assert "secret" not in cp.stdout


def test_env_file_precheck_rejects_extra_static_keys_before_source(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "tenant-import-rehearsal.env"
    env_file.write_text(
        "\n".join(
            [
                "SOURCE_DATABASE_URL='postgresql://user:secret@example.com/source'",
                "TARGET_DATABASE_URL='postgresql://user:secret@example.com/target'",
                "PATH='/tmp/blocked-path'",
                "PYTHON='/tmp/blocked-python'",
                "",
            ]
        )
    )
    env = os.environ.copy()
    env.pop("SOURCE_DATABASE_URL", None)
    env.pop("TARGET_DATABASE_URL", None)

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--env-file", str(env_file)],
        cwd=_REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 2
    assert "unsupported variable: PATH" in cp.stderr
    assert "may define only SOURCE_DATABASE_URL and TARGET_DATABASE_URL" in cp.stderr
    assert "postgresql://" not in cp.stdout
    assert "postgresql://" not in cp.stderr
    assert "secret" not in cp.stdout
    assert "secret" not in cp.stderr
    assert "command not found" not in cp.stderr


def test_env_file_precheck_rejects_default_keys_when_custom_names_selected(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "tenant-import-rehearsal.env"
    env_file.write_text(
        "\n".join(
            [
                "SOURCE_DATABASE_URL='postgresql://user:secret@example.com/source'",
                "TENANT_TARGET_URL='postgresql://user:secret@example.com/target'",
                "",
            ]
        )
    )

    cp = subprocess.run(  # noqa: S603,S607
        [
            "bash",
            str(_SCRIPT),
            "--env-file",
            str(env_file),
            "--source-url-env",
            "TENANT_SOURCE_URL",
            "--target-url-env",
            "TENANT_TARGET_URL",
        ],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 2
    assert "unsupported variable: SOURCE_DATABASE_URL" in cp.stderr
    assert "may define only TENANT_SOURCE_URL and TENANT_TARGET_URL" in cp.stderr
    assert "postgresql://" not in cp.stdout
    assert "postgresql://" not in cp.stderr
    assert "secret" not in cp.stdout
    assert "secret" not in cp.stderr


def test_env_file_precheck_rejects_invalid_variable_name_before_source(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "env-file-sourced"
    env_file = tmp_path / "tenant-import-rehearsal.env"
    env_file.write_text(
        "\n".join(
            [
                f"SOURCE_DATABASE_URL=$(touch {marker})",
                "TARGET_DATABASE_URL='postgresql://user:secret@example.com/target'",
                "",
            ]
        )
    )

    cp = subprocess.run(  # noqa: S603,S607
        [
            "bash",
            str(_SCRIPT),
            "--env-file",
            str(env_file),
            "--source-url-env",
            "SOURCE-DATABASE-URL",
        ],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 2
    assert (
        "--source-url-env must be an uppercase shell environment variable name "
        "([A-Z_][A-Z0-9_]*)"
    ) in cp.stderr
    assert not marker.exists()
    assert "postgresql://" not in cp.stdout
    assert "postgresql://" not in cp.stderr
    assert "secret" not in cp.stdout
    assert "secret" not in cp.stderr


def test_env_file_precheck_preserves_db_free_scope() -> None:
    source = _SCRIPT.read_text()

    assert "psql" not in source
    assert "curl " not in source
    assert "python -m" not in source
    assert "TENANCY_MODE" not in source
