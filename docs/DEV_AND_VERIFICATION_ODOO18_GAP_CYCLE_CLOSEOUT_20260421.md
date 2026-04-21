# DEV / Verification - Odoo18 Gap Cycle Closeout - 2026-04-21

## 1. Goal

Close the 2026-04-20 Odoo18 gap-analysis implementation cycle on current `main`.

This document is a release-style closeout record. It does not introduce new runtime behavior.

Baseline:

- source gap document: `docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260420.md`
- current main at closeout: `4757a2c test: fix report locale auth middleware noise (#340)`
- scope discipline: Part / BOM / Rev / ECO / Doc / CAD mainline only

## 2. Gap Status

| Gap item | Closeout status | Evidence |
| --- | --- | --- |
| §一.1 Auto numbering | Closed | `DEV_AND_VERIFICATION_AUTO_NUMBERING_LATEST_RELEASED_GUARD_20260420.md`, `DEV_AND_VERIFICATION_NUMBERING_FLOOR_DB_PUSHDOWN_20260421.md`, `DEV_AND_VERIFICATION_PR294_AUTO_NUMBERING_MERGE_20260421.md`, `DEV_AND_VERIFICATION_PR309_NUMBERING_FLOOR_DB_PUSHDOWN_MERGE_20260421.md`, PR #294, #309 |
| §一.2 Latest released write-time guard | Closed | `DEV_AND_VERIFICATION_AUTO_NUMBERING_LATEST_RELEASED_GUARD_20260420.md`, PR #294 |
| §一.3 Suspended lifecycle guard | Closed | `DEV_AND_VERIFICATION_LIFECYCLE_SUSPENDED_GUARD_20260421.md`, `DEV_AND_VERIFICATION_SHARED_DEV_142_POST_MERGE_PR310_SMOKE_20260421.md`, PR #310, #311 |
| §一.4 ECO escalation scheduler path | Closed for current backend scope | `DEV_AND_VERIFICATION_LIGHTWEIGHT_SCHEDULER_FOUNDATION_20260421.md`, `DEV_AND_VERIFICATION_SCHEDULER_DRY_RUN_PREFLIGHT_20260421.md`, `DEV_AND_VERIFICATION_SCHEDULER_AUDIT_RETENTION_ACTIVATION_RUNBOOK_20260421.md`, `DEV_AND_VERIFICATION_SCHEDULER_ECO_ESCALATION_ACTIVATION_RUNBOOK_20260421.md`, `DEV_AND_VERIFICATION_SCHEDULER_LOCAL_ACTIVATION_SUITE_20260421.md`, PR #313-#320 |
| §一.5 BOM to MBOM scheduler path | Closed for current backend scope | `DEV_AND_VERIFICATION_SCHEDULER_BOM_TO_MBOM_HANDLER_20260421.md`, `DEV_AND_VERIFICATION_SCHEDULER_BOM_TO_MBOM_ACTIVATION_RUNBOOK_20260421.md`, `DEV_AND_VERIFICATION_SCHEDULER_LOCAL_ACTIVATION_SUITE_BOM_TO_MBOM_20260421.md`, PR #324, #339 |
| §一.6 BOM dedup + product description i18n | Closed for backend scope | `DEV_AND_VERIFICATION_BOM_IMPORT_DEDUP_AGGREGATION_20260421.md`, `DEV_AND_VERIFICATION_PRODUCT_DESCRIPTION_I18N_HELPER_20260421.md`, `DEV_AND_VERIFICATION_CAD_BOM_IMPORT_I18N_DESCRIPTION_PRESERVATION_20260421.md`, `DEV_AND_VERIFICATION_REPORT_LANGUAGE_SELECTION_20260421.md`, PR #322, #335, #336 |

## 3. Major Delivery Threads

### 3.1 Numbering and write-time guards

- Auto numbering landed with canonical `item_number` behavior.
- Numbering floor allocation was pushed down to DB-level query behavior.
- Latest-released guard blocks downstream writes against invalid target versions.
- Suspended lifecycle guard blocks downstream writes against suspended items.
- Admin dependency duplication was reduced separately in `DEV_AND_VERIFICATION_REQUIRE_ADMIN_DEPENDENCY_DEDUP_20260421.md`.

### 3.2 Scheduler and consumers

The scheduler moved from infrastructure to real consumers:

- lightweight scheduler foundation,
- dry-run preflight,
- audit-retention activation smoke,
- ECO escalation activation smoke,
- jobs API readback smoke,
- BOM to MBOM sync handler,
- BOM to MBOM activation smoke,
- local activation suite with four steps,
- rendered activation suite report.

The scheduler remains default-off for shared-dev and production.

## 4. UOM-Aware Closeout

The UOM cascade is closed across write, read, compare, report, and MBOM surfaces:

| Path | Evidence |
| --- | --- |
| BOM duplicate lines by `(parent, child, uom)` | `DEV_AND_VERIFICATION_BOM_UOM_AWARE_DUPLICATE_GUARD_20260421.md`, `ea1fc2f` |
| BOM compare UOM-aware | `DEV_AND_VERIFICATION_BOM_COMPARE_UOM_AWARE_LINE_KEYS_20260421.md`, `4e3e787` |
| where-used UOM columns | `DEV_AND_VERIFICATION_WHERE_USED_UOM_EXPORT_COLUMNS_20260421.md`, `d8ec66b` |
| rollup child UOM | `DEV_AND_VERIFICATION_BOM_ROLLUP_UOM_CHILD_VISIBILITY_20260421.md`, `77e6380` |
| report BOM flatten UOM buckets | `DEV_AND_VERIFICATION_REPORT_BOM_FLATTEN_UOM_BUCKETS_20260421.md`, `342e326` |
| baseline compare UOM buckets | `DEV_AND_VERIFICATION_BASELINE_COMPARE_UOM_BUCKETS_20260421.md`, `2bf5c9e` |
| BOM merge UOM-aware | `DEV_AND_VERIFICATION_BOM_MERGE_MBOM_COMPARE_UOM_AWARE_20260421.md`, PR #337 |
| MBOM compare UOM-aware | `DEV_AND_VERIFICATION_BOM_MERGE_MBOM_COMPARE_UOM_AWARE_20260421.md`, PR #337 |
| refdes natural sort hardening | `DEV_AND_VERIFICATION_REFDES_NATURAL_SORT_HARDENING_20260421.md`, PR #338 |

Remaining UOM note:

- transformation rule schema still applies `exclude_items` and `substitute_items` at item-id granularity. This is recorded as a low-priority semantic extension, not a current bug.

## 5. i18n Closeout

The product/report language chain is closed for current backend scope:

- product description i18n helper: `DEV_AND_VERIFICATION_PRODUCT_DESCRIPTION_I18N_HELPER_20260421.md`
- CAD BOM import i18n preservation: `DEV_AND_VERIFICATION_CAD_BOM_IMPORT_I18N_DESCRIPTION_PRESERVATION_20260421.md`, PR #335
- report language selection: `DEV_AND_VERIFICATION_REPORT_LANGUAGE_SELECTION_20260421.md`, PR #336
- auth test hygiene for local report/locale router tests: `DEV_AND_VERIFICATION_REPORT_LOCALE_AUTH_TEST_HYGIENE_20260421.md`, PR #340

Remaining i18n note:

- automatic translation service integration remains out of scope. The backend now preserves, resolves, and consumes language-specific fields; it does not translate text.

## 6. Runtime Evidence

Shared-dev / local smoke records:

- `DEV_AND_VERIFICATION_SHARED_DEV_142_POST_CYCLE_SMOKE_20260421.md`
- `DEV_AND_VERIFICATION_SHARED_DEV_142_POST_MERGE_PR310_SMOKE_20260421.md`
- `DEV_AND_VERIFICATION_SCHEDULER_LOCAL_ACTIVATION_SUITE_BOM_TO_MBOM_20260421.md`
- `DEV_AND_VERIFICATION_REPORT_LOCALE_AUTH_TEST_HYGIENE_20260421.md`

Recent post-merge checks:

- PR #339 CI `contracts`: pass; local post-merge focused scheduler suite contracts: `27 passed`
- PR #340 CI `contracts`: pass; local post-merge report/locale focused set: `58 passed`

## 7. Explicit Non-Goals

These remain deliberately outside this cycle:

- production scheduler enablement,
- shared-dev scheduler activation beyond readonly/no-op/default-off smoke,
- shared-dev first-run bootstrap or baseline refreeze,
- scheduler long-running deployment rollout,
- UI work for BOM diff / CAD viewer / approval templates,
- Odoo-style automatic translation service,
- MES / workorder / sales-side feature expansion,
- router mega-refactor under §二 architecture optimization.

## 8. Follow-Up Backlog

Recommended next cycle candidates:

| Priority | Candidate | Reason |
| --- | --- | --- |
| P0 | Cycle release notes / stakeholder-facing summary | Current document is engineering closeout; external-facing release notes can be shorter and product-oriented. |
| P1 | §二 router decomposition taskbook | `parallel_tasks_router.py`, `cad_router.py`, `bom_router.py`, and `file_router.py` remain review/maintenance hotspots. |
| P2 | Transformation rules UOM granularity | Only needed if operations require UOM-specific exclude/substitute behavior during EBOM to MBOM transformation. |
| P3 | Production scheduler enablement plan | Requires separate operations decision, rollout gates, and monitoring; not implied by this cycle. |

## 9. Verification Commands

Doc-index contracts:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Current cycle focused smoke references:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_scheduler_local_activation_suite_contracts.py \
  src/yuantus/meta_engine/tests/test_scheduler_local_activation_suite_report_contracts.py \
  src/yuantus/meta_engine/tests/test_scheduler_bom_to_mbom_activation_smoke_contracts.py \
  src/yuantus/meta_engine/tests/test_locale_router.py \
  src/yuantus/meta_engine/tests/test_report_router_permissions.py
```

## 10. Closeout Decision

This cycle is complete for backend parity scope.

Do not start another gap item inside this cycle. New work should begin as a separate bounded increment with its own taskbook or implementation PR.
