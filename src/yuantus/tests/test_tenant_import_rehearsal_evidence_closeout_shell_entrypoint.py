from __future__ import annotations

import json
import subprocess
from pathlib import Path

from yuantus.scripts import tenant_import_rehearsal_operator_packet as operator_packet
from yuantus.tests.tenant_import_shell_test_env import shell_test_env
from yuantus.tests.test_tenant_import_rehearsal_evidence_archive import _write_green_chain


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
_SCRIPT = _REPO_ROOT / "scripts" / "run_tenant_import_evidence_closeout.sh"
_TARGET_URL_REDACTED = "postgresql://user:***@example.com/rehearsal"


def _env() -> dict[str, str]:
    return shell_test_env(_REPO_ROOT)


def _write_text(path: Path, text: str) -> Path:
    path.write_text(text)
    return path


def _write_operator_packet(tmp_path: Path, *, prefix: Path, paths: dict[str, Path]) -> Path:
    payload = {
        "schema_version": operator_packet.SCHEMA_VERSION,
        "tenant_id": "Acme Prod",
        "target_schema": "yt_t_acme_prod",
        "target_url": _TARGET_URL_REDACTED,
        "ready_for_operator_execution": True,
        "ready_for_cutover": False,
        "outputs": {
            "rehearsal_json": str(paths["rehearsal_json"]),
            "rehearsal_md": str(_write_text(tmp_path / "rehearsal.md", "real rehearsal\n")),
            "operator_evidence_template_json": str(paths["operator_evidence_template_json"]),
            "operator_evidence_md": str(paths["operator_evidence_md"]),
            "evidence_json": str(paths["evidence_json"]),
            "evidence_md": str(_write_text(tmp_path / "evidence.md", "real evidence\n")),
            "archive_json": f"{prefix}_import_rehearsal_evidence_archive.json",
            "archive_md": f"{prefix}_import_rehearsal_evidence_archive.md",
        },
        "blockers": [],
    }
    path = tmp_path / "operator-packet.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def test_shell_entrypoint_is_syntax_valid() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", "-n", str(_SCRIPT)],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr


def test_shell_entrypoint_help_documents_closeout_only_scope() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--help"],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = cp.stdout
    assert "run_tenant_import_evidence_closeout.sh" in out
    assert "DB-free P3.4 evidence closeout chain" in out
    assert "does not run row-copy rehearsal" in out
    assert "does not accept or synthesize operator evidence" in out
    assert "does not authorize production cutover" in out


def test_shell_entrypoint_builds_evidence_closeout_chain(tmp_path: Path) -> None:
    paths = _write_green_chain(tmp_path)
    prefix = tmp_path / "tenant_acme"
    operator_packet_json = _write_operator_packet(tmp_path, prefix=prefix, paths=paths)

    cp = subprocess.run(  # noqa: S603,S607
        [
            "bash",
            str(_SCRIPT),
            "--evidence-json",
            str(paths["evidence_json"]),
            "--operator-packet-json",
            str(operator_packet_json),
            "--operator-evidence-template-json",
            str(paths["operator_evidence_template_json"]),
            "--artifact-prefix",
            str(prefix),
        ],
        cwd=_REPO_ROOT,
        env=_env(),
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    reviewer_packet = json.loads((tmp_path / "tenant_acme_reviewer_packet.json").read_text())
    intake = json.loads((tmp_path / "tenant_acme_evidence_intake.json").read_text())
    handoff = json.loads((tmp_path / "tenant_acme_evidence_handoff.json").read_text())
    archive = json.loads(
        (tmp_path / "tenant_acme_import_rehearsal_evidence_archive.json").read_text()
    )
    redaction = json.loads((tmp_path / "tenant_acme_redaction_guard.json").read_text())

    assert archive["ready_for_archive"] is True
    assert redaction["ready_for_artifact_handoff"] is True
    assert handoff["ready_for_evidence_handoff"] is True
    assert intake["ready_for_evidence_intake"] is True
    assert reviewer_packet["ready_for_reviewer_packet"] is True
    assert reviewer_packet["ready_for_cutover"] is False


def test_shell_entrypoint_preserves_evidence_closeout_only_scope() -> None:
    source = _SCRIPT.read_text()

    assert "tenant_import_rehearsal_evidence_archive" in source
    assert "tenant_import_rehearsal_reviewer_packet" in source
    assert "tenant_import_rehearsal --" not in source
    assert "confirm-rehearsal" not in source
    assert "psql" not in source
    assert "TENANCY_MODE" not in source
