# DEV & Verification: OdooPLM Gap G3 — BOM Auto-Layout R1 Implementation

Date: 2026-06-01

Records the **R1 implementation** of the G3 BOM-derived auto-layout follow-up, per
the merged scope-lock taskbook `DEVELOPMENT_ODOOPLM_G3_BOM_AUTO_LAYOUT_TASKBOOK_20260530.md`
(#684, including its review-resolution: ambiguous `item_id` → **skip + warn**, never
guess). Baseline `main = b9c561e8`. Geometry-free; **no migration, no new
table/model** — reuses the existing explode-config storage.

## 1. Step-0 grounding re-confirmed (taskbook §11)

- `component_ref` remains opaque/client-defined; the binding never assumes
  `component_ref == item_id`.
- `BOMService.get_bom_structure` tree shape (`node["children"][] =
  {"relationship": rel.to_dict(), "child": child.to_dict()}`) confirmed —
  relationship id = `rel["id"]`, child item id = `child["id"]`, depth =
  recursion level, sibling order = index among siblings.
- Storage path = `meta_3d_overlays.properties["explode"]` (existing JSON
  column); `math` already imported; route count 690 baseline.

## 2. What changed

- `services/parallel_tasks_service.py` — `ThreeDOverlayService` gains:
  - `build_auto_layout(...)` — **READ-ONLY**: loads the overlay (REQUIRED, no
    auto-create; visibility gate via `get_overlay`), flattens
    `BOMService.get_bom_structure(relationship_types=["Part BOM"])` to child nodes
    (root excluded), binds `part_refs` → BOM nodes, returns
    `{explode:{factor,mode:"bom-depth",offsets[]}, binding:{matched,skipped,warnings[]}}`.
  - `_flatten_bom_nodes` / `_auto_layout_offset` static helpers — geometry-free:
    primary `axis` offset = `depth*depth_spacing*factor`, orthogonal sibling
    spread = `order*sibling_spacing*factor`; rejects non-finite.
- `web/parallel_tasks_cad_3d_router.py` — `ExplodeAutoLayoutRequest`
  (`root_item_id`, `levels`/`factor`/`depth_spacing`/`sibling_spacing` bounded,
  `axis: Literal["x","y","z"]`, `persist`) + `POST
  /api/v1/cad-3d/explode/{document_item_id}/auto-layout`: 403 on visibility,
  404 on missing overlay / BOM root, persists via the existing `upsert_explode`
  **iff `persist=true`** (400 on persist failure).
- Route count **690 → 691**; all four pins bumped + cad-3d contracts route set
  extended; full-tree residual scan clean.
- This DEV/verification record + one sorted `DELIVERY_DOC_INDEX.md` entry.

## 3. §4 binding LOCK realized

Binding precedence (never `component_ref == item_id`):
1. `relationship_id` / `bom_relationship_id` → BOM relationship id; unresolved →
   skip + `unmapped_component_ref`.
2. else `item_id` → BOM child item id: **unique only**; a **duplicate `item_id`
   is SKIPPED** with a per-component `ambiguous_item_id_fallback` warning (the
   #684 review resolution — no shallowest/first guess); no match → skip +
   `unmapped_component_ref`.
3. else skip. Root item gets no offset (R1 = child components only).

**Deliberate decision beyond the taskbook's literal text:** an unresolved
`relationship_id` is **terminal** — the row is skipped (`unmapped_component_ref`)
and its `item_id` is NOT consulted as a fallback. The taskbook §4 ("If
relationship_id… Otherwise if item_id…") doesn't specify the relationship_id-
present-but-unresolved case; falling back to `item_id` would re-introduce exactly
the guessing the §4 LOCK exists to prevent (a client that named a relationship
and got it wrong is a data error, not a hint). Covered by
`test_auto_layout_unresolved_relationship_id_does_not_fall_back_to_item_id`.

## 4. Verification

- DB-backed (`YUANTUS_PYTEST_DB=1`) — **261 passed** across the *full*
  `test_parallel_tasks_services.py` + `test_parallel_tasks_router.py` +
  `test_parallel_tasks_cad_3d_router_contracts.py` + the 4 route-pin contracts
  (zero-regression gate). New coverage:
  - service (real SQLite, self-contained fixture with a **diamond BOM**):
    relationship-id binding + unique item-id binding both match; **duplicate
    item-id skipped + `ambiguous_item_id_fallback`**; unmapped skipped +
    `unmapped_component_ref`; **overlay and part_refs required (no silent
    success)**; role-gate inheritance.
  - router (mock service): `persist=true` writes / `persist=false` does NOT call
    `upsert_explode`; invalid `axis` → 422; missing overlay → 404; visibility →
    403.
  - §8 **static source guards**: auto-layout code (docstrings/comments stripped)
    has no geometry tokens (trimesh/bbox/centroid/mesh/…), never
    `component_ref==item_id`, adds no table/`Column(`/migration, no
    odoo/GPL/AGPL.
- `create_app()` → **691** routes; migration-coverage 4 (no new table); verifiers
  28/13; `git diff --check` clean.
- **Test wiring**: all changes **extend existing files** (no new test file) → no
  conftest allowlist / ci.yml / portfolio change ([[feedback-test-file-ci-wiring-fanout]]).

## 5. CI shape (merge-readiness)

This PR edits `DELIVERY_DOC_INDEX.md`, so **`contracts` runs** (route pins +
cad-3d contracts + doc-index) — but the new behavioral tests run **only under
`regression`**. **Merge-readiness = `regression: pass`** (a real run), not just
aggregate CLEAN.

## 6. Non-Goals upheld

No server-side geometry/mesh/bbox/transform; no client rendering; no
multiple-named-presets table; no migration; the offsets are a deterministic
default, **not** a spatial-correctness guarantee; no GPL/AGPL/OdooPLM reuse.

## 7. Status

G3 BOM auto-layout R1 implemented and verified — the explicit-binding-only,
geometry-free default the taskbook scoped. Remaining OdooPLM items (each
separately opted-in): G4 category/property token; the minor gaps
(finishing/treatment, `plm_project`).
