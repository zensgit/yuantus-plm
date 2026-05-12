# Development And Verification: SolidWorks Confirmation Model R1

## 1. Summary

This change advances CAD Material Sync SolidWorks R1.2 with an SDK-free local
confirmation model. It converts a `/diff/preview` response into UI-ready rows,
confirmed `write_cad_fields`, and cancel/no-op behavior.

This is not the real Windows WPF or SolidWorks COM implementation. It is the
testable model layer that a future Windows UI can bind to.

## 2. Delivered Files

- `clients/solidworks-material-sync/SolidWorksMaterialSync/SolidWorksDiffConfirmationViewModel.cs`
- `clients/solidworks-material-sync/verify_solidworks_confirmation_fixture.py`
- `src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_confirmation_model_contracts.py`
- `docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_SOLIDWORKS_CONFIRMATION_MODEL_R1_20260512.md`
- `docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md`
- `docs/DELIVERY_DOC_INDEX.md`
- `.github/workflows/ci.yml`

## 3. Design

`SolidWorksDiffConfirmationViewModel` accepts:

- current CAD fields from the active SolidWorks document snapshot.
- `SolidWorksDiffPreviewResult` containing `target_cad_fields`,
  `write_cad_fields`, `statuses`, and `requires_confirmation`.

It produces:

- `Rows`: one `SolidWorksDiffFieldRow` per target SolidWorks field.
- `Confirm()`: returns sanitized SolidWorks `write_cad_fields` only when
  `requires_confirmation` is true.
- `Cancel()`: always returns an empty write package and marks the model
  cancelled.

Write filtering delegates to `SolidWorksWriteBackPlan`, so AutoCAD primary
labels cannot be applied by the SolidWorks client path.

## 4. Scope Control

Included:

- SDK-free confirmation view-model.
- Fixture verifier over `docs/samples/cad_material_solidworks_diff_confirm_fixture.json`.
- Contract tests for confirm, cancel, no-op, explicit-clear, indexing, and CI
  wiring.

Excluded:

- No WPF window or Windows UI rendering.
- No SolidWorks COM write.
- No save/reopen persistence evidence.
- No filled Windows evidence.
- No parent TODO completion.

## 5. TODO State

The TODO gains one completed SDK-free substep for the confirmation view-model.

The parent item remains unchecked:

`SolidWorks 本地客户端可视化差异预览和确认写回 UI。`

That parent requires real Windows UI, COM write-back, and Windows smoke.

## 6. Verification Commands

```bash
python3 clients/solidworks-material-sync/verify_solidworks_confirmation_fixture.py
```

```bash
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_confirmation_model_contracts.py
```

```bash
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_fixture_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_diff_confirm_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_windows_evidence_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_client_taskbook_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_client_skeleton_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_confirmation_model_contracts.py
```

```bash
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py
```

```bash
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_all_sections_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_verification_reports_sorting_contracts.py
```

```bash
git diff --check
```

## 7. Expected Result

All checks should pass on macOS without SolidWorks installed. The real UI and
COM path remain blocked on Windows SolidWorks runtime validation.

## 8. Verification Results

- Confirmation fixture verifier:
  `python3 clients/solidworks-material-sync/verify_solidworks_confirmation_fixture.py`
  -> `OK: SolidWorks confirmation fixture passed (3 cases)`.
- New confirmation model contract:
  `src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_confirmation_model_contracts.py`
  -> `5 passed`.
- SolidWorks contract bundle:
  fixture + diff-confirm + Windows evidence + taskbook + skeleton +
  confirmation model -> `32 passed`.
- Doc-index and CI list-order bundle -> `5 passed`.
- Full delivery doc-index sorting bundle -> `2 passed`.
- CAD material delivery package verifier:
  `python3 scripts/verify_cad_material_delivery_package.py` -> passed.
- Python compile:
  `python3 -m py_compile clients/solidworks-material-sync/verify_solidworks_confirmation_fixture.py src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_confirmation_model_contracts.py`
  -> passed.
- `git diff --check` -> clean.
- `dotnet build` was not run because this machine does not have the .NET SDK
  installed; this remains a Windows/.NET validation step for the implementation
  worker.
