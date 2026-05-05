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
_READINESS_STATUS = (
    _ROOT / "docs" / "PHASE3_TENANT_IMPORT_READINESS_STATUS_20260430.md"
)
_READINESS_TODO = (
    _ROOT / "docs" / "PHASE3_TENANT_IMPORT_READINESS_STATUS_TODO_20260430.md"
)


def test_parent_todo_keeps_real_operator_evidence_unchecked_after_synthetic_drill():
    todo = _TODO.read_text()

    assert "- [x] Add synthetic operator drill for DB-free command-path rehearsal." in todo
    assert "- [x] Add repo-external env-file template and DB-free env-file precheck." in todo
    assert "- [x] Add env-file support to operator command pack and full-closeout wrappers." in todo
    assert "- [x] Add generated operator command-file validator." in todo
    assert "- [x] Add operator command-file and env-file source safety hardening." in todo
    assert "- [x] Add wrapper-level unsafe env-file source guard contracts." in todo
    assert "- [x] Add runbook operator safety contracts." in todo
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


def test_runbook_pins_env_file_precheck_before_wrapper_source():
    runbook = _RUNBOOK.read_text()

    command_pack_pos = runbook.index("## 17.1 P3.4.2 Operator Command Pack")
    sequence_pos = runbook.index("## 17.2 P3.4.2 Operator Sequence Wrapper")
    full_closeout_pos = runbook.index("## 17.3 P3.4.2 Full Closeout Wrapper")
    row_copy_pos = runbook.index("## 18. P3.4.2 Tenant Import Rehearsal Row Copy")

    command_pack_section = runbook[command_pack_pos:sequence_pos]
    full_closeout_section = runbook[full_closeout_pos:row_copy_pos]

    assert "validates the file statically before loading it" in command_pack_section
    assert "rejected before the file is sourced" in command_pack_section
    assert "single-quoted assignments" in full_closeout_section
    assert "before the file is sourced" in full_closeout_section

    full_closeout_precheck_pos = full_closeout_section.index(
        "scripts/precheck_tenant_import_rehearsal_env_file.sh"
    )
    full_closeout_wrapper_pos = full_closeout_section.index(
        "scripts/run_tenant_import_rehearsal_full_closeout.sh"
    )
    assert full_closeout_precheck_pos < full_closeout_wrapper_pos


def test_runbook_pins_command_file_validator_as_non_executing_gate():
    runbook = _RUNBOOK.read_text()

    command_pack_pos = runbook.index("## 17.1 P3.4.2 Operator Command Pack")
    sequence_pos = runbook.index("## 17.2 P3.4.2 Operator Sequence Wrapper")
    command_pack_section = runbook[command_pack_pos:sequence_pos]
    normalized_section = " ".join(command_pack_section.split())

    assert "validates the generated command file before returning success" in command_pack_section
    assert "without executing it" in command_pack_section
    assert "required step order" in normalized_section
    assert "environment variable URL references" in normalized_section
    assert "forbidden DSN/cutover/remote-control patterns" in normalized_section


def test_readiness_status_keeps_operator_safety_hardening_db_free_and_blocked():
    status = _READINESS_STATUS.read_text()

    assert "DB-free" in status
    assert "repo-external env-file template generation" in status
    assert "DB-free env-file static precheck before shell source" in status
    assert "generated operator command-file validation" in status
    assert "runbook operator safety contracts" in status
    assert "rejecting unsafe env-file syntax" in status
    assert "out-of-order generated command files" in status
    assert "full-closeout wrapper using the prechecked env-file path" in status
    assert "operator-run PostgreSQL rehearsal evidence is not complete" in status
    assert "The next valid action is external operator execution" in status
    assert "- [ ] Add operator-run PostgreSQL rehearsal evidence." in status

    todo = _READINESS_TODO.read_text()
    assert "- [x] Track 2026-05-05 DB-free operator safety additions." in todo
    assert (
        "- [x] Keep env-file precheck, command-file validator, and wrapper safety "
        "contracts scoped to local safety."
    ) in todo
    assert "- [ ] Add operator-run PostgreSQL rehearsal evidence." in todo


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


def test_readiness_status_preserves_external_blocked_state():
    status = _READINESS_STATUS.read_text()

    assert "operator-run PostgreSQL rehearsal evidence is not complete" in status
    assert "production cutover" in status
    assert "runtime `TENANCY_MODE=schema-per-tenant` enablement" in status
    assert "The next valid action is external operator execution" in status
    assert "`ready_for_cutover=false`" in status
    assert "- [ ] Add operator-run PostgreSQL rehearsal evidence." in status
