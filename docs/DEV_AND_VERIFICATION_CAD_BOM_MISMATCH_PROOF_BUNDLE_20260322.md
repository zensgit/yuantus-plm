# CAD BOM Mismatch Proof Bundle: Development & Verification

**Date**: 2026-03-22
**Branch**: `feature/codex-cad-bom-mismatch-proof`

## Scope

This delivery extends the current CAD BOM recovery/export work with:

- derived live-vs-CAD mismatch analysis
- `GET /api/v1/cad/files/{file_id}/bom/mismatch`
- proof-oriented mismatch files in `bom/export`
- runbook guidance for mismatch-first triage

The raw artifact surface remains unchanged:

- `GET /api/v1/file/{file_id}/cad_bom`

## Implementation Notes

- `build_cad_bom_mismatch_analysis(...)` builds a compare tree from accepted CAD
  BOM nodes/edges and compares it to the current live BOM.
- the comparison uses `line_key=child_id_find_refdes` to keep the contract
  explicit and stable.
- empty and unresolved states now return a fixed contract shape so export and
  UI clients receive predictable fields.
- `cad_router` exposes the mismatch analysis both inline on `/bom` and through
  the dedicated `/bom/mismatch` endpoint.
- `bom/export` now emits mismatch evidence files plus `proof_manifest.json` for
  operator handoff and regression attachment.

## Tests Added / Extended

### `src/yuantus/meta_engine/tests/test_cad_bom_import_service.py`

- quantity drift against the live BOM is summarized as mismatch
- unresolved item binding still returns a stable empty mismatch contract

### `src/yuantus/meta_engine/tests/test_cad_bom_router.py`

- stored CAD BOM response includes `mismatch`
- job fallback keeps the mismatch contract available
- `GET /bom/mismatch` returns operator links and unresolved state
- zip export includes mismatch files and a proof manifest
- json export includes mismatch/proof manifest data

### Existing targeted regression pack

- `src/yuantus/meta_engine/tests/test_cad_bom_task.py`
- `src/yuantus/meta_engine/tests/test_file_viewer_readiness.py`

These continue to guard adjacent CAD review/readiness behavior so this
increment does not regress the surrounding operator surface.

## Commands

Syntax:

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-cad-bom-mismatch-pycompile \
python3 -m py_compile \
  src/yuantus/meta_engine/services/cad_bom_import_service.py \
  src/yuantus/meta_engine/web/cad_router.py \
  src/yuantus/meta_engine/tests/test_cad_bom_import_service.py \
  src/yuantus/meta_engine/tests/test_cad_bom_router.py
```

Result:

- passed

Targeted:

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-cad-bom-mismatch-target \
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_bom_import_service.py \
  src/yuantus/meta_engine/tests/test_cad_bom_router.py \
  src/yuantus/meta_engine/tests/test_cad_bom_task.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py
```

Result:

- `41 passed, 2 warnings in 49.55s`

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
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-cad-bom-mismatch-full \
PYTEST_ADDOPTS='-p no:cacheprovider' \
scripts/verify_odoo18_plm_stack.sh full
```

Result:

- `734 passed, 252 warnings in 17.83s`

## Expected Operator Outcome

After this delivery, operators can:

1. inspect whether the derived CAD BOM still matches the live BOM
2. distinguish structural drift from line-value drift without opening raw
   compare payloads
3. export a proof bundle before recovery actions
4. hand the same mismatch/proof artifact to support, QA, or customer
   verification

That is the concrete “operations/detail surpass” gain for this increment.
