# DEV / Verification - Router Decomposition Taskbook - 2026-04-22

## 1. Goal

Create a bounded taskbook for §二 router decomposition after the Odoo18 gap cycle closeout.

This PR is docs-only. It does not refactor routers yet.

## 2. Inventory Performed

The taskbook is based on direct repository inspection, not only on the prior gap-analysis prose.

Measured router hotspots:

| Router | LOC | Route decorators |
| --- | ---: | ---: |
| `parallel_tasks_router.py` | 4202 | 87 |
| `cad_router.py` | 2500 | 24 |
| `bom_router.py` | 2146 | 29 |
| `file_router.py` | 1982 | 27 |
| `eco_router.py` | 1417 | 41 |

Confirmed registration point:

- `src/yuantus/api/app.py` imports and mounts the target routers with `prefix="/api/v1"`.

## 3. Deliverables

Files added:

- `docs/DEVELOPMENT_CLAUDE_TASK_ROUTER_DECOMPOSITION_20260422.md`
- `docs/DEV_AND_VERIFICATION_ROUTER_DECOMPOSITION_TASKBOOK_20260422.md`

File updated:

- `docs/DELIVERY_DOC_INDEX.md`

## 4. Decision

The first implementation increment should be **R1: split `/doc-sync/*` endpoints from `parallel_tasks_router.py` into `parallel_tasks_doc_sync_router.py`**.

Reason:

- `parallel_tasks_router.py` is the largest hotspot.
- `/doc-sync/*` is a coherent 11-endpoint slice at the top of the file.
- Public route compatibility can be tested without touching CAD/BOM/ECO runtime behavior.

## 5. Non-Goals

This PR does not:

- move any Python route code,
- change FastAPI app registration,
- alter OpenAPI behavior,
- change auth,
- touch service-layer logic,
- run 142/shared-dev smoke.

## 6. Verification

Commands:

```bash
git diff --check

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Expected result:

- whitespace check passes,
- new `DEV_AND_VERIFICATION` MD is indexed,
- all indexed paths resolve,
- Development & Verification section remains sorted.

## 7. Follow-Up

After this taskbook merges, assign R1 to Claude Code CLI or a bounded worker branch. The review gate for R1 should focus on route compatibility, duplicate route registration, and absence of hidden business-logic rewrites.
