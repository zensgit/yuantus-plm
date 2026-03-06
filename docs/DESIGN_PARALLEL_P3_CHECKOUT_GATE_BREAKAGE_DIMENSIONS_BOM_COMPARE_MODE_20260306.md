# Parallel P3 Design: Checkout Gate + Breakage Dimensions + BOM Compare Mode

Date: 2026-03-06

## Background

This iteration continues the parallel-track plan after the Odoo18 enterprise reference study and implements three directly shippable branches:

1. Checkout gate strictness/threshold policy
2. Breakage grouped dimensions extension
3. BOM compare mode extension

## Odoo18 Reference Mapping

- `references/odoo18-enterprise-main/addons/plm_document_multi_site/*`
  - Borrowed idea: checkout/edit should be guarded by remote sync backlog state, with policy controls.
- `references/odoo18-enterprise-main/addons/plm_ent_breakages_helpdesk/*`
  - Borrowed idea: breakage cockpit should support richer operational dimensions for triage and ownership slices.
- `references/odoo18-enterprise-main/addons/plm_compare_bom/*`
  - Borrowed idea: BOM diff should expose user-facing compare strategies/modes for different engineering intents.

## Design Decisions

### 1) Checkout gate policy with thresholds

- Extend `DocumentMultiSiteService.evaluate_checkout_sync_gate` with policy/threshold params:
  - `block_on_dead_letter_only`
  - `max_pending`
  - `max_processing`
  - `max_failed`
  - `max_dead_letter`
- Keep backward compatibility by defaulting all thresholds to `0` and `block_on_dead_letter_only=False`.
- Add response diagnostics for operator transparency:
  - `policy`
  - `thresholds`
  - `blocking_reasons`
- In `version_router.checkout`, pass-through the new knobs and keep existing 409 flow when gate is blocking.

### 2) Breakage grouped dimensions (no DB migration)

- Add two derived dimensions using existing columns:
  - `mbom_id` -> `BreakageIncident.version_id`
  - `routing_id` -> `BreakageIncident.production_order_id`
- Extend:
  - `metrics_groups(group_by=...)`
  - `metrics` aggregates
  - `cockpit.metrics` aggregates
  - metrics markdown export payload sections
- Router descriptions updated for discoverability.

### 3) BOM compare mode extension

- Add compare mode `by_item` in `BOMService.COMPARE_MODES`:
  - `line_key=child_id`
  - `include_relationship_props=[quantity,uom]`
  - `aggregate_quantities=True`
- Add aliases: `item`, `by_child`, `child_id`.
- Update compare-mode descriptions in BOM/ECO routers and error text for invalid mode.

## Compatibility & Risk

- API behavior remains backward compatible for current callers using default parameters.
- No schema migration introduced.
- New response keys are additive and non-breaking.
- Main risk is client-side strict parsing of error/help strings; mitigated by preserving old modes and extending strings additively.
