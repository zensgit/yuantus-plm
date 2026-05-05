from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from yuantus.scripts import tenant_import_rehearsal as rehearsal
from yuantus.scripts import tenant_import_rehearsal_evidence as evidence
from yuantus.scripts import tenant_import_rehearsal_evidence_template as template
from yuantus.scripts import tenant_import_rehearsal_operator_launchpack as launchpack
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
_SCRIPT = _REPO_ROOT / "scripts" / "run_tenant_import_rehearsal_operator_sequence.sh"


def _fake_python(path: Path) -> Path:
    script = path / "fake-python"
    script.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "-" ]]; then
  exit 0
fi
if [[ "${1:-}" != "-m" ]]; then
  echo "unexpected python invocation: $*" >&2
  exit 2
fi
module="$2"
shift 2
out_json=""
out_md=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-json)
      out_json="$2"
      shift 2
      ;;
    --output-md)
      out_md="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done
mkdir -p "$(dirname "$out_json")" "$(dirname "$out_md")"
case "$module" in
  yuantus.scripts.tenant_import_rehearsal_operator_launchpack)
    printf '{"schema_version":"p3.4.2-operator-launchpack-v1","ready_for_operator_launchpack":true,"ready_for_cutover":false,"outputs":{},"blockers":[]}\n' > "$out_json"
    printf 'Ready for operator launchpack: `true`\nReady for cutover: `false`\n' > "$out_md"
    ;;
  yuantus.scripts.tenant_import_rehearsal)
    printf '{"schema_version":"p3.4.2-tenant-import-rehearsal-v1","ready_for_rehearsal_import":true,"import_executed":true,"db_connection_attempted":true,"ready_for_cutover":false,"blockers":[],"table_results":[{"table":"meta_items","source_rows_expected":1,"target_rows_inserted":1,"row_count_matches":true}]}\n' > "$out_json"
    printf 'Rehearsal import passed: `true`\nReady for cutover: `false`\n' > "$out_md"
    ;;
  yuantus.scripts.tenant_import_rehearsal_evidence_template)
    printf '{"schema_version":"p3.4.2-operator-evidence-template-v1","ready_for_operator_evidence_template":true,"ready_for_cutover":false,"blockers":[]}\n' > "$out_json"
    printf 'Ready for cutover: `false`\n' > "$out_md"
    ;;
  yuantus.scripts.tenant_import_rehearsal_evidence)
    printf '{"schema_version":"p3.4.2-tenant-import-rehearsal-evidence-v1","ready_for_rehearsal_evidence":true,"operator_rehearsal_evidence_accepted":true,"ready_for_cutover":false,"blockers":[]}\n' > "$out_json"
    printf 'Rehearsal evidence accepted: `true`\nReady for cutover: `false`\n' > "$out_md"
    ;;
  *)
    echo "unexpected module: $module" >&2
    exit 2
    ;;
esac
"""
    )
    script.chmod(0o755)
    return script


def test_operator_sequence_shell_is_syntax_valid() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", "-n", str(_SCRIPT)],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr


def test_operator_sequence_help_documents_real_row_copy_scope() -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(_SCRIPT), "--help"],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = cp.stdout
    assert "run_tenant_import_rehearsal_operator_sequence.sh" in out
    assert "executes the real row-copy rehearsal" in out
    assert "does not print database URL values" in out
    assert "authorize cutover" in out


def test_operator_sequence_requires_explicit_confirm(tmp_path: Path) -> None:
    implementation_packet_json = _write_green_packet(tmp_path)
    env = os.environ.copy()
    env["SOURCE_DATABASE_URL"] = "postgresql://user:secret@example.com/source"
    env["TARGET_DATABASE_URL"] = "postgresql://user:secret@example.com/target"

    cp = subprocess.run(  # noqa: S603,S607
        [
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
        ],
        cwd=_REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 2
    assert "--confirm-rehearsal is required" in cp.stderr


def test_operator_sequence_runs_ordered_chain_with_fake_python(tmp_path: Path) -> None:
    implementation_packet_json = _write_green_packet(tmp_path)
    artifact_prefix = tmp_path / "tenant_acme"
    implementation_packet_json.rename(
        tmp_path / "tenant_acme_importer_implementation_packet.json"
    )
    env = os.environ.copy()
    env["PYTHON"] = str(_fake_python(tmp_path))
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
        ],
        cwd=_REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    for suffix in (
        "_operator_launchpack.json",
        "_import_rehearsal.json",
        "_operator_rehearsal_evidence_template.json",
        "_import_rehearsal_evidence.json",
    ):
        assert (tmp_path / f"tenant_acme{suffix}").is_file()
    evidence_payload = json.loads(
        (tmp_path / "tenant_acme_import_rehearsal_evidence.json").read_text()
    )
    assert evidence_payload["ready_for_rehearsal_evidence"] is True
    assert evidence_payload["ready_for_cutover"] is False
    assert "Ready for evidence closeout: true" in cp.stdout
    assert "Ready for cutover: false" in cp.stdout
    assert "postgresql://" not in cp.stdout
    assert "secret" not in cp.stdout


def test_operator_sequence_preserves_cutover_and_closeout_boundaries() -> None:
    source = _SCRIPT.read_text()

    assert "precheck_tenant_import_rehearsal_operator.sh" in source
    assert "run_tenant_import_operator_launchpack.sh" in source
    assert "tenant_import_rehearsal" in source
    assert "tenant_import_rehearsal_evidence_template" in source
    assert "precheck_tenant_import_rehearsal_evidence.sh" in source
    assert "run_tenant_import_evidence_closeout.sh" not in source
    assert "tenant_import_rehearsal_reviewer_packet" not in source
    assert "TENANCY_MODE" not in source
    assert "gh pr" not in source
    assert "curl " not in source
