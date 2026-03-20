# C32 -- PLM Box Policy / Exceptions Bootstrap -- Design

## Goal
- Extend the isolated `box` domain with policy, exception, and export-ready helpers.

## Scope
- `src/yuantus/meta_engine/box/`
- `src/yuantus/meta_engine/web/box_router.py`
- `src/yuantus/meta_engine/tests/test_box_*.py`

## Implemented API
- `GET /api/v1/box/policy/overview`
- `GET /api/v1/box/exceptions/summary`
- `GET /api/v1/box/items/{box_id}/policy-check`
- `GET /api/v1/box/export/exceptions`

## Service Methods
- `policy_overview()` -- Fleet-wide policy compliance summary
- `exceptions_summary()` -- Exception flags across fleet with box ID lists
- `box_policy_check(box_id)` -- Per-box policy check with compliance status
- `export_exceptions()` -- Export-ready payload combining overview + exceptions

## Tests
### Service Tests (8)
- test_policy_overview
- test_policy_overview_empty
- test_exceptions_summary
- test_exceptions_summary_clean
- test_box_policy_check_compliant
- test_box_policy_check_incomplete
- test_box_policy_check_not_found
- test_export_exceptions

### Router Tests (5)
- test_policy_overview
- test_exceptions_summary
- test_box_policy_check
- test_box_policy_check_not_found_404
- test_export_exceptions

## Constraints
- No `app.py` registration.
- No workflow/storage/CAD integration.
- Stay inside the isolated `box` domain.
