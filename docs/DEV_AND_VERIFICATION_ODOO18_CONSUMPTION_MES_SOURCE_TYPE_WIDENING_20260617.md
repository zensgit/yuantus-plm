# Dev & Verification: MES `source_type` widening (Consumption R2.3)

Date: 2026-06-17
Status: **IMPLEMENTED** — pending gate review + merge
Roadmap item: `DEVELOPMENT_ROADMAP_AND_TODO_20260617.md` §2 R2.3.
Follows R2 (#778) / R2.1 (#779) / R2.2 (#781/#782).

## 1. Summary

Widens the MES ingestion `source_type` allowlist beyond `{mes, workorder}` to two additional
**positive-consumption** sources — **`scrap`** (material consumed and scrapped during
production) and **`rework`** (material consumed in a rework operation). Both are
`actual_quantity >= 0` consumption events that `variance` sums, so they fit the existing model
with no semantic change. Reversal/negative semantics (`return` / 冲销) are deliberately **not**
added (see §3).

## 2. Change

- `services/consumption_mes_contract.py`: `ALLOWED_SOURCE_TYPES = frozenset({"mes", "workorder",
  "scrap", "rework"})` + the comment documents each source and the positive-consumption
  invariant. Nothing else changes: the DTO validator already lower-cases + checks membership; the
  idempotency key already includes `source_type` (so scrap vs workorder for the same
  `mes_event_id` are **distinct** events → distinct rows, no collision); uom/variance/route
  unchanged.

## 3. Out of scope (carved out — not folded into the enum)

`return` / 冲销 / any reversal: the contract enforces `actual_quantity >= 0` (DTO
`_finite_non_negative`) and `variance` only **sums** (no offset), so a reversal source cannot be
a plain enum value — it needs its own taskbook (negative quantity or an explicit offset
mechanism + variance changes). The tests assert reversal-flavored names stay **rejected**.

## 4. Verification (`test_consumption_mes_ingestion_contract.py` + `_runtime.py`, 62 pass)

- the boundary set is exactly `{mes, workorder, scrap, rework}`; `manual` still rejected.
- `scrap`/`rework` accepted (case-insensitive normalize); `return`/`reversal`/`offset`/`credit`
  still rejected.
- runtime: a `scrap` event ingests → `CREATED`, persists `source_type="scrap"`; a `scrap` and a
  `workorder` event sharing a `mes_event_id` produce **two** rows (source_type is in the key),
  variance sums both.
- no route added (count 713), no migration, no pin change; idempotency/uom/variance/manual
  `/actuals` unaffected.

## 5. Files

`services/consumption_mes_contract.py` · `tests/test_consumption_mes_ingestion_contract.py` ·
`tests/test_consumption_mes_ingestion_runtime.py` · `docs/DELIVERY_DOC_INDEX.md` (this doc).
