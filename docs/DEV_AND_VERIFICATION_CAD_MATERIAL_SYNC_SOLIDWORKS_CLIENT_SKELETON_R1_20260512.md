# Development And Verification: SolidWorks Client Skeleton R1

## 1. Summary

This change starts CAD Material Sync SolidWorks client implementation with an
SDK-free R1.1 skeleton under `clients/solidworks-material-sync/`.

It does not build or run against SolidWorks. The purpose is to create the
source-level seam that a Windows-capable worker can bind to real SolidWorks
Add-in/COM calls without changing the server API or weakening the existing
evidence gates.

## 2. Delivered Files

- `clients/solidworks-material-sync/README.md`
- `clients/solidworks-material-sync/MANIFEST.md`
- `clients/solidworks-material-sync/SolidWorksMaterialSync/SolidWorksMaterialSync.csproj`
- `clients/solidworks-material-sync/SolidWorksMaterialSync/ICadMaterialFieldAdapter.cs`
- `clients/solidworks-material-sync/SolidWorksMaterialSync/ISolidWorksMaterialDocumentGateway.cs`
- `clients/solidworks-material-sync/SolidWorksMaterialSync/SolidWorksMaterialFieldAdapter.cs`
- `clients/solidworks-material-sync/SolidWorksMaterialSync/SolidWorksMaterialFieldMapper.cs`
- `clients/solidworks-material-sync/SolidWorksMaterialSync/SolidWorksDiffPreviewClient.cs`
- `clients/solidworks-material-sync/SolidWorksMaterialSync/SolidWorksWriteBackPlan.cs`
- `src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_client_skeleton_contracts.py`

## 3. Design

The skeleton keeps Windows-only SolidWorks APIs behind
`ISolidWorksMaterialDocumentGateway`.

The future COM/Add-in implementation must back that gateway with:

- `CustomPropertyManager.GetAll3` or equivalent key enumeration.
- `CustomPropertyManager.Get6` resolved-value reads.
- Cut-list and table-backed property reads.
- Confirmed custom-property writes from `write_cad_fields`.

The local diff-preview seam is pinned to:

`POST /api/v1/plugins/cad-material-sync/diff/preview`

with:

`cad_system=solidworks`

## 4. Guardrails

- No SolidWorks SDK dependency is introduced.
- No AutoCAD SDK symbols are imported.
- No binary artifacts are committed.
- No Windows evidence is filled.
- No parent SolidWorks TODO item is marked complete.
- AutoCAD primary labels are rejected from SolidWorks write-back plans.

## 5. TODO Update

The TODO now records two completed SDK-free skeleton substeps:

- SolidWorks Add-in/COM gateway and field adapter skeleton.
- SolidWorks diff-preview/write-back skeleton.

The parent items remain unchecked because real Windows smoke is still pending.

## 6. Verification Commands

```bash
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_client_skeleton_contracts.py
```

```bash
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_fixture_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_diff_confirm_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_windows_evidence_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_client_taskbook_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_client_skeleton_contracts.py
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

All checks should pass on macOS without SolidWorks installed. Real Add-in/COM
loading, UI rendering, document write-back, and save/reopen persistence remain
blocked on a Windows SolidWorks workstation.

## 8. Verification Results

- New skeleton contract:
  `src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_client_skeleton_contracts.py`
  -> `6 passed`.
- SolidWorks contract bundle:
  fixture + diff-confirm + Windows evidence + taskbook + skeleton -> `27 passed`.
- Doc-index and CI list-order bundle -> `5 passed`.
- Full delivery doc-index sorting bundle -> `2 passed`.
- CAD material delivery package verifier:
  `python3 scripts/verify_cad_material_delivery_package.py` -> passed.
- `git diff --check` -> clean.
- `dotnet build clients/solidworks-material-sync/SolidWorksMaterialSync/SolidWorksMaterialSync.csproj`
  was not run because this machine does not have the .NET SDK installed:
  `zsh:1: command not found: dotnet`.
