# Development Report - Relationship Item Phase 4 (Docs Cleanup)

Date: 2026-01-28

## Goal
Clarify post-migration usage rules and prevent legacy relationship writes by updating
operational documentation and reuse guidance.

## Changes Delivered
- Updated `docs/VERIFICATION.md` to use platform admin context for relationship write monitor
  (seed platform admin, login, and use `x-tenant-id: platform`).
- Added a “关系模型现状” section to `docs/REUSE.md` to state:
  - relationship facts live in `meta_items` (ItemType relationships)
  - `meta_relationships`/`RelationshipType` are deprecated and read-only
- Added “迁移后使用规范（Phase 4 说明）” to `docs/RELATIONSHIP_ITEM_PHASE3_USAGE_DESIGN_20260124_1502.md`.
- Added explicit legacy warnings in admin legacy-usage response and log when legacy rows exist.
- Marked `meta_relationships` table as deprecated (table comment).

## Files Touched
- `docs/VERIFICATION.md`
- `docs/REUSE.md`
- `docs/RELATIONSHIP_ITEM_PHASE3_USAGE_DESIGN_20260124_1502.md`
- `docs/DEVELOPMENT_REPORT_RELATIONSHIP_ITEM_PHASE4_20260128.md`
- `src/yuantus/api/routers/admin.py`
- `src/yuantus/meta_engine/relationship/models.py`
