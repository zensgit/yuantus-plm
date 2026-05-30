# DEV & Verification: OdooPLM Gap G3 BOM Auto-Layout Taskbook

Date: 2026-05-30

Records the doc-only scope-lock for the G3 BOM-derived auto-layout follow-up.

## 1. What changed

- Added `DEVELOPMENT_ODOOPLM_G3_BOM_AUTO_LAYOUT_TASKBOOK_20260530.md`.
- Added this DEV/verification record.
- Added sorted `DELIVERY_DOC_INDEX.md` entries.

No source code, route, migration, model, or runtime behavior changed.

## 2. Grounding checked

- Existing G3 thin explode implementation:
  - `DEV_AND_VERIFICATION_ODOOPLM_G3_3D_EXPLODE_IMPL_20260530.md`
  - `parallel_tasks_cad_3d_router.py` `PUT/GET /cad-3d/explode/{document_item_id}`
  - `ThreeDOverlayService.upsert_explode` / `get_explode`
- Existing overlay binding:
  - `ThreeDOverlayService.resolve_component(s)` matches opaque
    `component_ref` strings against overlay `part_refs[]`.
- Existing BOM source:
  - `BOMService.get_bom_structure` returns nested children with relationship and
    child item payloads.
- Original G3 taskbook already warned that BOM auto-layout is valid only if the
  `component_ref` binding is made explicit.
- Reviewer resolution folded into the taskbook before implementation: duplicate
  item-id fallback is **skip + per-component warning**, not shallowest/first-node
  guessing.

## 3. Verification plan

Expected checks for this doc-only slice:

- doc-index / `DELIVERY_DOC_INDEX.md` sorting and references contracts;
- `verify_lisp_shell_static.py`;
- `verify_bridge_static.py`;
- `verify_material_sync_static.py`;
- `git diff --check`.

No DB-backed regression or route-count pin change is required because this PR is
documentation-only.

## 4. Status

Doc-only taskbook drafted. Implementation remains unauthorized and must be a
separate opt-in.
