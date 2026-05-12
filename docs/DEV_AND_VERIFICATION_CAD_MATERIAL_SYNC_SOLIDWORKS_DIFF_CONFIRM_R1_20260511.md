# CAD Material Sync SolidWorks Diff Confirm R1 - Development & Verification

## 1. Goal

Advance the SolidWorks CAD Material Sync plan with an SDK-free diff-confirmation contract for future local SolidWorks clients.

This slice validates the `/diff/preview` consumption boundary for SolidWorks-style field names without implementing a real SolidWorks UI, COM writeback, or Windows smoke.

## 2. Delivered

- Fixture: `docs/samples/cad_material_solidworks_diff_confirm_fixture.json`
- Verifier: `scripts/verify_cad_material_solidworks_diff_confirm.py`
- Contract: `src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_diff_confirm_contracts.py`
- TODO update: `docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md`
- Index updates: `docs/DELIVERY_DOC_INDEX.md`, `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`

## 3. Contract Coverage

The fixture pins three future-client scenarios:

- Add `SW-Thickness@Part` and change `SW-Specification@Part`, producing a non-empty write package and `requires_confirmation=true`.
- Confirm a no-op SolidWorks package produces no write fields and `requires_confirmation=false`.
- Explicitly clear an unmapped SolidWorks custom property, proving client-owned custom fields can still be carried through.

## 4. Field Boundary

All generated target/write fields are SolidWorks-primary fields:

```text
SW-Material@Part
SW-Length@Part
SW-Width@Part
SW-Thickness@Part
SW-Specification@Part
SW-Coating@Part
```

The verifier rejects AutoCAD Chinese primary fields in the SolidWorks write package.

## 5. TODO State

The parent item remains unchecked:

```text
- [ ] SolidWorks 本地客户端可视化差异预览和确认写回 UI。
```

Only the SDK-free diff-confirmation fixture/contract subitem is complete. The real SolidWorks local UI, COM writeback, and Windows smoke remain pending.

## 6. Verification Commands

```bash
python3 scripts/verify_cad_material_solidworks_diff_confirm.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_diff_confirm_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_fixture_contracts.py \
  src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_diff_confirm_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m py_compile \
  scripts/verify_cad_material_solidworks_diff_confirm.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_diff_confirm_contracts.py

python3 scripts/verify_cad_material_delivery_package.py

git diff --check
```

## 7. Verification Results

- `python3 scripts/verify_cad_material_solidworks_diff_confirm.py`: passed.
- SolidWorks diff contract + SolidWorks field fixture contract + existing CAD Material Sync plugin regression: `49 passed`.
- SolidWorks diff contract + delivery scripts index + doc-index trio: `10 passed`.
- CI YAML test-list order contract: `1 passed`.
- `py_compile` for the new verifier and contract test: passed.
- `python3 scripts/verify_cad_material_delivery_package.py`: passed.
- `git diff --check`: clean.

## 8. Non-Goals

- No SolidWorks Add-in.
- No COM writeback.
- No local SolidWorks UI.
- No Windows smoke evidence.
- No CAD Material Sync runtime API change.
- No AutoCAD client change.

## 9. Reviewer Checklist

- The fixture uses `cad_system=solidworks`.
- The expected target/write fields use `SW-*@Part` names only.
- No-op cases produce no write package.
- Clear cases preserve explicit empty-string writeback.
- The TODO keeps the real SolidWorks UI/COM/Windows work incomplete.
