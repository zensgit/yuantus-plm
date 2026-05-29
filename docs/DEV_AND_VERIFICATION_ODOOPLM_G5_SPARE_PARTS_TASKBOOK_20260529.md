# DEV & Verification: OdooPLM Gap G5 — Spare Parts Grounding/Scope-Lock Taskbook

Date: 2026-05-29

Records the doc-only delivery of
`DEVELOPMENT_ODOOPLM_G5_SPARE_PARTS_TASKBOOK_20260529.md` — the grounding +
scope-lock for the G5 spare-parts gap. Doc-only: no code; merging it does **not**
authorize the spare-parts implementation. Baseline `main = 428900b3` (after G2 R4,
the first OdooPLM-gap slice).

## 1. What changed

- New G5 grounding/scope-lock taskbook (gap re-verified; ItemType-relationship
  approach mirroring substitute/equivalent; model/API/explode shape; no
  migration; non-goals; step-0 + preconditions).
- This DEV/verification record.
- Two sorted `DELIVERY_DOC_INDEX.md` entries (under `## Development &
  Verification`).

## 2. Grounding (against `main = 428900b3`)

- **Gap real**: no `*spare*` module/file under `src/yuantus`; no non-test `spare`
  reference. The 05-25 "spare→0 files" claim still holds.
- **Precedent for the approach**: `substitute_service` (`ItemType "Part BOM
  Substitute"`, `is_relationship=True`, `_ensure_type`) + `equivalent_service`
  (`ItemType "Part Equivalent"`), each with a router
  (`bom_substitutes_router` / `equivalent_router`) and **no bespoke table**. G5
  mirrors this — `ItemType "Part Spare"` + `SpareService` + `spare_router`.
- `ItemType.is_relationship` (meta_schema.py:29) makes relationships first-class
  typed items (the meta-engine differentiator); the legacy `meta_relationships`
  table is deprecated for new writes. So G5 uses the ItemType-relationship path
  (consistent with the comparison doc's §6.5 "ItemType + 关系" recommendation).

## 3. Locked decisions (summary)

Model spare parts as an `ItemType "Part Spare"` (`is_relationship=True`) mirroring
substitute/equivalent — **not** a bespoke table; a `SpareService` + a
`spare_router` (list / add / remove + exploded view); spare link = relationship-Item
(source=parent, related=spare part) with `quantity`/`position`/`notes` in
`properties`; the exploded view reuses BOM traversal (read-only); **no migration**
(existing tables); route count +N at impl (residual scan). Non-goals: no
purchase/sale/inventory/pricing of spares, no GPL/AGPL, no bespoke table.

## 4. Verification (this doc-only PR)

- doc-contract pytests — delivery-doc-index references; `## Development &
  Verification` sorting + completeness; doc-index sorting — pass.
- `verify_lisp_shell_static.py` 28, `verify_bridge_static.py` 13 — pass
  (unchanged; no client/helper change).
- `git diff --check` clean.

## 5. Status

Doc-only grounding + scope-lock. Ratifying §3–§8 of the taskbook sets the spare
implementation plan; the spare implementation needs its own explicit opt-in. G4
(numbering vocabulary) and the other OdooPLM gaps remain separately-opted.
