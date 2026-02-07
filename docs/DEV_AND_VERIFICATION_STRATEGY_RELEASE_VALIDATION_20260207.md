# Dev & Verification Report - Strategy-Based Release Validation (2026-02-07)

This delivery adds "strategy-based validation" for manufacturing release flows:

- Structured release diagnostics APIs (collect multiple precheck failures at once)
- Configurable release rulesets (via env JSON + `ruleset_id` query param)

## API

New endpoints:

- `GET /api/v1/routings/{routing_id}/release-diagnostics?ruleset_id=default`
- `GET /api/v1/mboms/{mbom_id}/release-diagnostics?ruleset_id=default`

Release endpoints now accept an optional ruleset selector (default keeps existing behavior):

- `PUT /api/v1/routings/{routing_id}/release?ruleset_id=default`
- `PUT /api/v1/mboms/{mbom_id}/release?ruleset_id=default`

## Configuration

- `YUANTUS_RELEASE_VALIDATION_RULESETS_JSON` (optional)

Format:

```json
{
  "routing_release": {
    "no_primary": [
      "routing.exists",
      "routing.not_already_released",
      "routing.has_operations",
      "routing.has_scope",
      "routing.operation_workcenters_valid"
    ]
  },
  "mbom_release": {
    "default": [
      "mbom.exists",
      "mbom.not_already_released",
      "mbom.has_non_empty_structure",
      "mbom.has_released_routing"
    ]
  }
}
```

Notes:
- Unknown rule ids are rejected to fail fast.
- Existence rules (`routing.exists` / `mbom.exists`) are always enforced first.

## Implementation

- Ruleset loader + issue model: `src/yuantus/meta_engine/services/release_validation.py`
- Routing release validation + diagnostics: `src/yuantus/meta_engine/manufacturing/routing_service.py`
- MBOM release validation + diagnostics: `src/yuantus/meta_engine/manufacturing/mbom_service.py`
- Router wiring: `src/yuantus/meta_engine/web/manufacturing_router.py`
- Settings: `src/yuantus/config/settings.py`

## Verification

- Unit tests:
  - `src/yuantus/meta_engine/tests/test_manufacturing_release_diagnostics.py`
  - `src/yuantus/meta_engine/tests/test_manufacturing_routing_router.py`
  - `src/yuantus/meta_engine/tests/test_manufacturing_mbom_router.py`
- Strict gate:
  - `docs/DAILY_REPORTS/STRICT_GATE_20260207-131352.md` (PASS)

