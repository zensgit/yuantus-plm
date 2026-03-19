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
- `C7` BOM compare hardening：reported complete by Claude on `feature/claude-c7-bom-compare`, pending integration
- `C8` quality-mrp integration：reported complete by Claude on `feature/claude-c8-quality-mrp`, pending integration
- `C9` maintenance-workcenter readiness：reported complete by Claude on `feature/claude-c9-maintenance-readiness`, pending integration
- `C10` locale description resolver：completed on this branch after Codex integration verification

## Priority Matrix
| Task ID | Priority | Target | Subsystem | Status |
| --- | --- | --- | --- | --- |
| C6 | P2 | locale/report bootstrap | `locale` + `report_locale` + `locale_router` | completed |
| P2-A | P2 | locale/report helpers | `parallel_tasks` workorder export + parallel-ops export locale integration | completed |
| C7 | P1 | BOM compare & summary hardening | `bom_service` + `bom_router` | branch_complete_reported |
| C8 | P1 | quality-mrp integration | `quality` + manufacturing integration edge | branch_complete_reported |
| C9 | P1 | maintenance-workcenter readiness | `maintenance` + workcenter integration edge | branch_complete_reported |
| C10 | P2 | locale description resolver | `locale` description/read-model helpers | completed |

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

## Claude Allocation
- `C7/C8` are now reported complete on Claude branches and should be integrated only after Codex-side verification.
- Next safe Claude tasks:
  - none on locale path until `C7/C8/C9` integration order is scheduled
- `C10` has been integrated and verified on the current Codex branch.
