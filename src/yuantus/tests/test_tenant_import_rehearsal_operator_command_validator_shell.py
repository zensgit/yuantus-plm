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


def _replace_one(command_file: Path, old: str, new: str) -> None:
    text = command_file.read_text()
    assert old in text
    command_file.write_text(text.replace(old, new, 1))


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
    assert "Ordered command sequence: true" in cp.stdout
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


def test_command_validator_rejects_out_of_order_required_step(tmp_path: Path) -> None:
    command_file = _write_generated_command_file(tmp_path)
    text = command_file.read_text()
    launchpack_start = text.index("scripts/run_tenant_import_operator_launchpack.sh")
    row_copy_start = text.index("PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal")
    launchpack_block = text[launchpack_start:row_copy_start]
    text_without_launchpack = text[:launchpack_start] + text[row_copy_start:]
    evidence_template_start = text_without_launchpack.index(
        "PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_evidence_template"
    )
    command_file.write_text(
        text_without_launchpack[:evidence_template_start]
        + launchpack_block
        + text_without_launchpack[evidence_template_start:]
    )

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--command-file", str(command_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert "command step out of order" in cp.stdout
    assert "row-copy rehearsal must appear after operator launchpack" in cp.stdout


def test_command_validator_requires_env_var_url_references(tmp_path: Path) -> None:
    command_file = _write_generated_command_file(tmp_path)
    text = command_file.read_text().replace(
        '--source-url "$SOURCE_DATABASE_URL"',
        "--source-url output/source.txt",
    )
    command_file.write_text(text)

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--command-file", str(command_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert 'missing required command pattern: --source-url "$' in cp.stdout


def test_command_validator_rejects_invalid_env_var_url_reference(tmp_path: Path) -> None:
    command_file = _write_generated_command_file(tmp_path)
    text = command_file.read_text().replace(
        '--target-url "$TARGET_DATABASE_URL"',
        '--target-url "$TARGET-DATABASE-URL"',
    )
    command_file.write_text(text)

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--command-file", str(command_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert "invalid --target-url environment variable reference" in cp.stdout
    assert "expected quoted uppercase env var reference" in cp.stdout


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


def test_command_validator_rejects_env_var_printing(tmp_path: Path) -> None:
    command_file = _write_generated_command_file(tmp_path)
    command_file.write_text(command_file.read_text() + '\necho "$SOURCE_DATABASE_URL"\n')

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--command-file", str(command_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert 'forbidden command pattern present: echo "$' in cp.stdout


def test_command_validator_rejects_extra_rm_command_without_echoing_line(
    tmp_path: Path,
) -> None:
    command_file = _write_generated_command_file(tmp_path)
    command_file.write_text(command_file.read_text() + "\nrm -rf output\n")

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--command-file", str(command_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert "unsupported command line" in cp.stdout
    assert "only generated tenant import commands are allowed" in cp.stdout
    assert "rm -rf" not in cp.stdout


def test_command_validator_rejects_extra_python_command_without_echoing_secret(
    tmp_path: Path,
) -> None:
    command_file = _write_generated_command_file(tmp_path)
    command_file.write_text(
        command_file.read_text()
        + "\npython -c 'print(\"postgresql://user:secret@example.com/source\")'\n"
    )

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--command-file", str(command_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert "unsupported command line" in cp.stdout
    assert "python -c" not in cp.stdout
    assert "secret" not in cp.stdout


def test_command_validator_rejects_redirection_in_path_option_without_echoing_value(
    tmp_path: Path,
) -> None:
    command_file = _write_generated_command_file(tmp_path)
    _replace_one(
        command_file,
        f"--output-json {tmp_path / 'tenant_acme_import_rehearsal.json'} \\",
        f"--output-json {tmp_path / 'tenant_acme_import_rehearsal.json'}>output/leak \\",
    )

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--command-file", str(command_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert "unsupported option line" in cp.stdout
    assert "generated command step: row_copy" in cp.stdout
    assert ">output/leak" not in cp.stdout


def test_command_validator_rejects_input_redirection_in_path_option_without_echoing_value(
    tmp_path: Path,
) -> None:
    command_file = _write_generated_command_file(tmp_path)
    _replace_one(
        command_file,
        f"--artifact-prefix {tmp_path / 'tenant_acme'}\n",
        f"--artifact-prefix {tmp_path / 'tenant_acme'}<input\n",
    )

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--command-file", str(command_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert "unsupported option line" in cp.stdout
    assert "generated command step: evidence_closeout" in cp.stdout
    assert "<input" not in cp.stdout


def test_command_validator_rejects_dollar_expansion_in_path_option_without_echoing_value(
    tmp_path: Path,
) -> None:
    command_file = _write_generated_command_file(tmp_path)
    _replace_one(
        command_file,
        f"--operator-packet-json {tmp_path / 'tenant_acme_operator_execution_packet.json'} \\",
        "--operator-packet-json $HOME/output.json \\",
    )

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--command-file", str(command_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert "unsupported option line" in cp.stdout
    assert "generated command step: launchpack" in cp.stdout
    assert "$HOME" not in cp.stdout


def test_command_validator_rejects_quoted_path_option_without_echoing_value(
    tmp_path: Path,
) -> None:
    command_file = _write_generated_command_file(tmp_path)
    _replace_one(
        command_file,
        f"--output-md {tmp_path / 'tenant_acme_import_rehearsal_evidence.md'} \\",
        '--output-md "output/hijack.md" \\',
    )

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--command-file", str(command_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert "unsupported option line" in cp.stdout
    assert "generated command step: evidence_gate" in cp.stdout
    assert '"output/hijack.md"' not in cp.stdout


def test_command_validator_rejects_variable_expansion_in_metadata_without_echoing_value(
    tmp_path: Path,
) -> None:
    command_file = _write_generated_command_file(tmp_path)
    _replace_one(
        command_file,
        '--backup-restore-owner "<owner>" \\',
        '--backup-restore-owner "$SOURCE_DATABASE_URL" \\',
    )

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--command-file", str(command_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert "unsupported option line" in cp.stdout
    assert "generated command step: evidence_template" in cp.stdout
    assert "SOURCE_DATABASE_URL" not in cp.stdout


def test_command_validator_rejects_backslash_escape_in_metadata_without_echoing_value(
    tmp_path: Path,
) -> None:
    command_file = _write_generated_command_file(tmp_path)
    _replace_one(
        command_file,
        '--evidence-reviewer "<reviewer>" \\',
        r'--evidence-reviewer "ops\reviewer" \\',
    )

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--command-file", str(command_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert "unsupported option line" in cp.stdout
    assert "generated command step: evidence_template" in cp.stdout
    assert r"ops\reviewer" not in cp.stdout


def test_command_validator_rejects_extra_export_command(tmp_path: Path) -> None:
    command_file = _write_generated_command_file(tmp_path)
    command_file.write_text(command_file.read_text() + "\nexport PATH=/tmp/blocked\n")

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--command-file", str(command_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert "unsupported command line" in cp.stdout
    assert "export PATH" not in cp.stdout


def test_command_validator_rejects_shell_control_syntax_without_echoing_line(
    tmp_path: Path,
) -> None:
    command_file = _write_generated_command_file(tmp_path)
    command_file.write_text(command_file.read_text() + "\ntouch output/a; rm output/a\n")

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--command-file", str(command_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert "forbidden shell control syntax on line" in cp.stdout
    assert "touch output" not in cp.stdout
    assert "rm output" not in cp.stdout


def test_command_validator_rejects_unknown_option_in_command_block(
    tmp_path: Path,
) -> None:
    command_file = _write_generated_command_file(tmp_path)
    text = command_file.read_text().replace(
        '  --target-url "$TARGET_DATABASE_URL" \\',
        '  --target-url "$TARGET_DATABASE_URL" \\\n  --confirm-cutover \\',
    )
    command_file.write_text(text)

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--command-file", str(command_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert "unsupported option line" in cp.stdout
    assert "generated command step: row_copy" in cp.stdout
    assert "--confirm-cutover" not in cp.stdout


def test_command_validator_rejects_option_in_wrong_command_block(
    tmp_path: Path,
) -> None:
    command_file = _write_generated_command_file(tmp_path)
    text = command_file.read_text().replace(
        '  --source-url-env SOURCE_DATABASE_URL \\',
        '  --source-url-env SOURCE_DATABASE_URL \\\n  --output-json output/hijack.json \\',
    )
    command_file.write_text(text)

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--command-file", str(command_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert "unsupported option line" in cp.stdout
    assert "generated command step: env_precheck" in cp.stdout
    assert "output/hijack.json" not in cp.stdout


def test_command_validator_rejects_orphan_option_line(tmp_path: Path) -> None:
    command_file = _write_generated_command_file(tmp_path)
    command_file.write_text(command_file.read_text() + "\n--strict\n")

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--command-file", str(command_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert "unsupported option line" in cp.stdout
    assert "outside generated command step" in cp.stdout


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


def test_command_validator_redacts_shell_syntax_error_details(tmp_path: Path) -> None:
    command_file = _write_generated_command_file(tmp_path)
    command_file.write_text(
        command_file.read_text()
        + "\npython -c print(postgresql://user:secret@example.com/source)\n"
    )

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--command-file", str(command_file)],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 1
    assert "shell syntax failed" in cp.stdout
    assert "shell syntax details hidden: true" in cp.stdout
    assert "python -c print" not in cp.stdout
    assert "postgresql://user" not in cp.stdout
    assert "secret" not in cp.stdout
