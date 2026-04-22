# Next Cycle Development and TODO Plan

Date: 2026-04-22

## 1. Current State

Current `main` is synced through PR #364.

- CAD router decomposition R1-R12 is complete.
- `cad_router.py` is now a zero-route compatibility shell.
- `cad_import_router.py` owns `POST /api/v1/cad/import`.
- The Odoo18 gap cycle §一.1-§一.6 backend scope is closed by the existing closeout documents.
- Local-only `.claude/` and `local-dev-env/` remain untracked and must not be committed.

## 2. Next Priorities

### P0: Closeout Validation

Goal: confirm the recent CAD router decomposition remains stable on `main`.

TODO:

- Run all CAD split router ownership contracts.
- Run pact provider verification.
- Run doc index contracts.
- If shared-dev 142 credentials are available, run readonly smoke only; do not run bootstrap.
- Produce:

`docs/DEV_AND_VERIFICATION_POST_CAD_ROUTER_DECOMPOSITION_CLOSEOUT_20260422.md`

### P0.5: Backlog Triage

Goal: categorize items carried forward from recent cycles into `do / dormant / delete / wait-for-external-signal`, so each item has an explicit disposition instead of being carried as open load.

Items to review:

- Scheduler infrastructure and its three consumers.
- UOM transformation rules granularity (low-priority audit follow-up).
- CadImportService extraction (P3 candidate).
- BOM router decomposition (P1 candidate).
- Shared-dev 142 real-world observations, if any.
- UI / frontend change requests, if any.

Output:

- A single decision table: one row per item, columns `item / current state / action / reason`.
- No new features, no new tests, no new ops tooling in this step.

Suggested output:

`docs/DEV_AND_VERIFICATION_BACKLOG_TRIAGE_20260422.md`

### P1: BOM Router Decomposition Taskbook

Goal: start §二 architecture reduction with the next high-value router hotspot.

Current hotspot:

- `bom_router.py` is about 2146 LOC.
- Responsibilities are mixed across tree/explode, compare, where-used, import, and effectivity.

Recommended first slice:

- Write a taskbook before moving code.
- Split BOM compare first.
- Add route ownership contracts.
- Preserve public API paths.

Suggested taskbook:

`docs/DEVELOPMENT_CLAUDE_TASK_BOM_ROUTER_DECOMPOSITION_20260422.md`

### P2: UOM Transformation Rules Granularity

Goal: close the remaining low-priority UOM-aware semantic edge.

Current state:

- BOM duplicate guard, compare, where-used, rollup, report flatten, and MBOM compare are UOM-aware.
- EBOM-to-MBOM transformation rules still apply `exclude_items` and `substitute_items` at item-id granularity.

TODO:

- Keep legacy item-id rules compatible.
- Add optional `(item_id, uom)` bucket rules.
- Ensure old rule behavior remains unchanged.
- Add real-session tests.

### P3: CadImportService Extraction

Goal: reduce `cad_import_router.py` complexity after route ownership is complete.

Current state:

- CAD import has been split out of the aggregate router.
- `cad_import_router.py` is still about 924 LOC and contains substantial business logic.

TODO:

- Write a taskbook before implementation.
- Extract `CadImportService`.
- Keep the router focused on Form parsing, dependencies, and HTTP mapping.
- Preserve import lock guards, dedup index payload, quota behavior, auto Part creation, and job enqueueing.

### P4: Scheduler Production Decision Gate

Goal: make an explicit go / no-go decision on scheduler production enablement, instead of continuing to write enablement plans.

This replaces the previous "enablement plan" framing. The prior framing risked "planning about planning" — producing more documentation without ever converging to a production trigger.

Decision gate (within 30 days of the gate PR):

- If a pilot owner, a pilot environment, and an operations commitment are all present: enter scheduler production rehearsal via a separate taskbook.
- If any of the three is missing: mark scheduler as `default-off maintenance`, stop investing in new scheduler ops PRs until a pull signal appears.

Constraints during the decision period:

- Keep scheduler default-off.
- Treat shared-dev 142 as readonly / no-op unless explicitly authorized.
- Do not enable production scheduler in the decision gate PR.

Suggested output:

`docs/DEV_AND_VERIFICATION_SCHEDULER_PRODUCTION_DECISION_GATE_20260422.md`

## 3. External Signal Collection

This section is not a feature expansion into MES / sales / procurement. It is a parallel activity to gather real deployment / customer / internal user feedback that calibrates the priorities above, so the internal work does not drift away from the actual pull signal.

Key questions to collect signal on:

- Does BOM router decomposition (P1) affect any current delivery timeline?
- Is there a real adopter ready to run scheduler in production (required input to the P4 decision gate)?
- Is CAD backend / profile customer-side selection already sufficient, or are there outstanding requests?
- What is the next customer-visible value — BOM, CAD import, approval / ops, or something else?

Collection methods (non-exhaustive):

- Stakeholder or pilot-owner check-in.
- Deployment telemetry from shared-dev `142`, readonly only.
- Internal operator or developer pain-point review.
- Cross-check with the P0.5 backlog triage output.

Output:

- A brief external signal summary. No PR, no feature, no new service.

Suggested output:

`docs/DEV_AND_VERIFICATION_EXTERNAL_SIGNAL_COLLECTION_20260422.md`

## 4. Recommended Execution Order

1. `POST_CAD_ROUTER_DECOMPOSITION_CLOSEOUT` documentation and validation (P0).
2. Backlog triage decision table (P0.5).
3. External signal collection summary (parallel to step 2).
4. `BOM_ROUTER_DECOMPOSITION_TASKBOOK` (P1).
5. BOM compare split as the first BOM router implementation slice (P1 first slice).
6. UOM transformation rules taskbook (P2).
7. CadImportService extraction taskbook (P3).
8. Scheduler production decision gate (P4; its outcome is conditional on steps 2 and 3).

## 5. Fixed PR Requirements

Every bounded PR should include:

- Independent branch.
- Development and verification MD.
- `docs/DELIVERY_DOC_INDEX.md` registration.
- Focused tests.
- Doc index contracts.
- Pact provider verification when API or CAD surface changes.
- Post-merge focused regression.

## 6. Recommended Verification Commands

Doc index contracts:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Pact provider:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py
```

CAD split ownership:

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
```

Whitespace:

```bash
git diff --check
```

## 7. Explicit Non-Goals

Do not do these in the immediate next cycle:

- Do not delete the `cad_router.py` compatibility shell.
- Do not start UI work.
- Do not enable production scheduler.
- Do not run shared-dev first-run bootstrap.
- Do not expand into MES, sales, or procurement.
- Do not mix BOM, file, and ECO router decomposition in one PR.

## 8. Collaboration Defaults

- Claude can continue bounded implementation.
- Codex owns taskbook review, PR review, focused regression, 142 readonly smoke decisions, and merge validation.
- Each implementation should remain small enough for independent review and rollback.
