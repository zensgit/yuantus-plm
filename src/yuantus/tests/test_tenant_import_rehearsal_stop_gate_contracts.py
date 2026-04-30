from __future__ import annotations

from pathlib import Path

from yuantus.scripts import tenant_import_rehearsal_synthetic_drill as drill


_ROOT = Path(__file__).resolve().parents[3]
_TODO = _ROOT / "docs" / "PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md"
_RUNBOOK = _ROOT / "docs" / "RUNBOOK_TENANT_MIGRATIONS_20260427.md"
_DESIGN = (
    _ROOT
    / "docs"
    / "DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_SYNTHETIC_DRILL_20260429.md"
)
_VERIFICATION = (
    _ROOT
    / "docs"
    / "DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_SYNTHETIC_DRILL_20260429.md"
)


def test_parent_todo_keeps_real_operator_evidence_unchecked_after_synthetic_drill():
    todo = _TODO.read_text()

    assert "- [x] Add synthetic operator drill for DB-free command-path rehearsal." in todo
    assert "- [ ] Add operator-run PostgreSQL rehearsal evidence." in todo
    assert "- [x] Add operator-run PostgreSQL rehearsal evidence." not in todo


def test_runbook_warns_synthetic_drill_is_not_operator_run_evidence():
    runbook = _RUNBOOK.read_text()

    handoff_pos = runbook.index("### 20.2 P3.4.2 Evidence Handoff Gate")
    synthetic_pos = runbook.index("### 20.5 P3.4.2 Synthetic Operator Drill")
    rollback_pos = runbook.index("## 21. Rollback")
    assert handoff_pos < synthetic_pos < rollback_pos
    assert "This output is not operator-run PostgreSQL rehearsal evidence." in runbook
    assert "do not mark the P3.4 stop gate complete from synthetic output" in runbook.replace(
        "\n",
        " ",
    )


def test_synthetic_drill_runtime_contract_keeps_real_gates_closed(tmp_path):
    report = drill.build_synthetic_drill_report(artifact_dir=tmp_path)

    assert report["synthetic_drill"] is True
    assert report["real_rehearsal_evidence"] is False
    assert report["db_connection_attempted"] is False
    assert report["ready_for_operator_evidence"] is False
    assert report["ready_for_evidence_handoff"] is False
    assert report["ready_for_cutover"] is False


def test_synthetic_drill_source_does_not_call_real_archive_or_handoff_gates():
    source = Path(drill.__file__).read_text()

    assert "tenant_import_rehearsal_evidence_archive" not in source
    assert "tenant_import_rehearsal_evidence_handoff" not in source


def test_design_and_verification_docs_state_external_evidence_remains_missing():
    design = _DESIGN.read_text()
    verification = _VERIFICATION.read_text()

    assert "real_rehearsal_evidence=false" in design
    assert "ready_for_evidence_handoff=false" in design
    assert "operator-run PostgreSQL rehearsal evidence is still missing" in verification
