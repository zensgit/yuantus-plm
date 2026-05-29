# Claude Taskbook: OdooPLM Gap G5 — Spare Parts (`plm_spare`) Grounding + Scope-Lock

Date: 2026-05-29

Type: **Doc-only taskbook (grounding + scope-lock).** It re-verifies the G5
spare-parts gap against current `main`, grounds the implementation approach on the
**existing** Yuantus item-relationship precedent (`substitute_service` /
`equivalent_service`), and scope-locks the slice boundaries. It changes no code.
**Merging this taskbook does NOT authorize the spare-parts implementation** — that
requires its own explicit opt-in.

Origin: `DEVELOPMENT_ODOOPLM_GROUNDED_COMPARISON_20260525.md` §5 G5 (备件,
mid impact / high fixability, "`spare`→0 文件,确为真缺失"), §6.5 ("新增 spare
（爆炸备件视图/备件目录）,可作为 meta_engine ItemType + 关系实现"). Baseline
`main = 428900b3` (after G2 R4).

## 0. What this is (and is not)

- The **first** OdooPLM-gap slice after G2; a **new domain** (spare parts), not an
  extension of the ERP-publication line.
- **Grounding first**: this taskbook re-verified the gap and the approach against
  current code (below), so the scope-lock is precedent-backed, not assumed.
- **No GPL/AGPL**: aligns with odooplm's `plm_spare` **semantics/contract only**
  (spare-parts designation + catalog/exploded view). No odooplm code is read,
  ported, or adapted.

## 1. Gap re-verified (against `main = 428900b3`)

- **`plm_spare` is genuinely absent**: no `*spare*` module/file under
  `src/yuantus`, no non-test `spare` reference in `src/yuantus/**.py`. The 05-25
  "spare→0 files" claim still holds on current main. The gap is **real**.
- The comparison doc's own G5 recommendation (§6.5): implement spare as a
  **meta_engine ItemType + relationship** — consistent with §7 (the meta-engine
  ItemType/relationship machinery is the Yuantus differentiator).

## 2. Semantic target (grounded, contract-level)

`plm_spare` = **spare-parts management**: designate which parts are spare parts of
a product/assembly, and surface them as a **spare-parts catalog** + an
**exploded spare-parts view** (the spares reachable down an assembly). This is an
**item-to-item relationship** (parent item → its spare-part items, with metadata),
NOT a purchase/inventory/pricing feature (those are ERP-side, out of scope).

## 3. Approach (ratify) — mirror the existing item-relationship precedent

**Recommendation: model spare parts as an ItemType-relationship, mirroring
`substitute_service` / `equivalent_service`** — NOT a bespoke table/module.

Grounded precedent (current main):
- `services/substitute_service.py`: `ItemType "Part BOM Substitute"`,
  `is_relationship=True`, `_ensure_type()` creates it if absent; router
  `web/bom_substitutes_router.py`.
- `services/equivalent_service.py`: `ItemType "Part Equivalent"`,
  `is_relationship=True`, `_ensure_type()`; router `web/equivalent_router.py`.
- `models/meta_schema.py::ItemType.is_relationship` (line 29) + `models/item.py`
  relationship fields (line 86) — relationships are first-class typed items
  (Aras-style). The **legacy** `relationship/legacy_models.py`
  (`meta_relationships`) is deprecated for new writes.

So G5 introduces:
- a `SpareService` over an `ItemType "Part Spare"` (`is_relationship=True`,
  `_ensure_type()` pattern);
- a `spare_router` (read/add/remove + exploded view);
- spare-relationship **instances** = relationship-Items (source = parent item,
  related = spare-part item) carrying metadata (quantity, position/ref, notes) in
  `properties`.

**Alternative considered + rejected:** a bespoke module (dedicated table + models,
subcontracting-style). Rejected — it would be inconsistent with the existing
item-relationship features (substitute/equivalent), add a needless table +
migration, and bypass the meta-engine differentiator. (A bespoke table is only
warranted if a grounded need emerges that the ItemType-relationship can't model —
not the case here.)

## 4. Model / relationship shape (ratify)

- `ItemType "Part Spare"` (`is_relationship=True`), tenant-visible like the
  substitute/equivalent types; created via `_ensure_type()` (no new SQL table,
  **no migration** — uses the existing item/relationship tables).
- A spare link = a relationship-Item: `source` = the product/assembly item,
  `related` = the spare-part item; `properties`: `quantity` (default 1),
  `position`/`ref` (optional), `notes` (optional).
- Reuse the substitute/equivalent create/list/remove flow verbatim in shape.

## 5. API surface (ratify) — mirror `bom_substitutes_router` / `equivalent_router`

- `GET /…/items/{item_id}/spares` — list an item's direct spare parts.
- `POST /…/items/{item_id}/spares` — add a spare link (related item + metadata).
- `DELETE /…/spares/{spare_rel_id}` — remove a spare link.
- `GET /…/items/{item_id}/spares/explode` — the **exploded spare-parts view**
  (§6).
- Auth: mirror the substitute/equivalent routers (confirm their exact dependency
  in impl step-0). Route count moves by the number of routes added → full-tree
  `grep -rn 'len(app.routes)'` residual scan + bump all pins (currently 684) at
  impl. (No route change in this doc-only taskbook.)

## 6. Exploded spare-parts view (ratify)

`…/spares/explode` recursively resolves spare parts **down the assembly** (a part's
spares, plus the spares of its BOM children), read-only — the analogue of the
existing BOM explode for spare designations. Impl step-0 grounds the recursion on
the existing BOM/explode service to avoid reinventing traversal (and to respect
effectivity/latest-released semantics where relevant).

## 7. Persistence + route-count (ratify)

- **No migration** — the `Part Spare` ItemType + relationship-Items use existing
  tables (exactly as substitute/equivalent add none). The migration-table-coverage
  contract is therefore unaffected. (This rests on a step-0 verification — §9.5 —
  that substitute/equivalent truly add zero migrations.)
- Route count: +N at impl (the `spare_router` routes); residual scan first.

## 8. Non-Goals

No purchase / sale / inventory / stock / pricing of spares (ERP-side; the G2 line
already owns publication, not transactions); no GPL/AGPL reuse; no bespoke spare
table/module; no change to substitute/equivalent or the BOM engine beyond reusing
their patterns; no UI.

## 9. Step-0 to enter the IMPLEMENTATION (grounding the impl must do)

1. Deep-read `substitute_service` + `equivalent_service` + their routers
   (`bom_substitutes_router` / `equivalent_router`) for the exact create / list /
   remove flow, the `_ensure_type` shape, response models, and **auth dependency**
   to mirror.
2. Ground the relationship-Item creation/query path (the AMLEngine / service
   layer) that substitute/equivalent use, so spare links are created/queried the
   same way.
3. Ground the BOM explode/traversal service for the `…/spares/explode` recursion.
4. Confirm test wiring: a new `test_*spare*` file → `conftest.py`
   `_ALLOWLIST_NO_DB` + the `ci.yml` contracts list; route-count pins to bump.
5. **Confirm "no migration" (§7) — highest-leverage check**: grep the migrations
   tree to verify substitute/equivalent added **zero** migrations for their
   ItemType/relationship persistence (i.e. the `Part Spare` ItemType +
   relationship-Items live entirely in the existing `meta_items`/relationship
   tables). If they seeded anything via a migration, spare inherits that and §7
   changes the impl's shape.
6. **`_ensure_type` concurrency**: check whether the substitute/equivalent lazy
   `_ensure_type` guards against a race (two simultaneous first-spare calls
   creating the `Part Spare` ItemType) — now that post-G2 workers / concurrent
   callers exist — so spare does not import a latent race.

## 10. Preconditions to enter the spare IMPLEMENTATION

1. §3 approach (ItemType-relationship mirroring substitute/equivalent, no bespoke
   table) ratified;
2. §4 model/relationship shape + metadata ratified;
3. §5 API surface ratified;
4. §6 exploded-view recursion ratified;
5. §7 no-migration + route-count discipline acknowledged;
6. §8 non-goals (no purchase/inventory/GPL-AGPL) ratified.

A **separate explicit opt-in** then authorizes the implementation.

## 11. Reviewer Focus

1. §1 — gap still real on main (spare absent)?
2. §3 — mirror substitute/equivalent (ItemType-relationship), not a bespoke table?
3. §4/§5 — relationship shape + API mirror the precedent?
4. §6 — exploded view reuses BOM traversal, read-only?
5. §7 — no migration (ItemType-relationship, existing tables)?
6. §8 — purchase/inventory/pricing + GPL/AGPL stay OUT?

## 12. Status

Doc-only grounding + scope-lock. Ready for review once the doc exists at the
canonical path; `DELIVERY_DOC_INDEX.md` references it + its DEV/verification record
(sorted under `## Development & Verification`); doc-index / sorting / completeness
checks pass; `git diff --check` clean. Ratifying §3–§8 sets the spare
implementation plan; **a separate explicit opt-in authorizes the implementation.**
G4 (numbering vocabulary) and the other OdooPLM gaps (G3, minor) remain
separately-opted.
