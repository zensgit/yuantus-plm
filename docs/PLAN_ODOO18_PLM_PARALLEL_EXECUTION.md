# Yuantus Odoo18 PLM Parallel Execution Plan

## Goal Snapshot
- 目标一：在当前真实代码基线上持续收口 Odoo18 PLM 对标能力
- 目标二：把 Claude 已完成分支按模块边界安全并入统一集成栈
- 当前工作分支：`main`

## Baseline Correction
- 当前仓库真实基线与此前长链路摘要不一致。
- 本分支没有 `revision-workbench` / `change-release/execute` 这一整条热主线。
- 因此本轮不再继续沿用那条不存在的基线，而是改为：
  - 先并入 Claude 已完成且低冲突的 `C6 locale bootstrap`
  - 再把 locale 能力接到当前真实存在的 `workorder-docs/export`

## Current Sprint
- `C6` locale/report bootstrap：completed on this branch
- `P2-A` workorder export locale pipeline：completed on this branch
- `P2-A` parallel-ops summary/trends locale pipeline：completed on this branch
- `P2-A` breakage metrics/groups locale pipeline：completed on this branch
- `P2-A` breakage incidents locale pipeline：completed on this branch
- unified stack regression automation：completed on this branch
- `C7` BOM compare hardening：merged and verified on this branch (`58f8db7`, `0a0a2eb`)
- `C8` quality-mrp integration：merged and verified on this branch (`f918784`, `12f5b9b`, `a7139ff`)
- `C9` maintenance-workcenter readiness：merged and verified on this branch (`736e612`, `b32ed6e`)
- `C10` locale description resolver：completed on this branch after Codex integration verification
- `C11` file/3D consumer hardening：completed on this branch
- `C12` generic approvals bootstrap：completed on this branch
- `C13` subcontracting bootstrap：completed on this branch
- `C14` approvals export / ops-report bootstrap：completed on this branch
- `C15` subcontracting analytics / export bootstrap：completed on this branch
- `C16` quality SPC / analytics bootstrap：completed on this branch
- `C17/C18/C19` greenfield candidate stack：merged into `main`
- post-merge stabilization refresh：completed on this branch
- next Claude greenfield batch `C20/C21/C22`：merged on `main`
- next Claude greenfield batch `C23/C24/C25`：merged on `main` and post-merge verified
- next Claude greenfield batch `C26/C27/C28`：merged on `main` and stabilization accepted
- next Claude greenfield batch `C29/C30/C31`：stabilization accepted on `main`
- next Claude greenfield batch `C32/C33/C34`：stabilization accepted on `main`
- next Claude greenfield batch `C35/C36/C37`：stabilization accepted on `main`
- next Claude greenfield batch `C38/C39/C40`：stabilization accepted on `main`
- next Claude greenfield batch `C41/C42/C43`：stabilization accepted on `main`
- next Claude greenfield batch `C44/C45/C46`：stabilization accepted on `main`

## Priority Matrix
| Task ID | Priority | Target | Subsystem | Status |
| --- | --- | --- | --- | --- |
| C6 | P2 | locale/report bootstrap | `locale` + `report_locale` + `locale_router` | completed |
| P2-A | P2 | locale/report helpers | `parallel_tasks` workorder export + parallel-ops export locale integration | completed |
| C7 | P1 | BOM compare & summary hardening | `bom_router` + summarized snapshot regression pack | completed_on_stack_branch |
| C8 | P1 | quality-mrp integration | `quality` + manufacturing integration edge | completed_on_stack_branch |
| C9 | P1 | maintenance-workcenter readiness | `maintenance` + workcenter integration edge | completed_on_stack_branch |
| C10 | P2 | locale description resolver | `locale` description/read-model helpers | completed |
| C11 | P1 | file/3D consumer hardening | `file_router` + file viewer tests | completed_on_this_branch |
| C12 | P2 | generic approvals bootstrap | new `approvals` module + router + tests | completed_on_this_branch |
| C13 | P2 | subcontracting bootstrap | new `subcontracting` module + router + tests | completed_on_this_branch |
| C14 | P2 | approvals export / ops-report | `approvals` service + router + tests | completed_on_this_branch |
| C15 | P2 | subcontracting analytics / export | `subcontracting` service + router + tests | completed_on_this_branch |
| C16 | P2 | quality SPC / analytics | `quality` analytics services + analytics router + tests | completed_on_this_branch |
| C17 | P2 | PLM box bootstrap | new `box` module + router + tests | merged_on_main_greenfield |
| C18 | P2 | document multi-site sync bootstrap | new `document_sync` module + router + tests | merged_on_main_greenfield |
| C19 | P2 | cutted-parts bootstrap | new `cutted_parts` module + router + tests | merged_on_main_greenfield |
| C20 | P2 | PLM box analytics / export | `box` analytics/read-model/export helpers | merged_on_main_greenfield |
| C21 | P2 | document sync analytics / export | `document_sync` analytics/conflict/export helpers | merged_on_main_greenfield |
| C22 | P2 | cutted-parts analytics / export | `cutted_parts` analytics/waste/export helpers | merged_on_main_greenfield |
| C23 | P3 | PLM box ops-report / transitions | `box` ops-report/state-transition/export helpers | merged_on_main_greenfield |
| C24 | P3 | document sync reconciliation | `document_sync` reconciliation/conflict-resolution/export helpers | merged_on_main_greenfield |
| C25 | P3 | cutted-parts cost / utilization | `cutted_parts` utilization/cost/export helpers | merged_on_main_greenfield |
| C26 | P3 | PLM box reconciliation / audit | `box` reconciliation/audit/export helpers | merged_on_main_greenfield |
| C27 | P3 | document sync replay / audit | `document_sync` replay/audit/export helpers | merged_on_main_greenfield |
| C28 | P3 | cutted-parts templates / scenarios | `cutted_parts` template/scenario/export helpers | merged_on_main_greenfield |
| C29 | P3 | PLM box capacity / compliance | `box` capacity/compliance/export helpers | merged_on_main_greenfield |
| C30 | P3 | document sync drift / snapshots | `document_sync` drift/snapshot/export helpers | merged_on_main_greenfield |
| C31 | P3 | cutted-parts benchmark / quote | `cutted_parts` benchmark/quote/export helpers | merged_on_main_greenfield |
| C32 | P3 | PLM box policy / exceptions | `box` policy/exception/export helpers | merged_on_main_greenfield |
| C33 | P3 | document sync baseline / lineage | `document_sync` baseline/lineage/export helpers | merged_on_main_greenfield |
| C34 | P3 | cutted-parts variance / recommendations | `cutted_parts` variance/recommendation/export helpers | merged_on_main_greenfield |
| C35 | P3 | PLM box reservations / traceability | `box` reservation/traceability/export helpers | merged_on_main_greenfield |
| C36 | P3 | document sync checkpoints / retention | `document_sync` checkpoint/retention/export helpers | merged_on_main_greenfield |
| C37 | P3 | cutted-parts thresholds / envelopes | `cutted_parts` threshold/envelope/export helpers | merged_on_main_greenfield |
| C38 | P3 | PLM box allocation / custody | `box` allocation/custody/export helpers | merged_on_main_greenfield |
| C39 | P3 | document sync freshness / watermarks | `document_sync` freshness/watermark/export helpers | merged_on_main_greenfield |
| C40 | P3 | cutted-parts alerts / outliers | `cutted_parts` alert/outlier/export helpers | merged_on_main_greenfield |
| C41 | P3 | PLM box occupancy / turnover | `box` occupancy/turnover/export helpers | merged_on_main_greenfield |
| C42 | P3 | document sync lag / backlog | `document_sync` lag/backlog/export helpers | merged_on_main_greenfield |
| C43 | P3 | cutted-parts throughput / cadence | `cutted_parts` throughput/cadence/export helpers | merged_on_main_greenfield |
| C44 | P3 | PLM box dwell / aging | `box` dwell/aging/export helpers | merged_on_main_greenfield |
| C45 | P3 | document sync skew / gaps | `document_sync` skew/gap/export helpers | merged_on_main_greenfield |
| C46 | P3 | cutted-parts saturation / bottlenecks | `cutted_parts` saturation/bottleneck/export helpers | merged_on_main_greenfield |

## Increment 2026-03-18 Codex-P2A-Locale-Export
- Imported `C6` files into this branch from `e28b47d`
- Registered `locale_router` in `src/yuantus/api/app.py`
- Extended `GET /api/v1/workorder-docs/export` with:
  - `report_lang`
  - `report_type`
  - `locale_profile_id`
- Extended `WorkorderDocumentPackService.export_pack(...)` with locale profile resolution
- Added:
  - `manifest.locale`
  - `locale.json` in zip bundles
  - locale block in PDF export payload text

## Increment 2026-03-18 Codex-P2A-Parallel-Ops-Locale
- Extended `ParallelOpsOverviewService.export_summary(...)` with:
  - `report_lang`
  - `report_type`
  - `locale_profile_id`
- Extended `ParallelOpsOverviewService.export_trends(...)` with the same locale contract
- Extended:
  - `GET /api/v1/parallel-ops/summary/export`
  - `GET /api/v1/parallel-ops/trends/export`
- Locale behavior:
  - JSON exports add `locale`
  - Markdown exports add `## Locale`
  - CSV exports remain unchanged

## Increment 2026-03-18 Codex-P2A-Breakage-Metrics-Locale
- Extended `BreakageIncidentService.export_metrics(...)` with:
  - `report_lang`
  - `report_type`
  - `locale_profile_id`
- Extended `BreakageIncidentService.export_metrics_groups(...)` with the same locale contract
- Extended:
  - `GET /api/v1/breakages/metrics/export`
  - `GET /api/v1/breakages/metrics/groups/export`
- Locale behavior:
  - JSON exports add `locale`
  - Markdown exports add `## Locale`
  - CSV exports remain unchanged

## Increment 2026-03-18 Codex-P2A-Breakage-Incidents-Locale
- Extended `BreakageIncidentService.export_incidents(...)` with:
  - `report_lang`
  - `report_type`
  - `locale_profile_id`
- Extended:
  - `GET /api/v1/breakages/export`
- Locale behavior:
  - JSON exports add `locale`
  - Markdown exports add `## Locale`
  - CSV exports remain unchanged

## Increment 2026-03-18 Codex-C10-Locale-Resolver
- Integrated Claude `C10` resolve helpers into current locale branch
- Extended `LocaleService` with:
  - `resolve_translation(...)`
  - `resolve_translations_batch(...)`
  - `fallback_preview(...)`
- Extended `ReportLocaleService` with:
  - `get_export_context(...)`
- Extended locale APIs:
  - `POST /api/v1/locale/translations/resolve`
  - `GET /api/v1/locale/translations/fallback-preview`
  - `GET /api/v1/locale/export-context`


## Increment 2026-03-19 Codex-C7-C8-C9-Integration
- `C7` integrated on `feature/codex-c7-bom-compare-integration`
  - imported branch-local summarized snapshot regression files
  - verified `24 passed` across summarized snapshot + delta BOM pack
- `C8` integrated on `feature/codex-c8-quality-integration`
  - registered `quality_router` in `src/yuantus/api/app.py`
  - replaced deprecated `dict()` with `model_dump()`
  - verified `32 passed` in quality service/router pack
- `C9` integrated on `feature/codex-c9-maintenance-integration`
  - imported missing `maintenance` model package from `C5` bootstrap
  - registered `maintenance_router` in `src/yuantus/api/app.py`
  - verified `35 passed` in maintenance service/router pack

## Increment 2026-03-19 Codex-C7-C8-C9-Stack
- Created `feature/codex-stack-c7c8c9` from the locale/export baseline
- Stacked:
  - `C9` integration commits `d395fb8`, `7340027`
  - `C8` integration commits `0423e03`, `3b971f3`, `7ee9f1e`
  - `C7` integration commits `5c31dd3`, `db781f4`
- Resolved real stack conflicts only in:
  - `contracts/claude_allowed_paths.json`
  - `src/yuantus/api/app.py`
- Conflict strategy:
  - preserved the broader `C1-C13` Claude path-guard matrix
  - kept `locale_router`, `maintenance_router`, and `quality_router` all registered in `create_app()`
- Unified stack regression on this branch:
  - `98 passed, 200 deselected, 54 warnings`

## Next Claude Allocation Draft
- `C7-C13` 已进入统一 stack 集成态
- 经过更大范围交叉回归后，可以重新给 Claude 开新绿地任务
- 下一批只允许在独立域内扩展，不回写当前 stack 热文件
- 推荐顺序：
  - `C14`
  - `C15`
  - `C16`

## Claude Allocation
- `C7/C8/C9/C10` should not be edited further on Claude branches unless a new bugfix branch is explicitly opened.
- `C11` file/3D consumer hardening
  - suggested branch: `feature/claude-c11-file-viewer-consumer`
  - write scope:
    - `src/yuantus/meta_engine/web/file_router.py`
    - `src/yuantus/meta_engine/tests/test_file_viewer_readiness.py`
  - deliverables:
    - viewer readiness export payload
    - geometry asset pack summary
    - consumer-ready field/read model
  - non-goals:
    - no edits to `parallel_tasks`, `quality`, `maintenance`, `locale`
- `C12` generic approvals bootstrap
  - suggested branch: `feature/claude-c12-approvals-bootstrap`
  - write scope:
    - new `src/yuantus/meta_engine/approvals/`
    - new `src/yuantus/meta_engine/web/approvals_router.py`
    - new approval tests
  - deliverables:
    - approval category model
    - approval request model
    - request state transition API
    - pending/list/detail endpoints
  - non-goals:
    - no changes to existing ECO approval hot files
- `C13` subcontracting bootstrap
  - suggested branch: `feature/claude-c13-subcontracting-bootstrap`
  - write scope:
    - new `src/yuantus/meta_engine/subcontracting/`
    - new `src/yuantus/meta_engine/web/subcontracting_router.py`
    - new subcontracting tests
  - deliverables:
    - subcontract order read model
    - vendor assignment fields
    - material issue/receipt skeleton
    - list/detail endpoints
  - non-goals:
    - do not mutate existing `manufacturing/routing_service.py` in the first increment
- `C10` has been integrated and verified on the current Codex branch.

## Claude Allocation Next Batch
- `C14` approvals export / ops-report bootstrap
  - suggested branch: `feature/claude-c14-approvals-export`
  - write scope:
    - `src/yuantus/meta_engine/approvals/`
    - `src/yuantus/meta_engine/web/approvals_router.py`
    - `src/yuantus/meta_engine/tests/test_approvals_*.py`
  - deliverables:
    - approvals list export
    - summary export
    - ops-report/bootstrap diagnostics
  - non-goals:
    - no edits to `eco_router.py`
    - no edits to `eco_service.py`
- `C15` subcontracting analytics / export bootstrap
  - suggested branch: `feature/claude-c15-subcontracting-analytics`
  - write scope:
    - `src/yuantus/meta_engine/subcontracting/`
    - `src/yuantus/meta_engine/web/subcontracting_router.py`
    - `src/yuantus/meta_engine/tests/test_subcontracting_*.py`
  - deliverables:
    - queue / order overview
    - export payload
    - vendor / receipt analytics read model
  - non-goals:
    - no changes to manufacturing core services
- `C16` quality SPC / analytics bootstrap
  - suggested branch: `feature/claude-c16-quality-spc`
  - write scope:
    - `src/yuantus/meta_engine/quality/`
    - `src/yuantus/meta_engine/web/quality_router.py`
    - `src/yuantus/meta_engine/tests/test_quality_*.py`
  - deliverables:
    - SPC-oriented aggregates
    - quality trend/export helpers
    - alert analytics read model
  - non-goals:
    - no edits to `parallel_tasks`
    - no edits to manufacturing hot paths

## Increment 2026-03-19 Codex-C14-C15-Integration
- Integrated `C14` directly on the unified stack branch using the worker-delivered contract:
  - `GET /api/v1/approvals/requests/export`
  - `GET /api/v1/approvals/summary/export`
  - `GET /api/v1/approvals/ops-report`
  - `GET /api/v1/approvals/ops-report/export`
- Integrated `C15` directly on the unified stack branch using the worker-delivered contract:
  - `GET /api/v1/subcontracting/overview`
  - `GET /api/v1/subcontracting/vendors/analytics`
  - `GET /api/v1/subcontracting/receipts/analytics`
  - `GET /api/v1/subcontracting/export/overview`
  - `GET /api/v1/subcontracting/export/vendors`
  - `GET /api/v1/subcontracting/export/receipts`
- Targeted regression:
  - `44 passed, 16 warnings`
- Unified stack regression via script:
  - `191 passed, 68 warnings`
- `C14/C15` should no longer be treated as pending Claude work
- Remaining greenfield Claude batch priority is now:
  - `C16`

## Increment 2026-03-19 Codex-C16-Integration
- Cherry-picked Claude `C16` commit `72d4134`
- Resolved only the expected path-guard conflict in:
  - `contracts/claude_allowed_paths.json`
- Registered `quality_analytics_router` in:
  - `src/yuantus/api/app.py`
- Extended unified stack regression script:
  - `scripts/verify_odoo18_plm_stack.sh`
  - now includes:
    - `test_quality_analytics_service.py`
    - `test_quality_analytics_router.py`
    - `test_quality_spc_service.py`
- Targeted regression:
  - `27 passed, 8 warnings`
- Unified stack regression via script:
  - `218 passed, 75 warnings`
- `C14/C15/C16` are all completed on the unified stack branch
- Recommendation:
  - pause new Claude feature branches until the current stack enters merge-prep

## Increment 2026-03-19 Codex-Merge-Prep-Broader-Regression
- Ran a broader merge-prep regression pack on top of the unified stack:
  - BOM summarized snapshot + delta
  - quality baseline + analytics + SPC
  - maintenance
  - locale/report-locale
  - subcontracting
  - file viewer
  - approvals
  - parallel tasks locale/export pack
- Result:
  - `112 passed, 283 deselected, 62 warnings`
- Merge hotspots currently expected against `main`:
  - `src/yuantus/api/app.py`
  - `contracts/claude_allowed_paths.json`
  - `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
  - `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
  - `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
  - `docs/DELIVERY_DOC_INDEX.md`
- No blocking merge-prep issue found on the unified stack branch
- Current recommendation:
  - stop opening new Claude feature branches
  - move to merge-prep and final wider regression

## Increment 2026-03-19 Next Claude Batch C17-C19
- Merge rehearsal passed on `feature/codex-merge-rehearsal-stack`
- Current unified stack remains frozen for merge-prep and final integration
- Claude can receive new work again, but only in net-new domains:
  - `C17`
  - `C18`
  - `C19`
- Claude greenfield branches should base from:
  - `feature/claude-greenfield-base`
  - current freeze point: `9b312e3`
- Do not branch these tasks from `main`, because `main` does not yet carry the prepared path-guard/docs baseline

### C17
- task: `PLM Box bootstrap`
- suggested branch: `feature/claude-c17-plm-box`
- write scope:
  - `src/yuantus/meta_engine/box/`
  - `src/yuantus/meta_engine/web/box_router.py`
  - `src/yuantus/meta_engine/tests/test_box_*.py`
- non-goals:
  - no edits to `src/yuantus/api/app.py`
  - no edits to `parallel_tasks`, `version`, `benchmark_branches`

### C18
- task: `document multi-site sync bootstrap`
- suggested branch: `feature/claude-c18-document-sync`
- write scope:
  - `src/yuantus/meta_engine/document_sync/`
  - `src/yuantus/meta_engine/web/document_sync_router.py`
  - `src/yuantus/meta_engine/tests/test_document_sync_*.py`
- non-goals:
  - no edits to `src/yuantus/api/app.py`
  - no edits to storage/CAD hot paths

### C19
- task: `cutted-parts bootstrap`
- suggested branch: `feature/claude-c19-cutted-parts`
- write scope:
  - `src/yuantus/meta_engine/cutted_parts/`
  - `src/yuantus/meta_engine/web/cutted_parts_router.py`
  - `src/yuantus/meta_engine/tests/test_cutted_parts_*.py`
- non-goals:
  - no edits to `src/yuantus/api/app.py`
  - no edits to BOM/manufacturing hot services

## Increment 2026-03-19 Codex-C17-Integration
- Created `feature/codex-c17-box-integration` from the frozen unified stack baseline `feature/codex-stack-c11c12`
- Cherry-picked Claude `C17` commit `dfd6a5c`
- Preserved the original greenfield constraint:
  - no `src/yuantus/api/app.py` registration
- Integrated artifacts:
  - `src/yuantus/meta_engine/box/__init__.py`
  - `src/yuantus/meta_engine/box/models.py`
  - `src/yuantus/meta_engine/box/service.py`
  - `src/yuantus/meta_engine/web/box_router.py`
  - `src/yuantus/meta_engine/tests/test_box_service.py`
  - `src/yuantus/meta_engine/tests/test_box_router.py`
- Verification results on the Codex integration branch:
  - box targeted pack:
    - `19 passed, 8 warnings`
  - light cross-pack regression:
    - `66 passed, 53 warnings`

## Increment 2026-03-19 Codex-C19-Integration
- Created `feature/codex-c19-cutted-parts-integration` from the frozen unified stack baseline `feature/codex-stack-c11c12`
- Cherry-picked Claude `C19` commit `e474466`
- Preserved the original greenfield constraint:
  - no `src/yuantus/api/app.py` registration
- Integrated artifacts:
  - `src/yuantus/meta_engine/cutted_parts/__init__.py`
  - `src/yuantus/meta_engine/cutted_parts/models.py`
  - `src/yuantus/meta_engine/cutted_parts/service.py`
  - `src/yuantus/meta_engine/web/cutted_parts_router.py`
  - `src/yuantus/meta_engine/tests/test_cutted_parts_service.py`
  - `src/yuantus/meta_engine/tests/test_cutted_parts_router.py`
- Verification results on the Codex integration branch:
  - cutted-parts targeted pack:
    - `35 passed, 11 warnings`
  - light cross-pack regression:
    - `69 passed, 56 warnings`

## Increment 2026-03-19 Codex-C11-C12-Integration
- Created `feature/codex-stack-c11c12` from the verified `C13` baseline
- Integrated Claude `C11` commit `c21346b`
  - resolved stack conflicts in:
    - `contracts/claude_allowed_paths.json`
    - `src/yuantus/meta_engine/web/file_router.py`
  - restored the missing service contract:
    - `CADConverterService.assess_viewer_readiness(...)`
  - verified:
    - `viewer_readiness`
    - `geometry/assets`
    - `consumer-summary`
    - `viewer-readiness/export`
    - `geometry-pack-summary`
- Integrated Claude `C12` commit `5e4f3f0`
  - preserved the broader `C1-C13` path guard matrix
  - registered `approvals_router` in `src/yuantus/api/app.py`
  - added `create_app()` smoke coverage for approvals routes
- Unified branch regression:
  - `47 passed, 24 warnings` for `C11 + C12`
  - `57 passed, 44 warnings` for `C11 + C12 + locale + quality + maintenance + subcontracting`

## Increment 2026-03-19 Codex-Unified-Stack-C7-C13
- Confirmed `feature/codex-stack-c11c12` contains:
  - locale/export baseline `1ed22a2`
  - `C7-C9` verified stack `2a64ebb`
  - `C13` integration `489396a`
  - `C11/C12` integration commits `1290eeb`, `d0e6d76`, `9e48f35`
- Ran a larger cross-pack regression across:
  - BOM summarized snapshot
  - quality
  - maintenance
  - locale
  - subcontracting
  - file viewer readiness
  - approvals
- Result:
  - `86 passed, 60 warnings`

## Increment 2026-03-19 Codex-Wider-Cross-Regression
- Expanded regression from router-only cross-pack to:
  - BOM summarized snapshot + delta
  - quality service/router
  - maintenance service/router
  - locale/report-locale/router
  - subcontracting service/router
  - file viewer readiness
  - approvals service/router
- Result:
  - `177 passed, 62 warnings`

## Increment 2026-03-19 Codex-Stack-Regression-Automation
- Added reusable regression script:
  - `scripts/verify_odoo18_plm_stack.sh`
- Added manual workflow entrypoint:
  - `.github/workflows/odoo18-plm-stack-regression.yml`
- Script modes:
  - `smoke`
  - `full`
- Current default verification baseline remains `full`, covering:
  - BOM summarized snapshot + delta
  - quality
  - maintenance
  - locale
  - subcontracting
  - file viewer readiness
  - approvals
- Intended use:
  - future `C14/C15/C16` integration should reuse this script before stack merge

## Increment 2026-03-19 Codex-C13-Subcontracting
- Created `feature/codex-c13-subcontracting-integration` from the verified stack baseline
- Added isolated subcontracting bootstrap module:
  - `src/yuantus/meta_engine/subcontracting/models.py`
  - `src/yuantus/meta_engine/subcontracting/service.py`
  - `src/yuantus/meta_engine/web/subcontracting_router.py`
- Registered `subcontracting_router` in `src/yuantus/api/app.py`
- Added service/router/app smoke tests:
  - `src/yuantus/meta_engine/tests/test_subcontracting_service.py`
  - `src/yuantus/meta_engine/tests/test_subcontracting_router.py`
- Verified `9 passed, 3 warnings`

## Increment 2026-03-19 Codex-Merge-Prep-Finalization
- Current unified stack remains `feature/codex-stack-c11c12`
- Merge rehearsal branch `feature/codex-merge-rehearsal-stack` already proved the stack merges cleanly into `main`
- Re-ran both regression baselines after freezing the stack and preparing `C17-C19`:
  - unified stack script:
    - `218 passed, 75 warnings`
  - broader merge-prep pack:
    - `112 passed, 283 deselected, 62 warnings`
- Current execution policy:
  - do not stack more Codex feature work on this branch
  - Claude may open only greenfield branches `C17 -> C18 -> C19`
  - Codex stays on merge-prep, final review, and later greenfield integration

## Increment 2026-03-19 Codex-C18-Integration
- Created `feature/codex-c18-document-sync-integration` from the frozen unified stack baseline `feature/codex-stack-c11c12`
- Cherry-picked Claude `C18` commit `f379e2c`
- Preserved the original greenfield constraint:
  - no `src/yuantus/api/app.py` registration
- Integrated artifacts:
  - `src/yuantus/meta_engine/document_sync/__init__.py`
  - `src/yuantus/meta_engine/document_sync/models.py`
  - `src/yuantus/meta_engine/document_sync/service.py`
  - `src/yuantus/meta_engine/web/document_sync_router.py`
  - `src/yuantus/meta_engine/tests/test_document_sync_service.py`
  - `src/yuantus/meta_engine/tests/test_document_sync_router.py`
- Verification results on the Codex integration branch:
  - document-sync targeted pack:
    - `33 passed, 12 warnings`
  - light cross-pack regression:
    - `70 passed, 57 warnings`

## Increment 2026-03-19 Codex-C17-C18-Stack
- Created `feature/codex-stack-c17c18` from the frozen unified stack baseline `feature/codex-stack-c11c12`
- Stacked:
  - `C17` integration commits `e56736a`, `b6d32bf`
  - `C18` integration commits `36ef954`, `f2534d6`
- Real shared-file conflicts appeared only in:
  - `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
  - `docs/DELIVERY_DOC_INDEX.md`
- Conflict strategy:
  - preserved both `C17` and `C18` status lines in the priority matrix
  - preserved both `C17` and `C18` entries in the delivery index
- Combined verification results on the stack branch:
  - `C17 + C18` targeted pack:
    - `52 passed, 19 warnings`
  - light cross-pack regression:
    - `77 passed, 64 warnings`

## Increment 2026-03-19 Codex-C17-C18-C19-Stack
- Created `feature/codex-stack-c17c18c19` from the verified greenfield candidate stack `feature/codex-stack-c17c18`
- Stacked:
  - `C19` integration commits `ea7af53`, `2f98e1b`
- Real shared-file conflict appeared only in:
  - `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- Conflict strategy:
  - preserved all three `C17` / `C18` / `C19` status lines in the priority matrix
  - preserved both prior `C17` / `C18` candidate-stack notes and added the `C19` integration record
- Combined verification results on the stack branch:
  - `C17 + C18 + C19` targeted pack:
    - `87 passed, 29 warnings`
  - light cross-pack regression:
    - `87 passed, 74 warnings`

## Increment 2026-03-19 Codex-C17-C18-C19-Merge-Prep
- Expanded `scripts/verify_odoo18_plm_stack.sh` to include:
  - `box`
  - `document_sync`
  - `cutted_parts`
- Refreshed the expanded candidate stack full baseline:
  - `305 passed, 103 warnings`
- Created merge rehearsal branch from `main`:
  - `feature/codex-merge-rehearsal-c17c18c19`
- Merge rehearsal result:
  - `feature/codex-stack-c17c18c19` merged into `main` without manual conflict resolution
  - merge rehearsal commit:
    - `7db4fc6`
  - rehearsal-branch full baseline:
    - `305 passed, 103 warnings`

## Increment 2026-03-19 Codex-Main-Merge-C17-C18-C19
- Executed the actual merge:
  - source: `feature/codex-stack-c17c18c19`
  - target: `main`
  - merge commit: `f46ff5e`
- Post-merge validation on `main`:
  - expanded stack script:
    - `305 passed, 103 warnings`
  - broader merge-prep pack:
    - `112 passed, 283 deselected, 63 warnings`
- Operational note:
  - `pytest` emitted a cache write warning because `.pytest_cache` hit `No space left on device`
  - test execution still completed successfully
- Current policy:
  - do not open new Claude feature branches until post-merge stabilization is accepted

## Increment 2026-03-19 Codex-Post-Merge-Stabilization-Refresh
- Performed cache/worktree hygiene after the real `main` merge:
  - removed `__pycache__` and `.pytest_cache` from clean Codex worktrees
  - removed superseded rehearsal and integration worktrees
  - restored free space to roughly `4.3Gi`
- Re-ran merged-`main` validation after cleanup:
  - expanded stack script:
    - `305 passed, 103 warnings`
  - broader merge-prep pack:
    - `112 passed, 283 deselected, 62 warnings`
- Operational conclusion:
  - the prior `.pytest_cache` `No space left on device` warning did not recur
  - keep Claude frozen until the stabilization window is explicitly accepted

## Increment 2026-03-19 Next Claude Batch C20-C22
- Stabilization window on merged `main` has been accepted for new greenfield planning.
- Claude may reopen parallel work only in the following low-conflict greenfield extensions:
  - `C20`
  - `C21`
  - `C22`
- Claude greenfield branches should now base from:
  - `feature/claude-greenfield-base-2`
  - source branch for that freeze point: `main`
- Keep these tasks out of hot paths:
  - no edits to `src/yuantus/api/app.py`
  - no edits to `parallel_tasks`, `version`, `benchmark_branches`
  - no edits to currently integrated hot routers

### C20
- task: `PLM box analytics / export bootstrap`
- suggested branch: `feature/claude-c20-box-analytics`
- write scope:
  - `src/yuantus/meta_engine/box/`
  - `src/yuantus/meta_engine/web/box_router.py`
  - `src/yuantus/meta_engine/tests/test_box_*.py`
- non-goals:
  - no app registration
  - no CAD/storage/version integration

### C21
- task: `document sync analytics / export bootstrap`
- suggested branch: `feature/claude-c21-document-sync-analytics`
- write scope:
  - `src/yuantus/meta_engine/document_sync/`
  - `src/yuantus/meta_engine/web/document_sync_router.py`
  - `src/yuantus/meta_engine/tests/test_document_sync_*.py`
- non-goals:
  - no app registration
  - no background workers or storage hot-path integration

### C22
- task: `cutted-parts analytics / export bootstrap`
- suggested branch: `feature/claude-c22-cutted-parts-analytics`
- write scope:
  - `src/yuantus/meta_engine/cutted_parts/`
  - `src/yuantus/meta_engine/web/cutted_parts_router.py`
  - `src/yuantus/meta_engine/tests/test_cutted_parts_*.py`
- non-goals:
  - no app registration
  - no optimization solver or BOM/manufacturing hot-path integration

## Increment 2026-03-19 Codex-C20-C21-Stack-Verification
- built isolated candidate stack branch `feature/codex-stack-c20c21`
- cherry-picked:
  - `4102f55` `feat(c20): add box analytics and export endpoints`
  - `18ecb5b` `feat(c21): add document sync analytics and export endpoints`
- stack commits after integration:
  - `e85d046` `feat(c20): add box analytics and export endpoints`
  - `b45e7a4` `feat(c21): add document sync analytics and export endpoints`
- validated `C20` and `C21` together without touching `app.py` or existing hot paths
- extended greenfield cross-regression with `C19`:
  - `118 passed, 43 warnings in 31.73s`
- current follow-up:
  - promote the candidate stack to `feature/codex-stack-c20c21c22`

## Increment 2026-03-19 Codex-C22-Integration
- extended candidate stack branch:
  - `feature/codex-stack-c20c21c22`
- cherry-picked:
  - `64c9724` `feat(c22): add cutted-parts analytics and export endpoints`
- integrated stack commit:
  - `68e3dbb` `feat(c22): add cutted-parts analytics and export endpoints`
- combined greenfield regression after `C22`:
  - `133 passed, 49 warnings in 3.32s`
- unified stack full regression on candidate stack:
  - `351 passed, 123 warnings in 28.77s`
- result:
  - `C20/C21/C22` are now all in Codex-verified candidate-stack state

## Increment 2026-03-19 Main-FastForward-C20-C21-C22
- fast-forwarded `main` from `dd4b72a` to `aebdc09`
- source branch:
  - `feature/codex-stack-c20c21c22`
- post-merge unified stack regression on `main`:
  - `351 passed, 123 warnings in 30.86s`
- result:
  - `C20/C21/C22` are now part of `main`

## Increment 2026-03-19 Main-Stability-Refresh-C20-C21-C22
- reran merged-`main` unified stack regression:
  - `351 passed, 123 warnings in 42.37s`
- reran merged-`main` broader post-merge pack:
  - `351 passed, 123 warnings in 42.32s`
- result:
  - `C20/C21/C22` stabilization window accepted on `main`
  - no new functional regression detected

## Increment 2026-03-19 Next Claude Batch C23-C25
- `C20/C21/C22` has completed merge and stabilization on `main`
- next Claude greenfield work should stay within the same isolated domains, but move to third-stage read-side helpers:
  - `C23`
  - `C24`
  - `C25`
- Claude should branch from:
  - `feature/claude-greenfield-base-3`
  - source branch: `main`

### C23
- task: `PLM box ops-report / transitions bootstrap`
- suggested branch: `feature/claude-c23-box-ops-report`
- write scope:
  - `src/yuantus/meta_engine/box/`
  - `src/yuantus/meta_engine/web/box_router.py`
  - `src/yuantus/meta_engine/tests/test_box_*.py`
- non-goals:
  - no app registration
  - no cross-domain integration

### C24
- task: `document sync reconciliation bootstrap`
- suggested branch: `feature/claude-c24-document-sync-reconciliation`
- write scope:
  - `src/yuantus/meta_engine/document_sync/`
  - `src/yuantus/meta_engine/web/document_sync_router.py`
  - `src/yuantus/meta_engine/tests/test_document_sync_*.py`
- non-goals:
  - no app registration
  - no background workers or storage hot-path integration

### C25
- task: `cutted-parts cost / utilization bootstrap`
- suggested branch: `feature/claude-c25-cutted-parts-costing`
- write scope:
  - `src/yuantus/meta_engine/cutted_parts/`
  - `src/yuantus/meta_engine/web/cutted_parts_router.py`
  - `src/yuantus/meta_engine/tests/test_cutted_parts_*.py`
- non-goals:
  - no app registration
  - no optimization solver or BOM/manufacturing hot-path integration

## Increment 2026-03-19 Codex-C23-C24-Stack-Verification
- built isolated candidate stack branch `feature/codex-c23c24-staging`
- cherry-picked:
  - `48af7e3` `feat(c23): add box ops report and transition summary endpoints`
  - `00df973` `feat(c24): add document sync reconciliation and conflict resolution endpoints`
- stack commits after integration:
  - `585d5f3` `feat(c23): add box ops report and transition summary endpoints`
  - `7ab31dc` `feat(c24): add document sync reconciliation and conflict resolution endpoints`
- combined targeted regression:
  - `111 passed, 44 warnings in 3.99s`
- unified stack full regression on staging:
  - `379 passed, 134 warnings in 31.56s`
- current follow-up:
  - promote the staging branch to `feature/codex-c23c24c25-staging`

## Increment 2026-03-19 Codex-C25-Integration
- extended staging branch:
  - `feature/codex-c23c24c25-staging`
- cherry-picked:
  - `30b7d3b` `feat(cutted-parts): add cost and utilization analytics (C25)`
- integrated staging commit:
  - `b2fec86` `feat(cutted-parts): add cost and utilization analytics (C25)`
- note:
  - `GET /utilization/overview` was accepted as the correct route because `GET /overview` already exists from `C22`
- combined greenfield regression after `C25`:
  - `178 passed, 66 warnings in 3.62s`
- unified stack full regression after `C25`:
  - `396 passed, 140 warnings in 15.87s`
- result:
  - `C23/C24/C25` are now all in Codex-verified staging state

## Increment 2026-03-19 Main-FastForward-C23-C24-C25
- `main` advanced from:
  - `ee2292d`
  - to `88abb79`
- source staging branch:
  - `feature/codex-c23c24c25-staging`
- post-merge unified stack rerun on `main`:
  - `396 passed, 140 warnings in 11.78s`
- post-merge broader regression rerun on `main`:
  - `249 passed, 122 warnings in 9.26s`
- result:
  - `C23/C24/C25` are now part of `main`
  - no new post-merge functional regression was observed

## Increment 2026-03-19 Next Claude Batch C26-C28
- `C23/C24/C25` has completed merge and stabilization on `main`
- next Claude greenfield work should continue the same three isolated domains with a fourth-stage read-side batch:
  - `C26`
  - `C27`
  - `C28`
- Claude should branch from:
  - `feature/claude-greenfield-base-4`
  - source branch: `main`

### C26
- task: `PLM box reconciliation / audit bootstrap`
- suggested branch: `feature/claude-c26-box-reconciliation`
- write scope:
  - `src/yuantus/meta_engine/box/`
  - `src/yuantus/meta_engine/web/box_router.py`
  - `src/yuantus/meta_engine/tests/test_box_*.py`
- non-goals:
  - no app registration
  - no cross-domain storage or workflow integration

### C27
- task: `document sync replay / audit bootstrap`
- suggested branch: `feature/claude-c27-document-sync-replay`
- write scope:
  - `src/yuantus/meta_engine/document_sync/`
  - `src/yuantus/meta_engine/web/document_sync_router.py`
  - `src/yuantus/meta_engine/tests/test_document_sync_*.py`
- non-goals:
  - no app registration
  - no background workers or storage hot-path integration

### C28
- task: `cutted-parts templates / scenarios bootstrap`
- suggested branch: `feature/claude-c28-cutted-parts-scenarios`
- write scope:
  - `src/yuantus/meta_engine/cutted_parts/`
  - `src/yuantus/meta_engine/web/cutted_parts_router.py`
  - `src/yuantus/meta_engine/tests/test_cutted_parts_*.py`
- non-goals:
  - no app registration
  - no optimization solver or BOM/manufacturing hot-path integration

## Increment 2026-03-19 Codex-C26-C27-Stack-Verification
- built isolated candidate stack branch:
  - `feature/codex-c26c27-staging`
- cherry-picked:
  - `77b5d4d` `feat(box): add reconciliation/audit analytics (C26)`
  - `608d4cd` `feat(document-sync): add replay/audit analytics (C27)`
- staging commits after integration:
  - `37e81be` `feat(box): add reconciliation/audit analytics (C26)`
  - `f828406` `feat(document-sync): add replay/audit analytics (C27)`
- combined targeted regression:
  - `140 passed, 55 warnings in 2.35s`
- unified stack full regression on staging:
  - `425 passed, 151 warnings in 13.34s`
- result:
  - `C26/C27` are now in Codex-verified staging state
  - `C28` remains pending by design

## Increment 2026-03-19 Codex-C28-Integration
- promoted candidate stack branch:
  - `feature/codex-c26c27c28-staging`
- cherry-picked:
  - `13c8c90` `feat(cutted-parts): add C28 templates/scenarios bootstrap`
- staging commit after integration:
  - `fabc2b5` `feat(cutted-parts): add C28 templates/scenarios bootstrap`
- combined greenfield regression after `C28`:
  - `222 passed, 82 warnings in 3.75s`
- unified stack full regression after `C28`:
  - `440 passed, 156 warnings in 13.91s`
- result:
  - `C26/C27/C28` are now all in Codex-verified staging state

## Increment 2026-03-19 Codex-Merge-Rehearsal-C26-C27-C28
- candidate branch:
  - `feature/codex-c26c27c28-staging`
- rehearsal branch:
  - `feature/codex-merge-rehearsal-c26c27c28`
- rehearsal fast-forward:
  - `d068476` -> `019e874`
- rehearsal result:
  - no manual conflict resolution required
  - unified stack full on rehearsal branch:
    - `440 passed, 156 warnings in 13.61s`
- next step:
  - actual fast-forward into `main` if we accept this fourth-stage batch

## Increment 2026-03-19 Main-FastForward-C26-C27-C28
- `main` advanced from:
  - `d068476`
  - to `129e773`
- source staging branch:
  - `feature/codex-c26c27c28-staging`
- post-merge unified stack rerun on `main`:
  - `440 passed, 156 warnings in 13.96s`
- result:
  - `C26/C27/C28` are now part of `main`
  - no new post-merge functional regression was observed

## Increment 2026-03-19 Main-Stability-Refresh-C26-C27-C28
- targeted greenfield stability rerun on `main`:
  - `222 passed, 82 warnings in 2.12s`
- unified stack stability rerun on `main`:
  - `440 passed, 156 warnings in 12.63s`
- result:
  - `C26/C27/C28` stabilization window accepted on `main`

## Increment 2026-03-19 Next Claude Batch C29-C31
- `C26/C27/C28` has completed merge and stabilization on `main`
- next Claude greenfield work should continue the same three isolated domains with a fifth-stage read-side batch:
  - `C29`
  - `C30`
  - `C31`
- Claude should branch from:
  - `feature/claude-greenfield-base-5`
  - source branch: `main`

### C29
- task: `PLM box capacity / compliance bootstrap`
- suggested branch: `feature/claude-c29-box-capacity`
- write scope:
  - `src/yuantus/meta_engine/box/`
  - `src/yuantus/meta_engine/web/box_router.py`
  - `src/yuantus/meta_engine/tests/test_box_*.py`
- non-goals:
  - no app registration
  - no storage or workflow integration

### C30
- task: `document sync drift / snapshot bootstrap`
- suggested branch: `feature/claude-c30-document-sync-drift`
- write scope:
  - `src/yuantus/meta_engine/document_sync/`
  - `src/yuantus/meta_engine/web/document_sync_router.py`
  - `src/yuantus/meta_engine/tests/test_document_sync_*.py`
- non-goals:
  - no app registration
  - no background workers or storage hot-path integration

### C31
- task: `cutted-parts benchmark / quote bootstrap`
- suggested branch: `feature/claude-c31-cutted-parts-benchmark`
- write scope:
  - `src/yuantus/meta_engine/cutted_parts/`
  - `src/yuantus/meta_engine/web/cutted_parts_router.py`
  - `src/yuantus/meta_engine/tests/test_cutted_parts_*.py`
- non-goals:
  - no app registration
  - no optimization solver or BOM/manufacturing hot-path integration

## Increment 2026-03-19 Codex-C29-C30-Stack-Verification
- built isolated candidate stack branch:
  - `feature/codex-c29c30-staging`
- cherry-picked:
  - `ab909e4` `feat(box): add C29 capacity/compliance bootstrap`
  - `b0b27b0` `feat(document-sync): add C30 drift/snapshots bootstrap`
- staging commits after integration:
  - `31e59bb` `feat(box): add C29 capacity/compliance bootstrap`
  - `6fcf9be` `feat(document-sync): add C30 drift/snapshots bootstrap`
- combined targeted regression:
  - `169 passed, 66 warnings in 2.17s`
- unified stack full regression on staging:
  - `469 passed, 167 warnings in 12.95s`
- result:
  - `C29/C30` are now in Codex-verified staging state
  - `C31` remains pending by design

## Increment 2026-03-19 Codex-C31-Stack-Verification
- promoted isolated candidate stack branch:
  - `feature/codex-c29c30c31-staging`
- cherry-picked:
  - `c190634` `feat(cutted-parts): add C31 benchmark/quote bootstrap`
- staging commit after integration:
  - `4f2e54b` `feat(cutted-parts): add C31 benchmark/quote bootstrap`
- combined targeted regression with `C29/C30/C31`:
  - `267 passed, 98 warnings in 3.61s`
- unified stack full regression on staging:
  - `485 passed, 172 warnings in 14.77s`
- result:
  - `C29/C30/C31` are now in Codex-verified staging state

## Increment 2026-03-19 Codex-Merge-Rehearsal-C29-C30-C31
- candidate branch:
  - `feature/codex-c29c30c31-staging`
- rehearsal branch:
  - `feature/codex-merge-rehearsal-c29c30c31`
- rehearsal fast-forward:
  - `c620f94` -> `64bfae3`
- rehearsal result:
  - no manual conflict resolution required
  - unified stack full on rehearsal branch:
    - `485 passed, 172 warnings in 15.85s`
- next step:
  - actual fast-forward into `main` if we accept this fifth-stage batch

## Increment 2026-03-19 Main-FastForward-C29-C30-C31
- `main` advanced from:
  - `c620f94`
  - to `5feeb4a`
- source staging branch:
  - `feature/codex-c29c30c31-staging`
- post-merge targeted greenfield rerun on `main`:
  - `267 passed, 98 warnings in 2.74s`
- post-merge unified stack rerun on `main`:
  - `485 passed, 172 warnings in 12.59s`
- result:
  - `C29/C30/C31` are now part of `main`
  - no new post-merge functional regression was observed

## Increment 2026-03-19 Main-Stability-Refresh-C29-C30-C31
- targeted greenfield stability rerun on `main`:
  - `267 passed, 98 warnings in 2.67s`
- unified stack stability rerun on `main`:
  - `485 passed, 172 warnings in 14.52s`
- result:
  - `C29/C30/C31` stabilization window accepted on `main`

## Increment 2026-03-19 Next Claude Batch C32-C34
- `C29/C30/C31` has completed merge and stabilization on `main`
- next Claude greenfield work should continue the same three isolated domains with a sixth-stage read-side batch:
  - `C32`
  - `C33`
  - `C34`
- Claude should branch from:
  - `feature/claude-greenfield-base-6`
  - source branch: `main`

### C32
- task: `PLM box policy / exceptions bootstrap`
- suggested branch: `feature/claude-c32-box-policy`
- write scope:
  - `src/yuantus/meta_engine/box/`
  - `src/yuantus/meta_engine/web/box_router.py`
  - `src/yuantus/meta_engine/tests/test_box_*.py`
- non-goals:
  - no app registration
  - no storage or workflow integration

### C33
- task: `document sync baseline / lineage bootstrap`
- suggested branch: `feature/claude-c33-document-sync-lineage`
- write scope:
  - `src/yuantus/meta_engine/document_sync/`
  - `src/yuantus/meta_engine/web/document_sync_router.py`
  - `src/yuantus/meta_engine/tests/test_document_sync_*.py`
- non-goals:
  - no app registration
  - no background workers or storage hot-path integration

### C34
- task: `cutted-parts variance / recommendations bootstrap`
- suggested branch: `feature/claude-c34-cutted-parts-variance`
- write scope:
  - `src/yuantus/meta_engine/cutted_parts/`
  - `src/yuantus/meta_engine/web/cutted_parts_router.py`
  - `src/yuantus/meta_engine/tests/test_cutted_parts_*.py`
- non-goals:
  - no app registration
  - no BOM/manufacturing hot-path integration

## Increment 2026-03-20 Codex-C32-C33-Stack-Verification
- built isolated candidate stack branch:
  - `feature/codex-c32c33-staging`
- cherry-picked:
  - `3c6c869` `feat(box): add C32 policy/exceptions bootstrap`
  - `a157314` `feat(document-sync): add C33 baseline/lineage bootstrap`
- staging commits after integration:
  - `80c2e7e` `feat(box): add C32 policy/exceptions bootstrap`
  - `c0d3e06` `feat(document-sync): add C33 baseline/lineage bootstrap`
- combined targeted regression:
  - `198 passed, 77 warnings in 6.03s`
- unified stack full regression on staging:
  - `514 passed, 183 warnings in 11.98s`
- result:
  - `C32/C33` are now in Codex-verified staging state
  - `C34` remains pending by design

## Increment 2026-03-20 Codex-C34-Stack-Verification
- promoted isolated candidate stack branch:
  - `feature/codex-c32c33c34-staging`
- cherry-picked:
  - `45a94fc` `feat(cutted-parts): add C34 variance/recommendations bootstrap`
- staging commit after integration:
  - `7b50ea2` `feat(cutted-parts): add C34 variance/recommendations analytics`
- combined targeted regression with `C32/C33/C34`:
  - `314 passed, 114 warnings in 3.32s`
- unified stack full regression on staging:
  - `532 passed, 188 warnings in 12.93s`
- result:
  - `C32/C33/C34` are now in Codex-verified staging state

## Increment 2026-03-20 Codex-Merge-Rehearsal-C32-C33-C34
- candidate branch:
  - `feature/codex-c32c33c34-staging`
- rehearsal branch:
  - `feature/codex-merge-rehearsal-c32c33c34`
- rehearsal fast-forward:
  - `5babffa` -> `0f6e2ee`
- rehearsal result:
  - no manual conflict resolution required
  - unified stack full on rehearsal branch:
    - `532 passed, 188 warnings in 15.72s`
- next step:
  - actual fast-forward into `main` if we accept this sixth-stage batch

## Increment 2026-03-20 Main-FastForward-C32-C33-C34
- `main` advanced from:
  - `5babffa`
  - to `45dc112`
- source staging branch:
  - `feature/codex-c32c33c34-staging`
- post-merge targeted greenfield rerun on `main`:
  - `314 passed, 114 warnings in 3.61s`
- post-merge unified stack rerun on `main`:
  - `532 passed, 188 warnings in 13.07s`
- result:
  - `C32/C33/C34` are now part of `main`
  - no new post-merge functional regression was observed

## Increment 2026-03-20 Main-Stability-Refresh-C32-C33-C34
- targeted greenfield stability rerun on `main`:
  - `314 passed, 114 warnings in 2.99s`
- unified stack stability rerun on `main`:
  - `532 passed, 188 warnings in 13.07s`
- result:
  - `C32/C33/C34` stabilization window accepted on `main`

## Increment 2026-03-20 Next Claude Batch C35-C37
- `C32/C33/C34` has completed merge and stabilization on `main`
- next Claude greenfield work should continue the same three isolated domains with a seventh-stage read-side batch:
  - `C35`
  - `C36`
  - `C37`
- Claude should branch from:
  - `feature/claude-greenfield-base-7`
  - source branch: `main`

### C35
- task: `PLM box reservations / traceability bootstrap`
- suggested branch: `feature/claude-c35-box-traceability`
- write scope:
  - `src/yuantus/meta_engine/box/`
  - `src/yuantus/meta_engine/web/box_router.py`
  - `src/yuantus/meta_engine/tests/test_box_*.py`
- non-goals:
  - no app registration
  - no storage, CAD, or workflow hot-path integration

### C36
- task: `document sync checkpoints / retention bootstrap`
- suggested branch: `feature/claude-c36-document-sync-checkpoints`
- write scope:
  - `src/yuantus/meta_engine/document_sync/`
  - `src/yuantus/meta_engine/web/document_sync_router.py`
  - `src/yuantus/meta_engine/tests/test_document_sync_*.py`
- non-goals:
  - no app registration
  - no background workers or storage hot-path integration

### C37
- task: `cutted-parts thresholds / envelopes bootstrap`
- suggested branch: `feature/claude-c37-cutted-parts-thresholds`
- write scope:
  - `src/yuantus/meta_engine/cutted_parts/`
  - `src/yuantus/meta_engine/web/cutted_parts_router.py`
  - `src/yuantus/meta_engine/tests/test_cutted_parts_*.py`
- non-goals:
  - no app registration
  - no optimization solver or BOM/manufacturing hot-path integration

## Increment 2026-03-20 Codex-C35-C36-Stack-Verification
- built isolated candidate stack branch:
  - `feature/codex-c35c36-staging`
- cherry-picked:
  - `d346de8` `feat(box): add C35 reservations/traceability analytics`
  - `bd3e14a` `feat(document-sync): add C36 checkpoints/retention analytics`
- staging commits after integration:
  - `bff4ec6` `feat(box): add C35 reservations/traceability analytics`
  - `576b975` `feat(document-sync): add C36 checkpoints/retention analytics`
- combined targeted regression:
  - `227 passed, 88 warnings in 2.89s`
- unified stack full regression on staging:
  - `561 passed, 199 warnings in 12.57s`
- result:
  - `C35/C36` are now in Codex-verified staging state
  - `C37` remains pending by design

## Increment 2026-03-20 Codex-C37-Stack-Verification
- promoted isolated candidate stack branch:
  - `feature/codex-c35c36c37-staging`
- cherry-picked:
  - `3fa66fa` `feat(cutted-parts): add C37 thresholds / envelopes bootstrap`
- staging commit after integration:
  - `f15ad29` `feat(cutted-parts): add C37 thresholds / envelopes bootstrap`
- combined targeted regression with `C35/C36/C37`:
  - `364 passed, 130 warnings in 8.36s`
- unified stack full regression on staging:
  - `582 passed, 204 warnings in 13.39s`
- result:
  - `C35/C36/C37` are now in Codex-verified staging state

## Increment 2026-03-20 Codex-Merge-Rehearsal-C35-C36-C37
- candidate branch:
  - `feature/codex-c35c36c37-staging`
- rehearsal branch:
  - `feature/codex-merge-rehearsal-c35c36c37`
- rehearsal fast-forward:
  - `d9fa6e7` -> `97b1492`
- rehearsal result:
  - no manual conflict resolution required
  - unified stack full on rehearsal branch:
    - `582 passed, 204 warnings in 19.00s`
- next step:
  - actual fast-forward into `main` if we accept this seventh-stage batch

## Increment 2026-03-20 Main-FastForward-C35-C36-C37
- `main` advanced from:
  - `d9fa6e7`
  - to `d9abd0c`
- source staging branch:
  - `feature/codex-c35c36c37-staging`
- post-merge targeted greenfield rerun on `main`:
  - `364 passed, 130 warnings in 3.71s`
- post-merge unified stack rerun on `main`:
  - `582 passed, 204 warnings in 13.67s`
- result:
  - `C35/C36/C37` are now part of `main`
  - no new post-merge functional regression was observed

## Increment 2026-03-20 Main-Stability-Refresh-C35-C36-C37
- targeted greenfield stability rerun on `main`:
  - `364 passed, 130 warnings in 3.09s`
- unified stack stability rerun on `main`:
  - `582 passed, 204 warnings in 13.92s`
- result:
  - `C35/C36/C37` stabilization window accepted on `main`

## Increment 2026-03-20 Next Claude Batch C38-C40
- `C35/C36/C37` has completed merge and stabilization on `main`
- next Claude greenfield work should continue the same three isolated domains with an eighth-stage read-side batch:
  - `C38`
  - `C39`
  - `C40`
- Claude should branch from:
  - `feature/claude-greenfield-base-8`
  - source branch: `main`

### C38
- task: `PLM box allocation / custody bootstrap`
- suggested branch: `feature/claude-c38-box-custody`
- write scope:
  - `src/yuantus/meta_engine/box/`
  - `src/yuantus/meta_engine/web/box_router.py`
  - `src/yuantus/meta_engine/tests/test_box_*.py`
- non-goals:
  - no app registration
  - no storage, CAD, or workflow hot-path integration

### C39
- task: `document sync freshness / watermarks bootstrap`
- suggested branch: `feature/claude-c39-document-sync-freshness`
- write scope:
  - `src/yuantus/meta_engine/document_sync/`
  - `src/yuantus/meta_engine/web/document_sync_router.py`
  - `src/yuantus/meta_engine/tests/test_document_sync_*.py`
- non-goals:
  - no app registration
  - no background workers or storage hot-path integration

### C40
- task: `cutted-parts alerts / outliers bootstrap`
- suggested branch: `feature/claude-c40-cutted-parts-alerts`
- write scope:
  - `src/yuantus/meta_engine/cutted_parts/`
  - `src/yuantus/meta_engine/web/cutted_parts_router.py`
  - `src/yuantus/meta_engine/tests/test_cutted_parts_*.py`
- non-goals:
  - no app registration
  - no optimization solver or BOM/manufacturing hot-path integration

## Increment 2026-03-20 Codex-C38-C39-Stack-Verification
- built isolated candidate stack branch:
  - `feature/codex-c38c39-staging`
- cherry-picked:
  - `8a1b5f7` `feat(box): add C38 allocation / custody bootstrap`
  - `872a17b` `feat(document-sync): add C39 freshness / watermarks bootstrap`
- staging commits after integration:
  - `1cb1ec1` `feat(box): add C38 allocation / custody bootstrap`
  - `a1658c2` `feat(document-sync): add C39 freshness / watermarks bootstrap`
- combined targeted regression:
  - `259 passed, 99 warnings in 3.50s`
- unified stack full regression on staging:
  - `614 passed, 215 warnings in 13.79s`
- result:
  - `C38/C39` are now in Codex-verified staging state
  - `C40` remains pending by design

## Increment 2026-03-20 Codex-C40-Stack-Verification
- promoted isolated candidate stack branch:
  - `feature/codex-c38c39c40-staging`
- cherry-picked:
  - `3a543bf` `feat(cutted-parts): add C40 alerts / outliers bootstrap`
- staging commit after integration:
  - `d789b72` `feat(cutted-parts): add C40 alerts / outliers bootstrap`
- combined targeted regression with `C38/C39/C40`:
  - `417 passed, 146 warnings in 7.52s`
- unified stack full regression on staging:
  - `635 passed, 220 warnings in 14.02s`
- result:
  - `C38/C39/C40` are now in Codex-verified staging state

## Increment 2026-03-20 Codex-Merge-Rehearsal-C38-C39-C40
- candidate branch:
  - `feature/codex-c38c39c40-staging`
- rehearsal branch:
  - `feature/codex-merge-rehearsal-c38c39c40`
- rehearsal fast-forward:
  - `5ef27df` -> `7205a1b`
- rehearsal result:
  - no manual conflict resolution required
  - unified stack full on rehearsal branch:
    - `635 passed, 220 warnings in 16.36s`
- next step:
  - actual fast-forward into `main` if we accept this eighth-stage batch

## Increment 2026-03-20 Main-FastForward-C38-C39-C40
- source branch:
  - `feature/codex-c38c39c40-staging`
- main fast-forward:
  - `5ef27df` -> `d70d102`
- post-merge targeted regression:
  - `417 passed, 146 warnings in 3.54s`
- post-merge unified stack full:
  - `635 passed, 220 warnings in 14.89s`
- result:
  - `C38/C39/C40` are now part of `main`
  - no new regression was introduced by the fast-forward

## Increment 2026-03-20 Main-Stability-Refresh-C38-C39-C40
- targeted greenfield stability rerun on `main`:
  - `417 passed, 146 warnings in 5.57s`
- unified stack stability rerun on `main`:
  - `635 passed, 220 warnings in 13.73s`
- result:
  - `C38/C39/C40` stabilization window accepted on `main`

## Increment 2026-03-20 Next Claude Batch C41-C43
- `C38/C39/C40` has completed merge and stabilization on `main`
- next Claude greenfield work should continue the same three isolated domains with a ninth-stage read-side batch:
  - `C41`
  - `C42`
  - `C43`
- Claude should branch from:
  - `feature/claude-greenfield-base-9`
  - source branch: `main`

### C41
- task: `PLM box occupancy / turnover bootstrap`
- suggested branch: `feature/claude-c41-box-turnover`
- write scope:
  - `src/yuantus/meta_engine/box/`
  - `src/yuantus/meta_engine/web/box_router.py`
  - `src/yuantus/meta_engine/tests/test_box_*.py`
- non-goals:
  - no app registration
  - no storage, CAD, or workflow hot-path integration

### C42
- task: `document sync lag / backlog bootstrap`
- suggested branch: `feature/claude-c42-document-sync-lag`
- write scope:
  - `src/yuantus/meta_engine/document_sync/`
  - `src/yuantus/meta_engine/web/document_sync_router.py`
  - `src/yuantus/meta_engine/tests/test_document_sync_*.py`
- non-goals:
  - no app registration
  - no background workers or storage hot-path integration

### C43
- task: `cutted-parts throughput / cadence bootstrap`
- suggested branch: `feature/claude-c43-cutted-parts-throughput`
- write scope:
  - `src/yuantus/meta_engine/cutted_parts/`
  - `src/yuantus/meta_engine/web/cutted_parts_router.py`
  - `src/yuantus/meta_engine/tests/test_cutted_parts_*.py`
- non-goals:
  - no app registration
  - no optimization solver or BOM/manufacturing hot-path integration

## Increment 2026-03-20 Codex-C41-C42-Stack-Verification
- built isolated candidate stack branch:
  - `feature/codex-c41c42-staging`
- cherry-picked:
  - `f1fcb43` `feat(box): add C41 occupancy / turnover bootstrap`
  - `fd9c58c` `feat(document-sync): add C42 lag / backlog bootstrap`
- staging commits after integration:
  - `f8c9753` `feat(box): add C41 occupancy / turnover bootstrap`
  - `31b98ab` `feat(document-sync): add C42 lag / backlog bootstrap`
- combined targeted regression:
  - `291 passed, 110 warnings in 3.37s`
- unified stack full regression on staging:
  - `667 passed, 231 warnings in 13.47s`
- result:
  - `C41/C42` are now in Codex-verified staging state
  - `C43` remains pending by design

## Increment 2026-03-20 Codex-C43-Stack-Verification
- promoted isolated candidate stack branch:
  - `feature/codex-c41c42c43-staging`
- cherry-picked:
  - `022a34f` `feat(cutted-parts): add C43 throughput / cadence bootstrap`
- staging commit after integration:
  - `3f6d4ae` `feat(cutted-parts): add C43 throughput / cadence bootstrap`
- combined targeted regression with `C41/C42/C43`:
  - `468 passed, 162 warnings in 4.49s`
- unified stack full regression on staging:
  - `686 passed, 236 warnings in 14.27s`
- result:
  - `C41/C42/C43` are now in Codex-verified staging state

## Increment 2026-03-20 Codex-Merge-Rehearsal-C41-C42-C43
- candidate branch:
  - `feature/codex-c41c42c43-staging`
- rehearsal branch:
  - `feature/codex-merge-rehearsal-c41c42c43`
- rehearsal fast-forward:
  - `88820f2` -> `2245073`
- rehearsal result:
  - no manual conflict resolution required
  - unified stack full on rehearsal branch:
    - `686 passed, 236 warnings in 15.71s`
- next step:
  - actual fast-forward into `main` if we accept this ninth-stage batch

## Increment 2026-03-20 Main-FastForward-C41-C42-C43
- source branch:
  - `feature/codex-c41c42c43-staging`
- main fast-forward:
  - `88820f2` -> `2db3c5c`
- post-merge targeted regression:
  - `468 passed, 162 warnings in 3.25s`
- post-merge unified stack full:
  - `686 passed, 236 warnings in 13.69s`
- result:
  - `C41/C42/C43` are now part of `main`
  - no new regression was introduced by the fast-forward

## Increment 2026-03-20 Main-Stability-Refresh-C41-C42-C43
- targeted greenfield stability rerun on `main`:
  - `468 passed, 162 warnings in 3.71s`
- unified stack stability rerun on `main`:
  - `686 passed, 236 warnings in 13.23s`
- result:
  - `C41/C42/C43` stabilization window accepted on `main`

## Increment 2026-03-20 Next Claude Batch C44-C46
- `C41/C42/C43` has completed merge and stabilization on `main`
- next Claude greenfield work should continue the same three isolated domains with a tenth-stage read-side batch:
  - `C44`
  - `C45`
  - `C46`
- Claude should branch from:
  - `feature/claude-greenfield-base-10`
  - source branch: `main`

### C44
- task: `PLM box dwell / aging bootstrap`
- suggested branch: `feature/claude-c44-box-aging`
- write scope:
  - `src/yuantus/meta_engine/box/`
  - `src/yuantus/meta_engine/web/box_router.py`
  - `src/yuantus/meta_engine/tests/test_box_*.py`
- non-goals:
  - no app registration
  - no storage, CAD, or workflow hot-path integration

### C45
- task: `document sync skew / gaps bootstrap`
- suggested branch: `feature/claude-c45-document-sync-gaps`
- write scope:
  - `src/yuantus/meta_engine/document_sync/`
  - `src/yuantus/meta_engine/web/document_sync_router.py`
  - `src/yuantus/meta_engine/tests/test_document_sync_*.py`
- non-goals:
  - no app registration
  - no background workers or storage hot-path integration

### C46
- task: `cutted-parts saturation / bottlenecks bootstrap`
- suggested branch: `feature/claude-c46-cutted-parts-bottlenecks`
- write scope:
  - `src/yuantus/meta_engine/cutted_parts/`
  - `src/yuantus/meta_engine/web/cutted_parts_router.py`
  - `src/yuantus/meta_engine/tests/test_cutted_parts_*.py`
- non-goals:
  - no app registration
  - no optimization solver or BOM/manufacturing hot-path integration

## Increment 2026-03-20 Codex-C44-C45-Stack-Verification
- built isolated candidate stack branch:
  - `feature/codex-c44c45-staging`
- cherry-picked:
  - `81e5300` `feat(box): add C44 dwell / aging bootstrap`
  - `0276af8` `feat(document-sync): add C45 skew / gaps bootstrap`
- staging commits after integration:
  - `52f84c5` `feat(box): add C44 dwell / aging bootstrap`
  - `b7dc629` `feat(document-sync): add C45 skew / gaps bootstrap`
- combined targeted regression:
  - `324 passed, 121 warnings in 4.84s`
- unified stack full regression on staging:
  - `719 passed, 247 warnings in 13.95s`
- result:
  - `C44/C45` are now in Codex-verified staging state
  - `C46` remains pending by design

## Increment 2026-03-21 Codex-C44-C45-C46-Merge-Prep
- built full tenth-stage candidate stack branch:
  - `feature/codex-c44c45c46-staging`
- integrated and closure commits:
  - `52f84c5` `feat(box): add C44 dwell / aging bootstrap`
  - `b7dc629` `feat(document-sync): add C45 skew / gaps bootstrap`
  - `2df0bf7` `feat(cutted_parts): add C46 saturation bottlenecks`
  - `d2363d7` `docs(cutted_parts): record C46 staging verification`
  - `7da729f` `docs(benchmark): add target matrix`
  - `8c114bb` `docs(benchmark): add capability checklists`
  - `ad99773` `docs(benchmark): add child checklist template`
- combined targeted regression on staging:
  - `516 passed in 8.81s`
- unified stack full regression on staging:
  - `734 passed, 252 warnings in 15.52s`
- isolated merge rehearsal:
  - branch: `feature/codex-merge-rehearsal-c44c45c46`
  - fast-forward: `df29d5f` -> `ad99773`
  - unified stack full regression on rehearsal branch:
    - `734 passed, 252 warnings in 12.95s`
- result:
  - `C44/C45/C46` are now merge-prep verified
  - final `main` fast-forward and stabilization rerun remain intentionally pending

## Increment 2026-03-21 Main-Stability-Refresh-C44-C45-C46
- fast-forwarded `main`:
  - `df29d5f` -> `03341b1`
- post-merge targeted regression on `main`:
  - `516 passed in 6.45s`
- post-merge unified stack full regression on `main`:
  - `734 passed, 252 warnings in 14.99s`
- stabilization targeted regression on `main`:
  - `516 passed in 5.07s`
- stabilization unified stack full regression on `main`:
  - `734 passed, 252 warnings in 12.49s`
- result:
  - `C44/C45/C46` stabilization window accepted on `main`
