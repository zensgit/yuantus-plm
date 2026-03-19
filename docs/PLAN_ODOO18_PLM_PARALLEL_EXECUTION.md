# Yuantus Odoo18 PLM Parallel Execution Plan

## Goal Snapshot
- 目标一：在当前真实代码基线上持续收口 Odoo18 PLM 对标能力
- 目标二：把 Claude 已完成分支按模块边界安全并入统一集成栈
- 当前工作分支：`feature/codex-stack-c11c12`

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
- `C7` BOM compare hardening：merged and verified on this branch (`58f8db7`, `0a0a2eb`)
- `C8` quality-mrp integration：merged and verified on this branch (`f918784`, `12f5b9b`, `a7139ff`)
- `C9` maintenance-workcenter readiness：merged and verified on this branch (`736e612`, `b32ed6e`)
- `C10` locale description resolver：completed on this branch after Codex integration verification
- `C11` file/3D consumer hardening：completed on this branch
- `C12` generic approvals bootstrap：completed on this branch
- `C13` subcontracting bootstrap：completed on this branch

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
- `C11/C12/C13` 已进入 Codex 集成完成态
- 下一批 Claude 任务需要重新开新边界，不再回写这三条线

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
