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
- next Claude greenfield batch `C20/C21/C22`：all codex-stack verified on candidate branch

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
| C20 | P2 | PLM box analytics / export | `box` analytics/read-model/export helpers | codex_stack_verified |
| C21 | P2 | document sync analytics / export | `document_sync` analytics/conflict/export helpers | codex_stack_verified |
| C22 | P2 | cutted-parts analytics / export | `cutted_parts` analytics/waste/export helpers | codex_stack_verified |

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
- result:
  - `C20/C21/C22` are now all in Codex-verified candidate-stack state
