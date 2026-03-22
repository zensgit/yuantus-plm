# CAD BOM Operator Export Bundle: Development & Verification

**Date**: 2026-03-22
**Branch**: `feature/codex-cad-bom-ops-bundle`

## Scope

This delivery extends the existing CAD BOM recovery work with:

- `GET /api/v1/cad/files/{file_id}/bom/export?export_format=zip|json`
- evidence-oriented zip contents for operator handoff
- dedicated CAD BOM operations runbook

The raw artifact surface remains unchanged:

- `GET /api/v1/file/{file_id}/cad_bom`

## Implementation Notes

- `cad_router` now builds a canonical operator bundle payload from:
  - the derived CAD BOM response
  - current review state
  - recent CAD history
  - stable follow-up links
- `zip` export mirrors the existing evidence-bundle pattern already used by
  impact and release-readiness exports.
- `RUNBOOK_CAD_BOM_OPERATIONS.md` documents inspection, export, review,
  history, and bounded reimport steps.

## Tests Added / Extended

### `src/yuantus/meta_engine/tests/test_cad_bom_router.py`

- zip export includes bundle, review, history, and recovery files
- json export supports job fallback
- unsupported export format returns `400`

### Existing targeted regression pack

- `src/yuantus/meta_engine/tests/test_cad_bom_import_service.py`
- `src/yuantus/meta_engine/tests/test_cad_bom_task.py`
- `src/yuantus/meta_engine/tests/test_file_viewer_readiness.py`

These continue to guard:

- contract validation summary
- automatic pending review flip
- file metadata CAD review exposure

## Commands

Targeted:

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-cad-bom-ops-target \
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_bom_import_service.py \
  src/yuantus/meta_engine/tests/test_cad_bom_router.py \
  src/yuantus/meta_engine/tests/test_cad_bom_task.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py
```

Result:

- `38 passed, 2 warnings in 9.75s`

Syntax:

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-cad-bom-ops-pycompile \
python3 -m py_compile \
  src/yuantus/meta_engine/web/cad_router.py \
  src/yuantus/meta_engine/tests/test_cad_bom_router.py \
  src/yuantus/meta_engine/tests/test_cad_bom_task.py \
  src/yuantus/meta_engine/services/cad_bom_import_service.py \
  src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py
```

Result:

- passed

Doc/runbook contracts:

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_doc_index_sorting.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_all_sections_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_core_required_entries_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbook_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py
```

Result:

- `9 passed in 0.11s`

Full stack:

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-cad-bom-ops-full \
PYTEST_ADDOPTS='-p no:cacheprovider' \
scripts/verify_odoo18_plm_stack.sh full
```

Result:

- `734 passed, 252 warnings in 15.50s`

## Expected Operator Outcome

After this delivery, operators can export one bounded evidence package that
answers:

1. what the current CAD BOM contract status is
2. whether the file is pending review
3. what happened recently in CAD history
4. which bounded recovery actions are available

That is the concrete “operations/detail surpass” gain for this increment.
