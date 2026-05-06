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
    assert "- [x] Add source/target URL env-name allowlist hardening." in todo
    assert "- [x] Add env-file key allowlist before shell source." in todo
    assert "- [x] Add generated command-file executable-line allowlist." in todo
    assert "- [x] Add generated command-file option-line allowlist." in todo
    assert "- [x] Add generated command-file safe path option validation." in todo
    assert "- [x] Add generated command-file quoted metadata expansion guard." in todo
    assert "- [x] Add generated command-file shell syntax diagnostic redaction." in todo
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
    normalized_command_pack_section = " ".join(command_pack_section.split())
    normalized_full_closeout_section = " ".join(full_closeout_section.split())

    assert "validates the file statically before loading it" in command_pack_section
    assert "rejected before the file is sourced" in command_pack_section
    assert "single-quoted assignments" in full_closeout_section
    assert "before the file is sourced" in normalized_full_closeout_section
    assert "Extra keys such as `PATH`, `PYTHON`, `PYTHONPATH`, and `BASH_ENV`" in (
        normalized_command_pack_section
    )
    assert "unsupported variables" in full_closeout_section

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
    assert "without executing it" in normalized_section
    assert "required step order" in normalized_section
    assert "environment variable URL references" in normalized_section
    assert "forbidden DSN/cutover/remote-control patterns" in normalized_section
    assert "rejects unsupported executable lines" in normalized_section
    assert "`rm`, `ssh`, `python -c`, `export`" in normalized_section
    assert "Continuation option lines are also checked against the generated command step" in (
        normalized_section
    )
    assert "`--confirm-cutover`" in normalized_section
    assert "orphan option lines" in normalized_section
    assert "Path-valued option arguments are restricted to a safe artifact path token set" in (
        normalized_section
    )
    assert "redirection, variable expansion, and quoted path rewrites" in normalized_section
    assert "rejected without echoing the edited value" in normalized_section
    assert "Quoted evidence metadata fields are also checked for shell expansion" in (
        normalized_section
    )
    assert '"$SOURCE_DATABASE_URL"' in normalized_section
    assert r'"ops\reviewer"' in normalized_section
    assert "Shell syntax diagnostics are also redacted" in normalized_section
    assert "does not echo the raw `bash -n` error line" in normalized_section


def test_readiness_status_keeps_operator_safety_hardening_db_free_and_blocked():
    status = _READINESS_STATUS.read_text()
    normalized_status = " ".join(status.split())

    assert "DB-free" in status
    assert "repo-external env-file template generation" in status
    assert "DB-free env-file static precheck before shell source" in status
    assert "generated operator command-file validation" in status
    assert "runbook operator safety contracts" in status
    assert "source/target URL env-name allowlist hardening" in status
    assert "env-file key allowlist before shell source" in status
    assert "rejects env-file keys outside" in status
    assert "generated command-file executable-line allowlist" in status
    assert "generated command-file option-line allowlist" in status
    assert "generated command-file safe path option validation" in status
    assert "generated command-file quoted metadata expansion guard" in status
    assert "generated command-file shell syntax diagnostic redaction" in status
    assert "Path-valued generated command options" in status
    assert "redirection, variable expansion, and quoted path rewrites" in normalized_status
    assert "Quoted generated evidence metadata fields" in normalized_status
    assert "shell variable expansion and backslash escape syntax" in normalized_status
    assert "Shell syntax diagnostics from generated command-file validation are redacted" in (
        normalized_status
    )
    assert "raw `bash -n` error lines cannot echo edited command content" in (
        normalized_status
    )
    assert "unsupported executable or option lines in generated command files" in status
    assert "rejecting unsafe env-file syntax" in status
    assert "out-of-order generated command files" in status
    assert "full-closeout wrapper using the prechecked env-file path" in status
    assert "repo-external env-file contains only the selected source/target URL variables" in status
    assert "uppercase source/target URL env-var names when overriding defaults" in status
    assert "operator-run PostgreSQL rehearsal evidence is not complete" in status
    assert "The next valid action is external operator execution" in status
    assert "- [ ] Add operator-run PostgreSQL rehearsal evidence." in status

    todo = _READINESS_TODO.read_text()
    assert "- [x] Track 2026-05-05 DB-free operator safety additions." in todo
    assert (
        "- [x] Keep env-file precheck, command-file validator, and wrapper safety "
        "contracts scoped to local safety."
    ) in todo
    assert (
        "- [x] Track source/target URL env-name allowlist hardening as local safety only."
    ) in todo
    assert "- [x] Track env-file key allowlist hardening as local safety only." in todo
    assert (
        "- [x] Track command-file executable-line allowlist hardening as local safety only."
    ) in todo
    assert (
        "- [x] Track command-file option-line allowlist hardening as local safety only."
    ) in todo
    assert (
        "- [x] Track command-file safe path option validation as local safety only."
    ) in todo
    assert (
        "- [x] Track command-file quoted metadata expansion guard as local safety only."
    ) in todo
    assert (
        "- [x] Track command-file shell syntax diagnostic redaction as local safety only."
    ) in todo
    assert (
        "- [x] Assert URL env-name allowlist does not close the external evidence gate."
    ) in todo
    assert (
        "- [x] Assert env-file key allowlist does not close the external evidence gate."
    ) in todo
    assert (
        "- [x] Assert command-file executable-line allowlist does not close the external evidence gate."
    ) in todo
    assert (
        "- [x] Assert command-file option-line allowlist does not close the external evidence gate."
    ) in todo
    assert (
        "- [x] Assert command-file safe path option validation does not close the external evidence gate."
    ) in todo
    assert (
        "- [x] Assert command-file quoted metadata expansion guard does not close the external evidence gate."
    ) in todo
    assert (
        "- [x] Assert command-file shell syntax diagnostic redaction does not close the external evidence gate."
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


def test_runbook_pins_source_target_env_name_allowlist_before_operator_commands():
    runbook = _RUNBOOK.read_text()

    command_pack_pos = runbook.index("## 17.1 P3.4.2 Operator Command Pack")
    sequence_pos = runbook.index("## 17.2 P3.4.2 Operator Sequence Wrapper")
    command_pack_section = runbook[command_pack_pos:sequence_pos]

    assert "`--source-url-env` and `--target-url-env`" in command_pack_section
    assert "[A-Z_][A-Z0-9_]*" in command_pack_section
    assert "before any env file is sourced" in command_pack_section
    assert "before indirect environment expansion" in command_pack_section
    assert "before generated operator commands are written" in command_pack_section
    assert "uppercase shell variable names" in command_pack_section
