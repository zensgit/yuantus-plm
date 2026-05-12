# Development And Verification: SolidWorks Pull Workflow R1

## 1. Summary

This change adds an SDK-free SolidWorks pull workflow orchestration layer for
CAD Material Sync.

It connects the previously merged pieces:

- field extraction through `SolidWorksMaterialFieldAdapter`.
- `/api/v1/plugins/cad-material-sync/diff/preview` through
  `SolidWorksDiffPreviewClient`.
- local confirmation through `SolidWorksDiffConfirmationViewModel`.
- confirmed write-back through the gateway `ApplyFields` boundary.

No real SolidWorks UI, COM call, save/reopen persistence, or Windows evidence is
introduced in this slice.

## 2. Delivered Files

- `clients/solidworks-material-sync/SolidWorksMaterialSync/SolidWorksMaterialPullWorkflow.cs`
- `clients/solidworks-material-sync/verify_solidworks_pull_workflow_fixture.py`
- `src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_pull_workflow_contracts.py`
- `docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_SOLIDWORKS_PULL_WORKFLOW_R1_20260512.md`
- `docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md`
- `docs/DELIVERY_DOC_INDEX.md`
- `.github/workflows/ci.yml`

## 3. Design

`SolidWorksMaterialPullWorkflow.PreviewAsync()`:

- extracts the current CAD field snapshot from the active document gateway.
- calls the diff-preview API via `SolidWorksDiffPreviewClient`.
- converts the preview result into a `SolidWorksDiffConfirmationViewModel`.

`ConfirmAndApply()`:

- calls `confirmation.Confirm()`.
- applies only confirmed SolidWorks `write_cad_fields`.
- returns `0` for null, no-op, or no-confirmation cases.

`Cancel()`:

- calls `confirmation.Cancel()`.
- always returns `0`, preserving cancel as a no-op write boundary.

## 4. Guardrails

- No WPF rendering.
- No SolidWorks COM call.
- No `Save` or `SaveAs` call.
- No evidence file creation.
- No parent TODO completion.
- AutoCAD labels remain filtered by `SolidWorksWriteBackPlan`.

## 5. TODO State

The TODO gains one completed SDK-free substep:

`SDK-free SolidWorks pull workflow orchestration`

The parent item remains unchecked:

`SolidWorks 本地客户端可视化差异预览和确认写回 UI。`

Real completion still requires a Windows UI, COM write-back, save/reopen
persistence, and accepted Windows evidence.

## 6. Verification Commands

```bash
python3 clients/solidworks-material-sync/verify_solidworks_pull_workflow_fixture.py
```

```bash
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_pull_workflow_contracts.py
```

```bash
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_fixture_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_diff_confirm_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_windows_evidence_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_client_taskbook_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_client_skeleton_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_confirmation_model_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_pull_workflow_contracts.py
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

All checks should pass on macOS without SolidWorks installed. Runtime UI and COM
validation remains deferred to a Windows SolidWorks workstation.

## 8. Verification Results

- Pull workflow fixture verifier:
  `python3 clients/solidworks-material-sync/verify_solidworks_pull_workflow_fixture.py`
  -> `OK: SolidWorks pull workflow fixture passed (3 cases)`.
- New pull workflow contract:
  `src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_pull_workflow_contracts.py`
  -> `5 passed`.
- SolidWorks contract bundle:
  fixture + diff-confirm + Windows evidence + taskbook + skeleton +
  confirmation model + pull workflow -> `37 passed`.
- Doc-index and CI list-order bundle -> `5 passed`.
- Full delivery doc-index sorting bundle -> `2 passed`.
- CAD material delivery package verifier:
  `python3 scripts/verify_cad_material_delivery_package.py` -> passed.
- Python compile:
  `python3 -m py_compile clients/solidworks-material-sync/verify_solidworks_pull_workflow_fixture.py src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_pull_workflow_contracts.py`
  -> passed.
- `git diff --check` -> clean.
- `dotnet --info` failed with `zsh:1: command not found: dotnet`; .NET build
  remains a Windows/.NET validation step for the implementation worker.
