# CAD Material Sync SolidWorks Windows Evidence Template - Development & Verification

## 1. Goal

Add the external validation gate for the real SolidWorks CAD Material Sync client work.

This slice does not implement a SolidWorks Add-in, COM writeback, or local UI. It defines the evidence shape and validator required before future real Windows/SolidWorks work can be marked complete.

## 2. Delivered

- Evidence template: `docs/CAD_MATERIAL_SYNC_SOLIDWORKS_WINDOWS_VALIDATION_EVIDENCE_TEMPLATE_20260511.md`
- Validator: `scripts/validate_cad_material_solidworks_windows_evidence.py`
- Contract: `src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_windows_evidence_contracts.py`
- TODO update: `docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md`
- Index updates: `docs/DELIVERY_DOC_INDEX.md`, `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`

## 3. Acceptance Boundary

The template separates SDK-free fixture completion from real SolidWorks acceptance.

Required evidence includes:

- Real Windows and SolidWorks version/service-pack details.
- Real add-in build and load evidence.
- Property read and cut-list/table read evidence from a sanitized `.sldprt` or `.sldasm`.
- Diff preview UI, cancel path, confirm path, and save/reopen persistence evidence.
- Reviewer decision fields that stay `no` / `pending` until real artifacts are attached.

## 4. Validator Rules

The validator rejects:

- Blank template values.
- Missing SolidWorks version, service pack, build, load, read, write, or reviewer fields.
- Acceptance fields that are not explicitly `yes`.
- `Decision` values other than `accept`.
- Before/after `SW-Specification@Part` values that do not differ.
- Mock fixture, synthetic, or production-customer evidence tokens.
- Plaintext bearer/API key/token/password/secret patterns.
- AutoCAD Chinese primary field names in the write-package evidence field.

It supports `--json` for redaction-safe automation output.

## 5. TODO State

The real work remains incomplete:

```text
- [ ] SolidWorks 明细表/属性表字段读取。
- [ ] SolidWorks 本地客户端可视化差异预览和确认写回 UI。
```

Only the evidence template and validator subitem is complete.

## 6. Verification Commands

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_windows_evidence_contracts.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_windows_evidence_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_diff_confirm_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_fixture_contracts.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_windows_evidence_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m py_compile \
  scripts/validate_cad_material_solidworks_windows_evidence.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_windows_evidence_contracts.py

python3 scripts/validate_cad_material_solidworks_windows_evidence.py --json
# Expected on the blank template: non-zero exit with redaction-safe JSON failures.

git diff --check
```

## 7. Verification Results

- SolidWorks Windows evidence contract: `8 passed`.
- SolidWorks evidence + diff-confirm + field fixture contracts: `16 passed`.
- SolidWorks evidence contract + delivery scripts index + doc-index trio: `14 passed`.
- CI YAML test-list order contract: `1 passed`.
- `py_compile` for the validator and contract test: passed.
- Blank-template `--json` validator run: expected non-zero, redaction-safe JSON with field-name failures only.
- `python3 scripts/verify_cad_material_delivery_package.py`: passed.
- `git diff --check`: clean.

## 8. Non-Goals

- No SolidWorks Add-in.
- No COM implementation.
- No local SolidWorks UI.
- No real Windows/SolidWorks evidence creation.
- No AutoCAD client change.
- No runtime API change.

## 9. Reviewer Checklist

- Template is clearly marked as not validation evidence.
- Blank template keeps all acceptance fields at `no` and decision at `pending`.
- Validator accepts a minimal real-evidence-shaped file.
- Validator rejects mock/synthetic evidence and secrets.
- TODO keeps real SolidWorks work incomplete.
