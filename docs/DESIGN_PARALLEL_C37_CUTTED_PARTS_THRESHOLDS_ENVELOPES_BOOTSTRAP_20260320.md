# C37 -- Cutted Parts Thresholds / Envelopes Bootstrap -- Design

## Goal
- Extend the isolated `cutted_parts` domain with threshold, envelope, and export-ready helpers.

## Scope
- `src/yuantus/meta_engine/cutted_parts/`
- `src/yuantus/meta_engine/web/cutted_parts_router.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_*.py`

## Planned API
- `GET /api/v1/cutted-parts/thresholds/overview`
- `GET /api/v1/cutted-parts/envelopes/summary`
- `GET /api/v1/cutted-parts/plans/{plan_id}/threshold-check`
- `GET /api/v1/cutted-parts/export/envelopes`

## Planned Service Methods
- `thresholds_overview()` -- Fleet-wide threshold hit-rate summary
- `envelopes_summary()` -- Material and plan envelope summary
- `plan_threshold_check(plan_id)` -- Per-plan threshold detail
- `export_envelopes()` -- Export-ready threshold/envelope payload

## Constraints
- No `app.py` registration.
- No optimization solver or BOM/manufacturing hot-path integration.
- Stay inside the isolated `cutted_parts` domain.
