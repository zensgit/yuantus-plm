# DEV & Verification: OdooPLM Gap G5 — Spare Parts Implementation

Date: 2026-05-29

Records the **implementation** of the G5 spare-parts gap, per the merged
grounding/scope-lock taskbook
`DEVELOPMENT_ODOOPLM_G5_SPARE_PARTS_TASKBOOK_20260529.md` (#677). Baseline
`main = 19ae08bd`. Code change (not doc-only). The "Part Spare" ItemType +
spare relationship-Items live in the existing item/relationship tables — **no
migration**, no bespoke table, modeled entirely on Yuantus's own
`equivalent_service` precedent (no GPL/AGPL / odooplm code).

## 1. Step-0 grounding outcome (taskbook §9)

- **§9.5 (highest-leverage) — no migration confirmed**: `meta_item_types`
  (`is_relationship`) and the relationship infra are in the **initial schema**
  (`f87ce5711ce1`); **no migration seeds** "Part Equivalent" / "Part BOM
  Substitute" (the only `substitute` hit in `migrations/` is an unrelated
  `include_substitutes` baseline column). The `Part Spare` ItemType is created
  lazily at runtime → spare adds zero migrations. The migration-table-coverage
  contract is therefore unaffected (verified, §4).
- **§9.6 — `_ensure_type` concurrency**: the precedent
  (`ensure_equivalent_item_type` / `ensure_substitute_item_type`) is plain
  check-then-insert with **no lock / no IntegrityError guard** — a latent race
  on concurrent first-call. `SpareService.ensure_spare_item_type` **hardens**
  this: on `IntegrityError` it rolls back and re-confirms the row (created by the
  race winner), so spare does not import the latent race. (Substitute/equivalent
  are intentionally left untouched — out of scope.)
- Closest precedent is `EquivalentService` (Part→Part), not `SubstituteService`
  (BOM-line→Part).

## 2. What changed

- `src/yuantus/meta_engine/services/spare_service.py` — `SpareService`
  (`ensure_spare_item_type` hardened; `add_spare` / `list_spares` /
  `remove_spare` directional: source=assembly Part, related=spare Part;
  `explode_spares` reuses `BOMService.get_bom_structure(relationship_types=
  ["Part BOM"])` read-only, then collects each unique part's spares).
  `SPARE_ITEM_TYPE = "Part Spare"`.
- `src/yuantus/meta_engine/web/spare_router.py` — `spare_router`
  (prefix `/items`, tag "Item Spares"), 4 routes mirroring `equivalent_router`
  auth + ValueError→HTTP mapping:
  - `GET /api/v1/items/{item_id}/spares` (list)
  - `POST /api/v1/items/{item_id}/spares` (add)
  - `DELETE /api/v1/items/{item_id}/spares/{spare_id}` (remove)
  - `GET /api/v1/items/{item_id}/spares/explode` (exploded view, bounded `levels`)
- `src/yuantus/api/app.py` — import + `include_router(spare_router, prefix=
  "/api/v1")` registered immediately after `equivalent_router`.
- Tests: `test_spare_router.py` (mock-based, DB-off, 21 cases) +
  `test_spare_router_contracts.py` (route ownership/registration/tag/order,
  6 cases) → both added to `conftest.py` `_ALLOWLIST_NO_DB` + the `ci.yml`
  contracts list; `test_spare_service.py` (real in-memory SQLite, 9 cases,
  regression — exercises the real `BOMService` explode incl. diamond dedup).
- Route count **684 → 688** (+4): all four pins bumped
  (`test_phase4_search_closeout_contracts.py` authoritative,
  `test_metrics_router_route_count_delta.py` `EXPECTED_TOTAL_ROUTES`,
  `test_breakage_design_loopback_metrics.py`, and the
  `test_tier_b_3_..._portfolio_contract.py` cross-ref string + `_at_688` test
  name). Full-tree `len(app.routes)` residual scan clean.
- This DEV/verification record + one sorted `DELIVERY_DOC_INDEX.md` entry.

## 3. Realized decisions / documented choices

- **Relationship shape**: directional ItemType-relationship (mirrors equivalent's
  create/list/remove verbatim in shape; dedup is directional `source==assembly
  AND related==spare`; `list_spares` lists the source side).
- **Metadata**: a free-form `properties` dict (verbatim precedent shape).
  Conventional keys documented in the request model: `quantity` (consumers treat
  absent as 1), `position`/`ref`, `notes`. No bespoke schema enforced.
- **No release guard**: mirrors `equivalent_service` (Part↔Part designation), not
  `substitute_service` — no `assert_latest_released` / `assert_not_suspended` on
  the spare. (A future tightening, if wanted, is a separate slice.)
- **Permission-before-ensure** is inherited from `equivalent_router`: the router
  checks `Part Spare` permission before the type is lazily created, so a
  non-admin gets 403 until an admin's first add creates the type; admins bypass.
  Identical to the equivalent precedent — not a spare regression.
- **DELETE path** is `/{item_id}/spares/{spare_id}` with a directional
  `source_id == item_id` ownership check (mirrors equivalent's path shape;
  reconciles the taskbook §5 `/spares/{spare_rel_id}` sketch to the precedent).
- **Explode** traverses `Part BOM` (EBOM) only, read-only, dedup by part id in
  document order (root first), `levels` bounded 1..50 (default 10).

## 4. Verification

- DB-off (py311, AUTH optional): `test_spare_router_contracts.py` +
  `test_spare_router.py` + the three route-count pin contracts
  (`test_phase4_search_closeout_contracts.py`,
  `test_metrics_router_route_count_delta.py`,
  `test_tier_b_3_..._portfolio_contract.py`) — **52 passed**.
- DB-backed (`YUANTUS_PYTEST_DB=1`): `test_spare_service.py` — **9 passed**
  (ensure idempotency; add/self-ref/non-part/duplicate; directional list; remove;
  explode multi-level + diamond dedup against a real `BOMService`).
- `test_migration_table_coverage_contracts.py` — **4 passed** (no new table).
- `create_app()` builds; **688** total routes; the 4 spare routes resolve to
  `spare_router`, registered exactly once, tag "Item Spares".
- `verify_lisp_shell_static.py` 28, `verify_bridge_static.py` 13,
  `verify_material_sync_static.py` — pass (unchanged; no client/helper change).
- `ci.yml` re-parsed as valid YAML; both spare test files in the contracts list
  + conftest allowlist. `git diff --check` clean.

## 5. Non-Goals upheld

No purchase / sale / inventory / stock / pricing of spares (ERP-side); no
GPL/AGPL or odooplm code reuse; no bespoke spare table/module; no migration; no
change to `substitute_service` / `equivalent_service` / the BOM engine beyond
reusing `BOMService.get_bom_structure` read-only; no UI.

## 6. Status

G5 spare-parts implemented and verified. Follow-ups (each separately opted-in):
G4 numbering-vocabulary grounding taskbook; other OdooPLM gaps (G3 explode,
minor). A spare release-guard tightening or MBOM-aware explode only with a
grounded need.
