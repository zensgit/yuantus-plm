# ADR: PLM Core Convergence — ECO Write Path

**Status:** Accepted  
**Date:** 2026-04-13  
**Authors:** Claude, Codex, Maintainer  

## Context

The codebase had two parallel write paths for Engineering Change Orders:

1. **`/ecm` (legacy)** — `change_router.py` → `ChangeService` — used Aras-style
   "Affected Item" relationships (`Item(item_type_id="Affected Item")`), executed
   ECOs by iterating affected items and directly performing Release/Revise/New
   Generation without approval workflow.

2. **`/eco` (canonical)** — `eco_router.py` → `ECOService` — full stage pipeline
   with SLA, approval, 3-way merge rebase, impact analysis, custom workflow hooks.

Both were registered in `app.py` and the frontend called both depending on the
operation.  The `/eco` PUT endpoint also bypassed `ECOService.update_eco()`,
directly mutating model fields without permission checks, event emission, or
audit trail.

## Decision

### 1. `/eco` is the single canonical write path

All ECO create, bind, update, approve, execute, and rebase operations go through
`ECOService` methods.

### 2. Product binding is a separate command, not a generic update

`POST /eco/{eco_id}/bind-product` is the only way to associate a product with an
ECO.  `PUT /eco/{eco_id}` only accepts metadata fields (name, description,
priority, effectivity_date) via a field whitelist.

**Why separate:**
- Binding has business rules (idempotent, reject rebind, target_version guard)
  that don't fit generic PATCH semantics.
- The PUT endpoint was previously broken (bypassed service layer), so we fixed
  it and hardened it simultaneously.

### 3. `/ecm` is retained as a thin compatibility shim

`change_router.py` now delegates to `LegacyEcmCompatService` which maps old
endpoint semantics to `ECOService` calls:
- `POST /ecm/.../affected-items` → `bind_product()` (only `action="Change"`)
- `POST /ecm/.../execute` → `get_apply_diagnostics()` → `action_apply()` (requires APPROVED state)
- All responses include `Deprecation` and `Sunset` headers

### 4. `ChangeService` is deprecated

Retained only for existing `test_change_service.py` assertions.  No new code
should import it.

## Consequences

- **Frontend**: `workbench.html` switched from `/ecm` to `/eco/bind-product`
- **API consumers**: `/ecm` still works but returns deprecation headers
- **Tests**: 32 new tests cover bind_product rules, update whitelist, compat
  shim behavior, and an e2e main chain test
- **Sunset**: `/ecm` endpoints and `ChangeService` to be removed after confirming
  zero traffic (target: 2026-07-01)

## Files Changed

| File | Change |
|------|--------|
| `eco_service.py` | Added `bind_product()`, hardened `update_eco()` with whitelist + state guard |
| `eco_router.py` | Added `POST /{eco_id}/bind-product`, fixed `PUT /{eco_id}` to use service |
| `change_router.py` | Rewritten as compat shim over `LegacyEcmCompatService` |
| `legacy_ecm_compat_service.py` | New — maps old /ecm shapes to canonical calls |
| `change_service.py` | Marked deprecated |
| `workbench.html` | Switched eco-add-affected to `/eco/bind-product` |
| `app.py` | Added sunset comment on change_router registration |
