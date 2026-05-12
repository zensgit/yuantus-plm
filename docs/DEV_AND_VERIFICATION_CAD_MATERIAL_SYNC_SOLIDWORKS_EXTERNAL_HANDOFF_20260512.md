# Development And Verification: SolidWorks External Validation Handoff

Date: 2026-05-12

Path:
`docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_SOLIDWORKS_EXTERNAL_HANDOFF_20260512.md`

## 1. Summary

PRs #518 through #522 delivered the repository-side SolidWorks material sync
client plan, SDK-free client skeletons, confirmation/pull workflow contracts,
Windows evidence template, validator, runbook, and Windows preflight script.

The remaining validation is external: a Windows workstation with a real
SolidWorks installation must build/load the Add-in/COM path, read real
SolidWorks custom properties and cut-list/table fields, show the diff preview
UI, exercise cancel and confirm/write, save the document, reopen it, and return
sanitized evidence.

This change is a handoff/launchpack only. It does not implement real
SolidWorks runtime support, mark the TODO parents complete, or create filled
acceptance evidence.

## 2. Canonical Inputs

The Windows operator should use these repository artifacts as the source of
truth:

- `docs/DEVELOPMENT_CLAUDE_TASK_CAD_MATERIAL_SYNC_SOLIDWORKS_CLIENT_R1_20260512.md`
- `clients/solidworks-material-sync/WINDOWS_SOLIDWORKS_VALIDATION_GUIDE.md`
- `clients/solidworks-material-sync/verify_solidworks_windows_preflight.ps1`
- `docs/CAD_MATERIAL_SYNC_SOLIDWORKS_WINDOWS_VALIDATION_EVIDENCE_TEMPLATE_20260511.md`
- `scripts/validate_cad_material_solidworks_windows_evidence.py`

## 3. Operator Procedure

Run this sequence on Windows with SolidWorks installed:

1. Sync to the target `main` commit recorded by the reviewer.
2. From `clients\solidworks-material-sync`, run:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\verify_solidworks_windows_preflight.ps1
   ```

3. Build the SolidWorks material sync Add-in/COM assembly from the local
   checkout. The compiled DLL is evidence output and must not be committed.
4. Load the Add-in/COM into SolidWorks.
5. Run custom property read against a real SolidWorks document.
6. Run cut-list or table field read against the same real document when the
   document type supports it.
7. Run `/api/v1/plugins/cad-material-sync/diff/preview` with
   `cad_system=solidworks`.
8. Show the diff preview UI and capture a sanitized screenshot/log path.
9. Exercise the cancel path and confirm it performs no write.
10. Exercise the confirm write path and write only the returned
    `write_cad_fields` keys.
11. Save the SolidWorks document, close it, reopen it, and confirm the written
    fields persisted.
12. Fill
    `docs/CAD_MATERIAL_SYNC_SOLIDWORKS_WINDOWS_VALIDATION_EVIDENCE_TEMPLATE_20260511.md`
    with sanitized output.
13. From the repository root, run:

    ```powershell
    python scripts\validate_cad_material_solidworks_windows_evidence.py <filled-evidence.md>
    ```

14. Return the filled evidence MD plus sanitized log/screenshot paths only.

## 4. Required Returned Artifacts

The reviewer should reject an evidence package that does not include all of
these items:

- preflight output.
- SolidWorks version.
- SolidWorks service pack.
- build result.
- Add-in/COM load result.
- custom property read result.
- cut-list or table field read result.
- diff preview UI result.
- cancel path result.
- confirm write result.
- save/reopen result.
- validator OK output.

The expected validator success line is:

```text
OK: CAD material SolidWorks Windows evidence shape is acceptable
```

## 5. Redaction Rules

The returned evidence must not contain:

- plaintext secrets, bearer tokens, API keys, refresh tokens, passwords, or
  session cookies.
- tenant tokens or organization tokens.
- workstation usernames or home-directory paths.
- production CAD file paths.
- customer names, supplier names, project names, drawing numbers, or proprietary
  part names.
- screenshots with unredacted customer drawings or material tables.

Evidence should use sanitized labels such as `sanitized-test-part.sldprt`,
`evidence/solidworks-diff-preview.png`, and `evidence/solidworks-addin.log`.

## 6. Stop Gates

Do not accept the external SolidWorks validation when any of these is true:

- any preflight step fails.
- the workstation does not have a real SolidWorks installation.
- Add-in/COM load is not demonstrated in SolidWorks.
- custom property read uses a mock, fixture, or SDK-free contract output.
- cut-list/table read is skipped without a written explanation.
- diff preview UI is not shown.
- cancel path is not demonstrated.
- confirm write is not demonstrated.
- save/reopen persistence is missing.
- `scripts\validate_cad_material_solidworks_windows_evidence.py` fails.
- evidence contains plaintext secrets or unredacted customer data.
- TODO parent items are marked complete from this handoff alone.

## 7. TODO Boundary

This handoff keeps the remaining real SolidWorks runtime TODOs open:

- `SolidWorks 明细表/属性表字段读取。`
- `真实 SolidWorks Add-in/COM 读取实现与 Windows smoke。`
- `SolidWorks 本地客户端可视化差异预览和确认写回 UI。`
- `真实 SolidWorks 本地确认 UI、COM 写回和 Windows smoke。`

The handoff is acceptable only as an operator launchpack. It is not Windows
acceptance evidence and must not be used to mark those parent items complete.

## 8. Non-Goals

- No runtime code changes.
- No SolidWorks DLL or binary artifact.
- No COM registration.
- No filled evidence file.
- No production CAD file modification.
- No TODO parent completion.
- No replacement for Windows + SolidWorks manual validation.

## 9. Verification Commands

```bash
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_external_handoff_contracts.py
```

```bash
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_fixture_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_client_taskbook_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_client_skeleton_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_confirmation_model_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_pull_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_diff_confirm_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_external_handoff_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_windows_evidence_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_windows_runbook_contracts.py
```

```bash
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_all_sections_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_verification_reports_sorting_contracts.py
```

```bash
python3 -m py_compile \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_external_handoff_contracts.py
```

```bash
git diff --check
```

## 10. Verification Results

- SolidWorks external handoff contract:
  `src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_external_handoff_contracts.py`
  -> `5 passed`.
- SolidWorks contract bundle:
  fixture + taskbook + skeleton + confirmation model + pull workflow +
  diff-confirm + external handoff + Windows evidence + Windows runbook ->
  `46 passed`.
- Doc-index, CI list-order, and full doc-index sorting bundle -> `7 passed`.
- Python compile:
  `python3 -m py_compile src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_external_handoff_contracts.py`
  -> passed.
- `git diff --check` -> clean.

The PowerShell preflight and SolidWorks runtime path were not executed on this
macOS machine. They remain Windows + SolidWorks operator responsibilities.

## 11. Reviewer Checklist

- Confirm every canonical input exists and is referenced by this handoff.
- Confirm the preflight and evidence-validator commands are present.
- Confirm the required returned artifacts cover read, preview, cancel, confirm,
  save/reopen, and validator success.
- Confirm redaction rules reject secrets and customer CAD data.
- Confirm stop gates keep mock/fixture output from being accepted as real
  SolidWorks evidence.
- Confirm the SolidWorks TODO parents remain unchecked.
