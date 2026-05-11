# Dev & Verification - CAD Material Sync Windows Evidence Template

Date: 2026-05-11

Path:
`docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_WINDOWS_EVIDENCE_TEMPLATE_20260511.md`

## 1. Summary

Added a blank evidence template for the CAD Material Sync Windows + AutoCAD
validation path.

This is not validation evidence. It is an operator/reviewer template to make the
future Windows evidence submission consistent and reviewable.

## 2. Delivered

- `docs/CAD_MATERIAL_SYNC_WINDOWS_VALIDATION_EVIDENCE_TEMPLATE_20260511.md`
- `docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_WINDOWS_EVIDENCE_TEMPLATE_20260511.md`
- Contract coverage in
  `src/yuantus/meta_engine/tests/test_cad_material_sync_external_validation_contracts.py`
- `docs/DELIVERY_DOC_INDEX.md` entries for both documents

## 3. Design

The template separates three states:

1. Delivery package merged.
2. Windows validation evidence pending.
3. Windows validation accepted after real AutoCAD output exists.

It intentionally keeps every acceptance field as explicit `no` and keeps the
review decision as `pending` until real Windows artifacts are attached and
reviewed. This avoids treating a blank template as optional acceptance evidence.

## 4. Scope Controls

- No runtime code changes.
- No AutoCAD client source changes.
- No binary artifacts.
- No fake or synthetic Windows evidence.
- No production DWG content.
- No Phase 5 implementation.
- No P3.4 evidence creation or acceptance.
- No production cutover.

## 5. Verification Commands

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_material_sync_external_validation_contracts.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_material_sync_external_validation_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m py_compile \
  src/yuantus/meta_engine/tests/test_cad_material_sync_external_validation_contracts.py

git diff --check
```

## 6. Verification Results

- External validation contract: 5 passed.
- Focused doc-index suite: 4 passed.
- `py_compile` on the updated contract: passed.
- `git diff --check`: clean.

## 7. Reviewer Checklist

- Confirm the template is blank and cannot be mistaken for completed evidence.
- Confirm AutoCAD 2018 / `R22.0` remains the primary baseline.
- Confirm AutoCAD 2024 is represented only as a regression section.
- Confirm no runtime, client source, binary, Phase 5, P3.4, or cutover changes
  are included.
