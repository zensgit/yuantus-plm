# CAD Asset Quality Proof Linking: Development & Verification

**Date**: 2026-03-22
**Branch**: `feature/codex-cad-asset-quality-proof-linking`

## Scope

This delivery extends the existing CAD BOM proof/export line with:

- a shared CAD operator proof bundle builder
- `GET /api/v1/cad/files/{file_id}/proof`
- `asset_quality` and `viewer_readiness` linkage inside the CAD proof surface
- additional proof files in `GET /api/v1/cad/files/{file_id}/bom/export`
- recovery guidance that points back to the unified proof surface
- runbook updates for proof-first operator triage

The raw artifact surfaces remain unchanged:

- `GET /api/v1/file/{file_id}/cad_bom`
- `GET /api/v1/file/{file_id}/asset_quality`
- `GET /api/v1/file/{file_id}/viewer_readiness`

## Implementation Notes

- `cad_router.py` now assembles one shared operator proof bundle instead of
  letting `/proof` and `/bom/export` diverge
- `operator_proof.status` is derived from asset trust, viewer readiness, BOM
  drift, and review state
- `proof_gaps` makes missing/degraded evidence explicit and stable
- `proof_manifest.json` now records operator-proof, asset-quality, and
  viewer-readiness status alongside mismatch metadata
- export bundles now carry `operator_proof.json`, `viewer_readiness.json`, and
  `asset_quality.json`, plus dedicated CSV rows for asset issue codes and
  recovery actions
- CAD BOM mismatch recovery guidance now includes
  `open_cad_operator_proof_surface`

## Tests Added / Extended

### `src/yuantus/meta_engine/tests/test_cad_bom_router.py`

- `GET /api/v1/cad/files/{file_id}/proof` returns linked asset quality, viewer
  readiness, mismatch, and proof manifest data
- zip export includes operator-proof, asset-quality, and viewer-readiness files
- json export now includes `asset_quality`, `viewer_readiness`, and
  `operator_proof`
- README/proof manifest carry proof-level links and statuses

### `src/yuantus/meta_engine/tests/test_cad_bom_import_service.py`

- mismatch recovery actions now include `open_cad_operator_proof_surface`

### Existing targeted regression pack

- `src/yuantus/meta_engine/tests/test_file_viewer_readiness.py`

This remains important because the new proof surface is deliberately composed
from the existing file-level readiness/asset-quality contract rather than
redefining it.

## Commands

Syntax:

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-cad-proof-linking-pycompile2 \
python3 -m py_compile \
  src/yuantus/meta_engine/web/cad_router.py \
  src/yuantus/meta_engine/services/cad_bom_import_service.py \
  src/yuantus/meta_engine/tests/test_cad_bom_router.py \
  src/yuantus/meta_engine/tests/test_cad_bom_import_service.py
```

Result:

- passed

Targeted:

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-cad-proof-linking-target2 \
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_bom_router.py \
  src/yuantus/meta_engine/tests/test_cad_bom_import_service.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py
```

Result:

- `46 passed, 2 warnings in 24.26s`

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

- `9 passed in 0.16s`

Full stack:

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-cad-proof-linking-full \
PYTEST_ADDOPTS='-p no:cacheprovider' \
scripts/verify_odoo18_plm_stack.sh full
```

Result:

- `739 passed, 253 warnings in 16.18s`

## Expected Operator Outcome

After this delivery, operators can:

1. open one proof surface and immediately see whether CAD assets are trusted,
   whether the viewer is ready, whether the live BOM drifts, and whether review
   is still pending
2. export one bundle that already carries asset trust, drift, and history
   evidence together
3. follow recovery actions that point back to the unified proof context instead
   of bouncing between unrelated surfaces

That is the concrete operations/detail surpass gain for this increment.
