# C32 -- PLM Box Policy / Exceptions Bootstrap -- Design

## Goal
- Extend the isolated `box` domain with policy, exception, and export-ready helpers.

## Scope
- `src/yuantus/meta_engine/box/`
- `src/yuantus/meta_engine/web/box_router.py`
- `src/yuantus/meta_engine/tests/test_box_*.py`

## Suggested API
- `GET /api/v1/box/policy/overview`
- `GET /api/v1/box/exceptions/summary`
- `GET /api/v1/box/items/{box_id}/policy-check`
- `GET /api/v1/box/export/exceptions`

## Constraints
- No `app.py` registration.
- No workflow/storage/CAD integration.
- Stay inside the isolated `box` domain.
