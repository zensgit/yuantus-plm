# CAD BOM Recovery Surfacing: Development & Verification

**Date**: 2026-03-22
**Branch**: `feature/codex-cad-bom-recovery-surfacing`

## Scope

This delivery extends the previous CAD BOM contract work with:

- derived `summary` on `GET /api/v1/cad/files/{file_id}/bom`
- automatic `cad_review_state=pending` on partial/invalid BOM imports
- `POST /api/v1/cad/files/{file_id}/bom/reimport`

The raw artifact endpoint remains unchanged:

- `GET /api/v1/file/{file_id}/cad_bom`

## Implementation Notes

- `build_cad_bom_operator_summary(...)` converts detailed contract/import state
  into coarse operator-facing signals and recovery actions.
- `cad_pipeline_tasks.cad_bom(...)` persists the summary alongside the BOM
  wrapper and flips the file review badge to `pending` for degraded imports.
- `cad_router` exposes the summary and the reimport endpoint.
- `file metadata` continues to surface the existing review badge via
  `cad_review_state`.

## Tests Added / Extended

### `src/yuantus/meta_engine/tests/test_cad_bom_import_service.py`

- ambiguous root binding is reported for graph payloads
- graph payload root inference keeps import flow working
- invalid node/edge entries are recorded without crashing
- degraded imports yield coarse issue codes and recovery actions

### `src/yuantus/meta_engine/tests/test_cad_bom_router.py`

- stored BOM wrapper returns `summary`
- job fallback returns `summary`
- reimport uses stored `item_id`
- reimport returns `400` for ambiguous item resolution

### `src/yuantus/meta_engine/tests/test_cad_bom_task.py`

- partial import sets `cad_review_state=pending`
- stored wrapper persists the derived `summary`

### `src/yuantus/meta_engine/tests/test_file_viewer_readiness.py`

- file metadata still includes viewer readiness
- file metadata exposes the pending CAD review badge

## Commands

Targeted:

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_bom_import_service.py \
  src/yuantus/meta_engine/tests/test_cad_bom_router.py \
  src/yuantus/meta_engine/tests/test_cad_bom_task.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py
```

Result:

- `35 passed, 2 warnings in 17.43s`

Syntax:

```bash
python3 -m py_compile \
  src/yuantus/meta_engine/services/cad_bom_import_service.py \
  src/yuantus/meta_engine/web/cad_router.py \
  src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py \
  src/yuantus/meta_engine/web/file_router.py \
  src/yuantus/meta_engine/tests/test_cad_bom_import_service.py \
  src/yuantus/meta_engine/tests/test_cad_bom_router.py \
  src/yuantus/meta_engine/tests/test_cad_bom_task.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py
```

Result:

- passed

Full stack:

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-cad-bom-recovery \
PYTEST_ADDOPTS='-p no:cacheprovider' \
scripts/verify_odoo18_plm_stack.sh full
```

Result:

- `734 passed, 252 warnings in 15.52s`

## Expected Operator Outcome

After this delivery, an operator no longer needs to inspect only free-form
`contract_validation.issues` or raw import errors.

They can:

1. read `summary.status` and `summary.issue_codes`
2. see `cad_review_state=pending` on the file detail surface
3. trigger a bounded `bom/reimport` recovery action

That is the concrete “operations/detail surpass” gain for this increment.
