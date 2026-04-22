# DEVELOPMENT Task - Router Decomposition - 2026-04-22

## 1. Goal

Start §二 architecture optimization from `docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260420.md` with a bounded router decomposition plan.

This taskbook is intentionally a planning gate before code movement. The first implementation PR should be small enough to review without revalidating the full PLM cycle.

## 2. Current Inventory

Measured on `main` after PR #342:

| Router | LOC | Route decorators | Notes |
| --- | ---: | ---: | --- |
| `src/yuantus/meta_engine/web/parallel_tasks_router.py` | 4202 | 87 | doc-sync, ECO activity, workflow action, consumption, breakage/helpdesk, workorder docs, CAD overlays, parallel ops all share one file |
| `src/yuantus/meta_engine/web/cad_router.py` | 2500 | 24 | connector/profile/capabilities, sync-template, file metadata, import, checkout/checkin |
| `src/yuantus/meta_engine/web/bom_router.py` | 2146 | 29 | effective/version tree, EBOM/MBOM convert, children, obsolete, rollup, where-used, compare, substitutes, summarized snapshots |
| `src/yuantus/meta_engine/web/file_router.py` | 1982 | 27 | upload, metadata, preview/geometry/assets, conversion queue, attach/detach, legacy process CAD |
| `src/yuantus/meta_engine/web/eco_router.py` | 1417 | 41 | stages, approvals dashboard/audit/export, ECO CRUD, impact, apply, suspend/unsuspend, move stage |

Application registration is centralized in `src/yuantus/api/app.py` through `app.include_router(..., prefix="/api/v1")`. Endpoint compatibility must be preserved there.

## 3. Recommended First Increment

Implement **R1: split doc-sync routes out of `parallel_tasks_router.py`**.

Rationale:

- `parallel_tasks_router.py` is the largest hotspot and has the highest endpoint count.
- The first 11 endpoints form a coherent `/doc-sync/*` slice.
- The slice already has a distinct prefix family and can be moved without changing public paths.
- It avoids touching CAD/BOM/ECO runtime semantics in the same PR.

R1 target files:

- new `src/yuantus/meta_engine/web/parallel_tasks_doc_sync_router.py`
- updated `src/yuantus/meta_engine/web/parallel_tasks_router.py`
- updated `src/yuantus/api/app.py`
- focused tests for route compatibility and imports
- dev/verification MD and `DELIVERY_DOC_INDEX.md`

## 4. R1 Route Boundary

Move these endpoints as-is:

| Method | Path |
| --- | --- |
| POST | `/doc-sync/sites` |
| GET | `/doc-sync/sites` |
| POST | `/doc-sync/sites/{site_id}/health` |
| POST | `/doc-sync/jobs` |
| GET | `/doc-sync/jobs` |
| GET | `/doc-sync/jobs/dead-letter` |
| POST | `/doc-sync/jobs/replay-batch` |
| GET | `/doc-sync/summary` |
| GET | `/doc-sync/summary/export` |
| GET | `/doc-sync/jobs/{job_id}` |
| POST | `/doc-sync/jobs/{job_id}/replay` |

Public URLs must remain unchanged:

- before: `app.include_router(parallel_tasks_router, prefix="/api/v1")`
- after: `app.include_router(parallel_tasks_doc_sync_router, prefix="/api/v1")` plus existing `parallel_tasks_router`

The new router should keep `tags=["ParallelTasks"]` unless a reviewer explicitly decides to introduce a new tag. Avoid tag churn in R1.

## 5. Implementation Constraints

- Do not change request/response schemas.
- Do not change permission/auth dependencies.
- Do not change service calls, default query parameters, exports, or HTTP status mapping.
- Do not rename public endpoints.
- Do not collapse or rewrite business logic while moving routes.
- Do not move unrelated `/eco-activities`, `/workflow-actions`, `/consumption`, `/breakages`, `/workorder-docs`, `/cad-3d`, or `/parallel-ops` endpoints in R1.
- Do not add new settings, migrations, tables, or scheduler behavior.

## 6. Compatibility Contract

R1 must prove that route movement is behavior-preserving:

1. The doc-sync endpoint set is identical before and after when mounted with `/api/v1`.
2. `parallel_tasks_router.py` no longer contains `/doc-sync` route decorators.
3. `parallel_tasks_doc_sync_router.py` owns all `/doc-sync` route decorators.
4. Existing tests that patch `yuantus.meta_engine.web.parallel_tasks_router` need explicit review. If a moved endpoint has tests patching old module symbols, update those tests to patch the new module path.
5. No duplicate route registration for `/doc-sync/*`.

Recommended focused tests:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

If route-contract tests do not already cover the moved endpoints, add one small test that mounts both routers on a `FastAPI()` test app and asserts the expected `/api/v1/doc-sync/*` route paths exist exactly once.

## 7. Suggested PR Sequence

| PR | Scope | Reason |
| --- | --- | --- |
| R1 | Split `parallel_tasks_doc_sync_router.py` | Lowest-risk proof that the router split pattern works |
| R2 | Split `parallel_tasks_breakage_router.py` | Biggest remaining cluster inside the same mega-router |
| R3 | Split `parallel_tasks_ops_router.py` | Parallel ops read/export cluster |
| R4 | Split `cad_router.py` into profile/capabilities/import/checkin slices | CAD router has cross-cutting helpers; defer until R1-R3 pattern is stable |
| R5 | Split `bom_router.py` compare/snapshot endpoints | BOM compare has heavy helper logic and many tests |
| R6 | Split `file_router.py` conversion/asset/attachment endpoints | File paths touch storage and conversion queue; defer |
| R7 | Slim `eco_router.py` approvals/dashboard/apply slices | ECO has the highest behavioral risk despite lower LOC |

## 8. Acceptance Criteria

- R1 reduces `parallel_tasks_router.py` by at least the doc-sync route block without changing public API paths.
- `src/yuantus/api/app.py` registers both routers explicitly.
- Focused tests pass locally.
- CI `contracts` passes.
- Dev/verification MD documents moved routes, unchanged paths, and tests.
- No shared-dev or 142 smoke is required for R1 unless runtime code beyond route movement changes.

## 9. Review Checklist

Reviewers should verify:

- No endpoint path, method, query parameter, response model, or status mapping changed.
- No auth dependency was weakened or silently removed.
- Import cycles were not introduced.
- Tests patch the new module path for moved route internals.
- `parallel_tasks_router.py` still exports `parallel_tasks_router` for remaining endpoints.
- The new module name is explicit and domain-scoped, not generic.

## 10. Non-Goals

- Full router rearchitecture in one PR.
- Service-layer rewrites.
- Business logic cleanup hidden inside route movement.
- Production behavior changes.
- OpenAPI tag redesign.
- API versioning changes.

## 11. Suggested Claude Code CLI Prompt

Use this prompt for implementation:

```text
Implement R1 from docs/DEVELOPMENT_CLAUDE_TASK_ROUTER_DECOMPOSITION_20260422.md.

Move only the /doc-sync/* endpoints from src/yuantus/meta_engine/web/parallel_tasks_router.py into a new src/yuantus/meta_engine/web/parallel_tasks_doc_sync_router.py.

Preserve public paths, methods, schemas, auth dependencies, service calls, HTTP status behavior, and tags. Update src/yuantus/api/app.py to include the new router with prefix="/api/v1" while keeping the existing parallel_tasks_router for all remaining endpoints.

Add or update focused route-contract tests so /api/v1/doc-sync/* paths exist exactly once and parallel_tasks_router.py no longer owns doc-sync route decorators. Update any tests that patch moved internals to the new module path.

Do not move any non-doc-sync routes. Do not rewrite business logic. Add a DEV_AND_VERIFICATION MD and update DELIVERY_DOC_INDEX.md. Run focused tests and report results.
```
