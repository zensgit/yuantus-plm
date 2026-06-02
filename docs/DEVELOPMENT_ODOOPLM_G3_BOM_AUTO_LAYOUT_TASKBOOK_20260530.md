# OdooPLM Gap G3 — BOM-Derived Auto-Layout Taskbook

Date: 2026-05-30

Status: **doc-only scope-lock**. This taskbook does not authorize
implementation.

Baseline: `main = b4448fb8` after the OdooPLM gap ledger refresh (#683). The
thin G3 explode-config surface is already implemented (#682): a validated config
stored at `meta_3d_overlays.properties["explode"]`, keyed by opaque
`component_ref`, with no migration and no server-side geometry.

## 1. Goal

Add a follow-up implementation slice that can generate a **default explode
offset config from the BOM tree** when the existing 3D overlay already provides a
safe binding between BOM nodes and viewer component refs.

This is a convenience/defaulting slice, not a geometry engine. The server may use
BOM depth and order to create deterministic offsets, but it must not claim those
offsets are spatially correct for the mesh.

## 2. Grounded facts

- Existing G3 config:
  - `PUT /api/v1/cad-3d/explode/{document_item_id}` stores
    `{factor, mode, offsets[]}`.
  - `GET /api/v1/cad-3d/explode/{document_item_id}` returns the stored config or
    null.
  - `ThreeDOverlayService.upsert_explode` stores under
    `properties["explode"]`; no dedicated table/column.
- Existing overlay binding:
  - `ThreeDOverlayService.resolve_component(s)` treats `component_ref` as an
    opaque, client-defined string.
  - Overlay `part_refs[]` is the only current place where the server can see a
    possible link between a viewer component (`component_ref`) and a PLM item
    (`item_id` or other free-form row keys).
- Existing BOM source:
  - `BOMService.get_bom_structure(item_id, levels, relationship_types=...)`
    returns a tree shaped as `node["children"][] = {"relationship": rel_dict,
    "child": child_tree}`.
  - Relationship rows carry ids and properties; child nodes carry item ids.
- Therefore: BOM auto-layout is valid only as a **mapping-assisted default**.
  It is invalid to assume `component_ref == BOM item id`.

## 3. Recommended R1 shape

Add one admin/authenticated CAD-3D route:

`POST /api/v1/cad-3d/explode/{document_item_id}/auto-layout`

Request:

```json
{
  "root_item_id": "part-root-id",
  "levels": 10,
  "factor": 1.0,
  "depth_spacing": 1.0,
  "sibling_spacing": 0.25,
  "axis": "x",
  "persist": true
}
```

Response:

```json
{
  "document_item_id": "doc-id",
  "root_item_id": "part-root-id",
  "explode": {
    "factor": 1.0,
    "mode": "bom-depth",
    "offsets": [
      {"component_ref": "viewer-node-1", "offset": [1.0, 0.0, 0.0]}
    ]
  },
  "binding": {
    "matched": 1,
    "skipped": 0,
    "warnings": [
      {
        "component_ref": "viewer-node-2",
        "code": "ambiguous_item_id_fallback",
        "message": "item_id matched multiple BOM nodes; skipped"
      }
    ]
  },
  "persisted": true
}
```

If `persist=false`, return the computed config without writing
`properties["explode"]`.

## 4. Binding policy (LOCK)

The implementation must not assume `component_ref == item_id`.

Build a flattened BOM node list from `BOMService.get_bom_structure`, then bind
overlay `part_refs[]` to BOM nodes in this order:

1. If an overlay row has `relationship_id` or `bom_relationship_id`, match it to
   the BOM relationship id.
2. Otherwise, if an overlay row has `item_id`, match it to the BOM child item id.
3. Otherwise skip the overlay row.

For item-id fallback:

- If an item id occurs once in the BOM tree, use that node depth/order.
- If an item id occurs multiple times, **skip that overlay row** and emit a
  per-component warning code `ambiguous_item_id_fallback`.
- If no BOM node matches, skip the row and emit `unmapped_component_ref`.

Rationale: relationship-id binding is the real disambiguator. R1 must not guess
the shallowest/first BOM occurrence for duplicate item ids, because a plausible
but wrong default offset is worse than no offset.

Root handling: do not emit an offset for the root item unless a later taskbook
adds an explicit `include_root` option. R1 offsets are for child components.

## 5. Layout algorithm

R1 uses a deterministic, geometry-free algorithm:

- `mode = "bom-depth"`.
- `axis` may be `"x"`, `"y"`, or `"z"`; default `"x"`.
- For each matched component, offset along `axis` by
  `depth * depth_spacing * factor`.
- Apply a small orthogonal sibling spread using sibling order and
  `sibling_spacing * factor`.
- Clamp/validate all numeric inputs; reject non-finite values.

The exact orthogonal axis may be simple and deterministic. It is not a visual
quality guarantee; client viewers may later replace it with mesh-aware layout.

## 6. Persistence and compatibility

- Reuse existing `ThreeDOverlayService.upsert_explode`.
- Store only the existing explode config shape under `properties["explode"]`:
  `{factor, mode, offsets}`.
- Do not add a table, column, migration, or named preset model.
- Do not change `PUT/GET /cad-3d/explode/{document_item_id}` semantics.
- If the overlay is absent, return 404/400 instead of creating an empty overlay;
  auto-layout needs `part_refs[]` to be meaningful.
- Inherit the overlay visibility gate on reads used during auto-layout.

## 7. Route and contract impact

Expected implementation impact:

- `parallel_tasks_cad_3d_router.py`: +1 route.
- `parallel_tasks_service.py`: add a small helper around
  `BOMService.get_bom_structure` and the overlay `part_refs` binding.
- Route count: **690 -> 691**. Full-tree residual scan is mandatory before
  editing pins.
- Extend the existing cad-3d router contract test; do not add a new test file
  unless implementation genuinely needs one. If a new test file is added, update
  the CI allowlist/portfolio surfaces in the same PR.

## 8. Required tests / guards for implementation

Behavior tests:

- no overlay / no `part_refs` -> no silent success;
- relationship-id binding wins over item-id binding;
- item-id fallback works for a unique item;
- duplicate item-id fallback skips the component and emits a per-component
  `ambiguous_item_id_fallback` warning;
- unmapped overlay row is skipped and reported;
- `persist=false` does not call/write `upsert_explode`;
- `persist=true` writes via `upsert_explode`;
- role-gated overlay is denied consistently with existing explode GET;
- invalid numeric inputs and invalid axis are rejected;
- route count pins move exactly 690 -> 691.

Static/source guards:

- no server-side geometry imports or mesh/bbox/transform computation;
- no string pattern that equates `component_ref` directly to item id as a
  fallback-free assumption;
- no migration/model/table added;
- no GPL/AGPL or OdooPLM code reuse.

## 9. Non-goals

- Mesh-aware explosion, bounding boxes, transforms, collision avoidance, camera
  controls, or renderer work.
- Multiple named explode presets.
- Client-side viewer implementation.
- BOM mutation or EBOM/MBOM conversion.
- Productized UI controls.
- Any claim of OdooPLM client parity beyond generating a default config.

## 10. Reviewer focus

1. Is the binding policy strict enough to avoid the old
   `component_ref == BOM item id` assumption?
2. Is `skip + per-component warning` for duplicate item-id fallback the right R1
   lock, or should ambiguous rows fail the whole request?
3. Is one route (`/auto-layout`) acceptable, or should the computation be
   service-only until a UI/client is ready?
4. Are route-count and CI fan-out surfaces complete for the eventual code slice?

Ratifying this taskbook authorizes only the **shape** of a later R1
implementation. The code slice still needs separate opt-in.
