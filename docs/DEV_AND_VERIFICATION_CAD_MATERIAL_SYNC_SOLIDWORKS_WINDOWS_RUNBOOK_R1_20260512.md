# Development And Verification: SolidWorks Windows Runbook R1

## 1. Summary

This change adds the Windows execution runbook and preflight script for the
SolidWorks CAD Material Sync runtime validation path.

It does not implement or validate real SolidWorks runtime support. The purpose
is to give the Windows/SolidWorks operator a concrete command path for build,
Add-in/COM load, field read, diff preview, confirm/cancel, save/reopen, and
evidence validation.

## 2. Delivered Files

- `clients/solidworks-material-sync/WINDOWS_SOLIDWORKS_VALIDATION_GUIDE.md`
- `clients/solidworks-material-sync/verify_solidworks_windows_preflight.ps1`
- `src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_windows_runbook_contracts.py`
- `docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_SOLIDWORKS_WINDOWS_RUNBOOK_R1_20260512.md`
- `clients/solidworks-material-sync/MANIFEST.md`
- `docs/DELIVERY_DOC_INDEX.md`
- `.github/workflows/ci.yml`

## 3. Design

The runbook covers the Windows-only acceptance path:

- Preflight from `clients\solidworks-material-sync`.
- SolidWorks installation discovery.
- MSBuild discovery.
- Add-in/COM build and load smoke.
- Real `CustomPropertyManager` read path.
- Cut-list/table field read.
- `/api/v1/plugins/cad-material-sync/diff/preview` with
  `cad_system=solidworks`.
- Confirm/cancel smoke.
- Save/reopen persistence smoke.
- Evidence validation through
  `scripts/validate_cad_material_solidworks_windows_evidence.py`.

## 4. Scope Control

Included:

- Windows operator guide.
- PowerShell preflight script.
- Contract tests for required runbook sections, preflight checks, non-evidence
  language, and CI wiring.

Excluded:

- No compiled DLL.
- No SolidWorks interop assembly.
- No real Add-in/COM implementation.
- No filled evidence file.
- No TODO parent completion.

## 5. Verification Commands

```bash
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_windows_runbook_contracts.py
```

```bash
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_fixture_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_diff_confirm_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_windows_evidence_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_client_taskbook_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_client_skeleton_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_confirmation_model_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_pull_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_windows_runbook_contracts.py
```

```bash
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py
```

```bash
python3 -m py_compile \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_windows_runbook_contracts.py
```

```bash
git diff --check
```

## 6. Expected Result

All repository checks pass on macOS. The PowerShell preflight is syntax/content
guarded by contracts here, but its real execution requires Windows with
SolidWorks installed.

## 7. Verification Results

- Windows runbook contract:
  `src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_windows_runbook_contracts.py`
  -> `4 passed`.
- SolidWorks contract bundle:
  fixture + diff-confirm + Windows evidence + taskbook + skeleton +
  confirmation model + pull workflow + Windows runbook -> `41 passed`.
- Doc-index and CI list-order bundle -> `5 passed`.
- Full delivery doc-index sorting bundle -> `2 passed`.
- Python compile:
  `python3 -m py_compile src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_windows_runbook_contracts.py`
  -> passed.
- CAD material delivery package verifier:
  `python3 scripts/verify_cad_material_delivery_package.py` -> passed.
- `git diff --check` -> clean.

The PowerShell preflight was not executed because this machine is macOS and has
no SolidWorks installation. That is expected; real execution belongs to the
Windows validation step.
