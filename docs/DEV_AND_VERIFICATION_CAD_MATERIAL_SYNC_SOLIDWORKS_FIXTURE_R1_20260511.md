# CAD Material Sync SolidWorks Fixture R1 - Development & Verification

## 1. Goal

Add the first SolidWorks-specific CAD Material Sync validation slice without requiring SolidWorks, Windows, COM, or a real client add-in.

This slice pins the field boundary for future SolidWorks client work:

- SolidWorks-style custom properties and cut-list properties normalize to plugin canonical material fields.
- Table adjacent-cell and inline `key=value` reads are covered.
- `cad_system=solidworks` writeback packages use `SW-*@Part` target fields instead of AutoCAD Chinese primary field names.
- The real SolidWorks Add-in/COM adapter and Windows smoke remain explicitly incomplete.

## 2. Delivered

- Fixture: `docs/samples/cad_material_solidworks_fixture.json`
- Verifier: `scripts/verify_cad_material_solidworks_fixture.py`
- Contract: `src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_fixture_contracts.py`
- TODO update: `docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md`
- Index updates: `docs/DELIVERY_DOC_INDEX.md`, `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`

## 3. Fixture Shape

The fixture models three SolidWorks input surfaces:

- `custom_properties`: part-level keys such as `SW-Part Number@Part`, `SW-Material@Part`, and `SW-Thickness@Part`.
- `cut_list_properties`: cut-list keys such as `SW-Length@CutList` and `SW-Width@CutList`.
- `tables`: adjacent-cell and inline `key=value` cells such as `SW-MaterialCategory@Part`, `SW-Specification@Part`, and `SW-HeatTreatment@Part=none`.

Expected extraction is normalized to:

```text
item_number, name, material, thickness, length, width, material_category, specification, heat_treatment
```

Expected writeback is limited to:

```text
SW-Material@Part, SW-Specification@Part, SW-Length@Part, SW-Width@Part, SW-Thickness@Part
```

## 4. Guardrails

- No SolidWorks SDK import.
- No `win32com`, `pythoncom`, or `SldWorks.Application`.
- No Windows runtime assumption.
- No runtime API or plugin behavior change.
- No claim that SolidWorks field reading is fully complete.
- No AutoCAD Chinese primary field names in SolidWorks writeback output.
- No overwrite of undeclared source-only fields such as `SW-HeatTreatment@Part`.

## 5. TODO State

The parent SolidWorks client item remains unchecked:

```text
- [ ] SolidWorks 明细表/属性表字段读取。
```

Only the SDK-free fixture/contract subitem is complete. The real SolidWorks Add-in/COM implementation and Windows smoke stay pending.

## 6. Verification Commands

```bash
python3 scripts/verify_cad_material_solidworks_fixture.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_fixture_contracts.py \
  src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_fixture_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m py_compile \
  scripts/verify_cad_material_solidworks_fixture.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_fixture_contracts.py

python3 scripts/verify_cad_material_delivery_package.py

git diff --check
```

## 7. Verification Results

- `python3 scripts/verify_cad_material_solidworks_fixture.py`: passed.
- SolidWorks fixture contract + existing CAD Material Sync plugin regression: `45 passed`.
- SolidWorks fixture contract + delivery scripts index + doc-index trio: `10 passed`.
- CI YAML test-list order contract: `1 passed`.
- `py_compile` for the new verifier and contract test: passed.
- `python3 scripts/verify_cad_material_delivery_package.py`: passed.
- `git diff --check`: clean.

## 8. Non-Goals

- No SolidWorks Add-in.
- No COM interop.
- No real Windows smoke evidence.
- No AutoCAD client change.
- No CAD Material Sync API change.
- No PLM database migration.

## 9. Reviewer Checklist

- The script runs on macOS/Linux with only Python and JSON.
- The fixture includes part-level, cut-list, adjacent-cell, and inline table field reads.
- The writeback package is SolidWorks-primary and does not use AutoCAD Chinese field keys.
- The TODO keeps real SolidWorks client work incomplete.
- CI runs the new contract test.
