from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from yuantus.tests.test_tenant_import_rehearsal_operator_packet import _write_green_packet
from yuantus.tests.test_tenant_import_rehearsal_operator_sequence_shell import _fake_python


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
_SCRIPT = _REPO_ROOT / "scripts" / "run_tenant_import_rehearsal_full_closeout.sh"


def _full_fake_python(path: Path) -> Path:
    script = _fake_python(path)
    text = script.read_text()
    text = text.replace(
        '  *)\n    echo "unexpected module: $module" >&2\n    exit 2\n    ;;\n',
        """  yuantus.scripts.tenant_import_rehearsal_evidence_archive)
    printf '{"schema_version":"p3.4.2-evidence-archive-v1","ready_for_archive":true,"ready_for_cutover":false,"artifacts":[],"blockers":[]}\n' > "$out_json"
    printf 'Ready for archive: `true`\nReady for cutover: `false`\n' > "$out_md"
    ;;
  yuantus.scripts.tenant_import_rehearsal_redaction_guard)
    printf '{"schema_version":"p3.4.2-redaction-guard-v1","ready_for_artifact_handoff":true,"ready_for_cutover":false,"blockers":[]}\n' > "$out_json"
    printf 'Ready for artifact handoff: `true`\nReady for cutover: `false`\n' > "$out_md"
    ;;
  yuantus.scripts.tenant_import_rehearsal_evidence_handoff)
    printf '{"schema_version":"p3.4.2-evidence-handoff-v1","ready_for_evidence_handoff":true,"ready_for_cutover":false,"blockers":[]}\n' > "$out_json"
    printf 'Ready for evidence handoff: `true`\nReady for cutover: `false`\n' > "$out_md"
    ;;
  yuantus.scripts.tenant_import_rehearsal_evidence_intake)
    printf '{"schema_version":"p3.4.2-evidence-intake-v1","ready_for_evidence_intake":true,"ready_for_cutover":false,"blockers":[]}\n' > "$out_json"
    printf 'Ready for evidence intake: `true`\nReady for cutover: `false`\n' > "$out_md"
    ;;
  yuantus.scripts.tenant_import_rehearsal_reviewer_packet)
    printf '{"schema_version":"p3.4.2-reviewer-packet-v1","ready_for_reviewer_packet":true,"ready_for_cutover":false,"blockers":[]}\n' > "$out_json"
    printf 'Ready for reviewer packet: `true`\nReady for cutover: `false`\n' > "$out_md"
    ;;
  *)
    echo "unexpected module: $module" >&2
    exit 2
    ;;
""",
    )
    script.write_text(text)
    return script


def test_full_closeout_shell_is_syntax_valid() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", "-n", str(_SCRIPT)],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr


def test_full_closeout_help_documents_confirmation_and_scope() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--help"],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = cp.stdout
    assert "run_tenant_import_rehearsal_full_closeout.sh" in out
    assert "--confirm-rehearsal" in out
    assert "--confirm-closeout" in out
    assert "--env-file" in out
    assert "$HOME/.config/yuantus/tenant-import-rehearsal.env" in out
    assert "does not print database URL values" in out
    assert "authorize cutover" in out


def test_full_closeout_requires_both_confirmations(tmp_path: Path) -> None:
    implementation_packet_json = _write_green_packet(tmp_path)
    env = os.environ.copy()
    env["SOURCE_DATABASE_URL"] = "postgresql://user:secret@example.com/source"
    env["TARGET_DATABASE_URL"] = "postgresql://user:secret@example.com/target"

    base_args = [
        "bash",
        str(_SCRIPT),
        "--implementation-packet-json",
        str(implementation_packet_json),
        "--artifact-prefix",
        str(tmp_path / "tenant_acme"),
        "--backup-restore-owner",
        "Ops Owner",
        "--rehearsal-window",
        "2026-05-05T10:00:00Z/2026-05-05T12:00:00Z",
        "--rehearsal-executed-by",
        "Operator",
        "--evidence-reviewer",
        "Reviewer",
        "--date",
        "2026-05-05",
    ]

    missing_rehearsal = subprocess.run(  # noqa: S603,S607
        base_args + ["--confirm-closeout"],
        cwd=_REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )
    assert missing_rehearsal.returncode == 2
    assert "--confirm-rehearsal is required" in missing_rehearsal.stderr

    missing_closeout = subprocess.run(  # noqa: S603,S607
        base_args + ["--confirm-rehearsal"],
        cwd=_REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )
    assert missing_closeout.returncode == 2
    assert "--confirm-closeout is required" in missing_closeout.stderr


def test_full_closeout_runs_sequence_and_closeout_with_fake_python(tmp_path: Path) -> None:
    implementation_packet_json = _write_green_packet(tmp_path)
    implementation_packet_json.rename(
        tmp_path / "tenant_acme_importer_implementation_packet.json"
    )
    artifact_prefix = tmp_path / "tenant_acme"
    env = os.environ.copy()
    env["PYTHON"] = str(_full_fake_python(tmp_path))
    env["SOURCE_DATABASE_URL"] = "postgresql://user:secret@example.com/source"
    env["TARGET_DATABASE_URL"] = "postgresql://user:secret@example.com/target"

    cp = subprocess.run(  # noqa: S603,S607
        [
            "bash",
            str(_SCRIPT),
            "--implementation-packet-json",
            str(tmp_path / "tenant_acme_importer_implementation_packet.json"),
            "--artifact-prefix",
            str(artifact_prefix),
            "--backup-restore-owner",
            "Ops Owner",
            "--rehearsal-window",
            "2026-05-05T10:00:00Z/2026-05-05T12:00:00Z",
            "--rehearsal-executed-by",
            "Operator",
            "--evidence-reviewer",
            "Reviewer",
            "--date",
            "2026-05-05",
            "--confirm-rehearsal",
            "--confirm-closeout",
        ],
        cwd=_REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    reviewer_packet = json.loads((tmp_path / "tenant_acme_reviewer_packet.json").read_text())
    assert reviewer_packet["ready_for_reviewer_packet"] is True
    assert reviewer_packet["ready_for_cutover"] is False
    assert (tmp_path / "tenant_acme_import_rehearsal_evidence_archive.json").is_file()
    assert (tmp_path / "tenant_acme_redaction_guard.json").is_file()
    assert (tmp_path / "tenant_acme_evidence_handoff.json").is_file()
    assert (tmp_path / "tenant_acme_evidence_intake.json").is_file()
    assert "Ready for reviewer packet: true" in cp.stdout
    assert "Ready for cutover: false" in cp.stdout
    assert "postgresql://" not in cp.stdout
    assert "secret" not in cp.stdout


def test_full_closeout_can_load_dsn_env_file_without_printing_values(
    tmp_path: Path,
) -> None:
    implementation_packet_json = _write_green_packet(tmp_path)
    implementation_packet_json.rename(
        tmp_path / "tenant_acme_importer_implementation_packet.json"
    )
    artifact_prefix = tmp_path / "tenant_acme"
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
    env["PYTHON"] = str(_full_fake_python(tmp_path))
    env.pop("SOURCE_DATABASE_URL", None)
    env.pop("TARGET_DATABASE_URL", None)

    cp = subprocess.run(  # noqa: S603,S607
        [
            "bash",
            str(_SCRIPT),
            "--implementation-packet-json",
            str(tmp_path / "tenant_acme_importer_implementation_packet.json"),
            "--artifact-prefix",
            str(artifact_prefix),
            "--backup-restore-owner",
            "Ops Owner",
            "--rehearsal-window",
            "2026-05-05T10:00:00Z/2026-05-05T12:00:00Z",
            "--rehearsal-executed-by",
            "Operator",
            "--evidence-reviewer",
            "Reviewer",
            "--date",
            "2026-05-05",
            "--env-file",
            str(env_file),
            "--confirm-rehearsal",
            "--confirm-closeout",
        ],
        cwd=_REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    reviewer_packet = json.loads((tmp_path / "tenant_acme_reviewer_packet.json").read_text())
    assert reviewer_packet["ready_for_reviewer_packet"] is True
    assert reviewer_packet["ready_for_cutover"] is False
    assert "postgresql://" not in cp.stdout
    assert "secret" not in cp.stdout


def test_full_closeout_rejects_unsafe_env_file_before_source(
    tmp_path: Path,
) -> None:
    implementation_packet_json = _write_green_packet(tmp_path)
    implementation_packet_json.rename(
        tmp_path / "tenant_acme_importer_implementation_packet.json"
    )
    artifact_prefix = tmp_path / "tenant_acme"
    marker = tmp_path / "env-file-command-executed"
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
    env = os.environ.copy()
    env["PYTHON"] = str(_full_fake_python(tmp_path))
    env.pop("SOURCE_DATABASE_URL", None)
    env.pop("TARGET_DATABASE_URL", None)

    cp = subprocess.run(  # noqa: S603,S607
        [
            "bash",
            str(_SCRIPT),
            "--implementation-packet-json",
            str(tmp_path / "tenant_acme_importer_implementation_packet.json"),
            "--artifact-prefix",
            str(artifact_prefix),
            "--backup-restore-owner",
            "Ops Owner",
            "--rehearsal-window",
            "2026-05-05T10:00:00Z/2026-05-05T12:00:00Z",
            "--rehearsal-executed-by",
            "Operator",
            "--evidence-reviewer",
            "Reviewer",
            "--date",
            "2026-05-05",
            "--env-file",
            str(env_file),
            "--confirm-rehearsal",
            "--confirm-closeout",
        ],
        cwd=_REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 2
    assert "contains shell expansion syntax" in cp.stderr
    assert not marker.exists()
    assert not (tmp_path / "tenant_acme_reviewer_packet.json").exists()
    assert "postgresql://" not in cp.stdout
    assert "postgresql://" not in cp.stderr
    assert "secret" not in cp.stdout
    assert "secret" not in cp.stderr


def test_full_closeout_rejects_invalid_variable_name_before_env_file_source(
    tmp_path: Path,
) -> None:
    implementation_packet_json = _write_green_packet(tmp_path)
    implementation_packet_json.rename(
        tmp_path / "tenant_acme_importer_implementation_packet.json"
    )
    artifact_prefix = tmp_path / "tenant_acme"
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
    env = os.environ.copy()
    env["PYTHON"] = str(_full_fake_python(tmp_path))

    cp = subprocess.run(  # noqa: S603,S607
        [
            "bash",
            str(_SCRIPT),
            "--implementation-packet-json",
            str(tmp_path / "tenant_acme_importer_implementation_packet.json"),
            "--artifact-prefix",
            str(artifact_prefix),
            "--backup-restore-owner",
            "Ops Owner",
            "--rehearsal-window",
            "2026-05-05T10:00:00Z/2026-05-05T12:00:00Z",
            "--rehearsal-executed-by",
            "Operator",
            "--evidence-reviewer",
            "Reviewer",
            "--date",
            "2026-05-05",
            "--env-file",
            str(env_file),
            "--source-url-env",
            "SOURCE DATABASE URL",
            "--confirm-rehearsal",
            "--confirm-closeout",
        ],
        cwd=_REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 2
    assert "--source-url-env must be an uppercase shell environment variable name" in cp.stderr
    assert not marker.exists()
    assert not (tmp_path / "tenant_acme_reviewer_packet.json").exists()
    assert "postgresql://" not in cp.stdout
    assert "secret" not in cp.stdout


def test_full_closeout_preserves_scope_boundaries() -> None:
    source = _SCRIPT.read_text()

    assert "run_tenant_import_rehearsal_operator_sequence.sh" in source
    assert "run_tenant_import_evidence_closeout.sh" in source
    assert "confirm_rehearsal" in source
    assert "confirm_closeout" in source
    assert "TENANCY_MODE" not in source
    assert "gh pr" not in source
    assert "curl " not in source
