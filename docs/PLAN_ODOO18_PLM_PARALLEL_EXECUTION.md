# Yuantus Odoo18 PLM Parallel Execution Plan

## Goal Snapshot
- 目标一：在当前真实代码基线上持续收口 Odoo18 PLM 对标能力
- 目标二：把 Claude 已完成分支按模块边界安全并入，不和进行中的 `C7` 冲突
- 当前工作分支：`feature/codex-p2a-locale-export`

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
- `C7` BOM compare hardening：Codex-integrated on `feature/codex-c7-bom-compare-integration` (`5c31dd3`, `db781f4`)
- `C8` quality-mrp integration：Codex-integrated on `feature/codex-c8-quality-integration` (`3b971f3`, `7ee9f1e`)
- `C9` maintenance-workcenter readiness：Codex-integrated on `feature/codex-c9-maintenance-integration` (`d395fb8`, `7340027`)
- `C10` locale description resolver：completed on this branch after Codex integration verification
- `C11` file/3D consumer hardening：ready_for_claude
- `C12` generic approvals bootstrap：ready_for_claude
- `C13` subcontracting bootstrap：ready_for_claude

## Priority Matrix
| Task ID | Priority | Target | Subsystem | Status |
| --- | --- | --- | --- | --- |
| C6 | P2 | locale/report bootstrap | `locale` + `report_locale` + `locale_router` | completed |
| P2-A | P2 | locale/report helpers | `parallel_tasks` workorder export + parallel-ops export locale integration | completed |
| C7 | P1 | BOM compare & summary hardening | `bom_router` + summarized snapshot regression pack | completed_on_codex_integration_branch |
| C8 | P1 | quality-mrp integration | `quality` + manufacturing integration edge | completed_on_codex_integration_branch |
| C9 | P1 | maintenance-workcenter readiness | `maintenance` + workcenter integration edge | completed_on_codex_integration_branch |
| C10 | P2 | locale description resolver | `locale` description/read-model helpers | completed |
| C11 | P1 | file/3D consumer hardening | `file_router` + file viewer tests | ready_for_claude |
| C12 | P2 | generic approvals bootstrap | new `approvals` module + router + tests | ready_for_claude |
| C13 | P2 | subcontracting bootstrap | new `subcontracting` module + router + tests | ready_for_claude |

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

## Next Claude Allocation Draft
- `C11` file/3D consumer hardening: scoped and ready
- `C12` generic approvals bootstrap: scoped and ready
- `C13` subcontracting bootstrap: scoped and ready

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
