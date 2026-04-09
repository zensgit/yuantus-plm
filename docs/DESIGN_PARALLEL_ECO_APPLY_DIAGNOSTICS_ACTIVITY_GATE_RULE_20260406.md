# Design: ECO Apply Diagnostics Activity Gate Rule

## Date

2026-04-06

## Scope

Add `eco.activity_blockers_clear` rule to `get_apply_diagnostics()`, matching
the pattern already used in `get_unsuspend_diagnostics()`.

## Problem

`get_apply_diagnostics()` checked state, fields, product, version, and conflicts
but did NOT check activity gate blockers. The activity gate was only checked at
runtime in `action_apply()` via `_ensure_activity_gate_ready()`, meaning
the diagnostics endpoint couldn't surface activity blockers pre-flight.

## Fix

### `release_validation.py`

Added `"eco.activity_blockers_clear"` to `ECO_APPLY_RULES_DEFAULT` after
`eco.state_approved`.

### `eco_service.py` — `get_apply_diagnostics()`

Added handler for `eco.activity_blockers_clear`:
```python
elif rule == "eco.activity_blockers_clear":
    try:
        self._ensure_activity_gate_ready(eco_id)
    except ValueError as exc:
        errors.append(ValidationIssue(
            code="eco_activity_blockers_present",
            message=str(exc),
            rule_id=rule,
            details={"eco_id": eco_id},
        ))
```

Exact same pattern as unsuspend diagnostics (line 829-839).

## Files Changed

| File | Change | LOC |
|------|--------|:---:|
| `release_validation.py` | Added rule to default ruleset | 1 |
| `eco_service.py` | Activity gate handler in get_apply_diagnostics | ~10 |
| `test_eco_apply_diagnostics.py` | New structured error test | ~25 |
