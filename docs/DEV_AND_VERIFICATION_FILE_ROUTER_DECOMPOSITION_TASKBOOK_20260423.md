# File Router Decomposition Taskbook - Development And Verification

Date: 2026-04-23

## 1. Goal

Create a bounded taskbook for the new backend hotspot reduction cycle focused on `file_router.py`.

The first implementation slice is R1 conversion route extraction.

## 2. Evidence

Current `main` after PR #382 shows:

- `file_router.py`: about 1982 LOC;
- `eco_router.py`: about 1417 LOC;
- `parallel_tasks_service.py`: about 11809 LOC.

`file_router.py` is the best first target because it has cohesive route families and existing focused tests for conversion, upload preview queueing, viewer readiness, and attachment lock guards.

## 3. Decision

Start with File Router R1 conversion split.

Reasons:

- conversion routes are cohesive;
- existing tests already isolate meta job queue behavior;
- the route family has legacy compatibility requirements that should be contract-pinned;
- R1 is small enough to review and roll back.

## 4. Taskbook

Implementation taskbook:

- `docs/DEVELOPMENT_CLAUDE_TASK_FILE_ROUTER_DECOMPOSITION_20260423.md`

## 5. Verification

Taskbook verification is documentation-only plus route-scope inspection.

Required checks:

```bash
git diff --check

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

## 6. Non-Goals

- No scheduler production enablement.
- No shared-dev `142` mutation.
- No UI work.
- No file upload or attachment behavior changes in the taskbook itself.

