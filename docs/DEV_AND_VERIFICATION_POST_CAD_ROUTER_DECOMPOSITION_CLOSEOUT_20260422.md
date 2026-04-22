# Post CAD Router Decomposition Closeout

Date: 2026-04-22

## 1. Goal

Close the CAD router decomposition sequence after PR #364.

This document records post-cycle validation only. It does not introduce runtime behavior.

## 2. Current State

Current `main` includes:

- PR #353: CAD backend profile router split
- PR #354: CAD connectors router split
- PR #355: CAD sync template router split
- PR #356: CAD file data router split
- PR #357: CAD mesh stats router split
- PR #358: CAD properties router split
- PR #359: CAD review router split
- PR #360: CAD diff router split
- PR #361: CAD history router split
- PR #362: CAD view-state router split
- PR #363: CAD checkin router split
- PR #364: CAD import router split
- PR #365: next-cycle TODO plan

`cad_router.py` is now a zero-route compatibility shell. It remains registered and importable so route ownership contract tests can assert that split routers own the CAD API surface.

## 3. Route Ownership Snapshot

Measured router sizes after decomposition:

| Router | LOC | Ownership |
| --- | ---: | --- |
| `cad_import_router.py` | 924 | `POST /cad/import` |
| `cad_backend_profile_router.py` | 426 | CAD backend profiles and capabilities |
| `cad_checkin_router.py` | 294 | checkout, undo-checkout, checkin, checkin-status |
| `cad_view_state_router.py` | 216 | CAD file view-state read/update |
| `cad_sync_template_router.py` | 176 | CAD sync template read/update |
| `cad_file_data_router.py` | 162 | CAD manifest/document/BOM file reads |
| `cad_mesh_stats_router.py` | 115 | CAD mesh stats |
| `cad_review_router.py` | 88 | CAD review read/write |
| `cad_properties_router.py` | 87 | CAD properties read/update |
| `cad_connectors_router.py` | 80 | connector catalog and capability matrix |
| `cad_diff_router.py` | 72 | CAD diff read |
| `cad_history_router.py` | 60 | CAD file history |
| `cad_router.py` | 23 | compatibility shell, zero owned routes |

## 4. Verification

Commands:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_backend_profile_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_connectors_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_diff_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_file_data_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_history_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_import_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_mesh_stats_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_properties_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_review_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_sync_template_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_view_state_router_contracts.py

.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Results:

- CAD split router ownership contracts: `36 passed in 5.67s`
- Pact provider verification: `1 passed in 10.94s`
- Doc index contracts: `3 passed in 0.02s`

Pact provider emitted only existing deprecation warnings from legacy relationship imports and websockets dependencies.

## 5. Acceptance

| Check | Status |
| --- | --- |
| Split routers own all CAD routes | Pass |
| `cad_router.py` owns no CAD routes | Pass |
| `create_app()` registration remains duplicate-free for moved CAD routes | Pass |
| Pact provider remains green | Pass |
| Delivery documentation is indexed | Pass |
| Shared-dev first-run bootstrap was not run | Pass |

## 6. Follow-Up

Immediate next work should follow `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260422.md`:

1. P0.5 backlog triage.
2. External signal collection.
3. BOM router decomposition taskbook.

Do not delete the `cad_router.py` compatibility shell in the next PR. Removing that shell is a separate compatibility cleanup and should wait until the next-cycle backlog triage explicitly selects it.
