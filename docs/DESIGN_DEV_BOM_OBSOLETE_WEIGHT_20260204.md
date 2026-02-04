# BOM Obsolete Handling + Weight Rollup (Design/Dev 2026-02-04)

## Goals

- Detect obsolete BOM lines under a root item (by lifecycle end state or non-current item).
- Provide two resolution modes:
  - `update`: swap line to a replacement item in-place.
  - `new_bom`: clone all current BOM lines for the parent and apply replacements, leaving history.
- Provide BOM weight rollup with optional write-back to item properties.

## Implementation Summary

### 1) Obsolete BOM Service

- New service: `src/yuantus/meta_engine/services/bom_obsolete_service.py`.
- Scan flow:
  - BFS over current BOM relationship lines (`Part BOM`, `Manufacturing BOM`).
  - Obsolete reasons:
    - child missing
    - child `is_current == false`
    - lifecycle end state or `state == Obsolete`
    - property flags: `obsolete=true`, `is_obsolete=true`, `engineering_state=obsoleted`
  - Replacement resolution:
    - `properties.replacement_id` or `properties.superseded_by`
    - fallback: same `config_id` + `is_current` + not Obsolete
- Resolve flow:
  - `update`: modify `related_id` on relationship items.
  - `new_bom`: clone all current lines for each affected parent, copy effectivities + substitutes, mark old lines `is_current=false`.

### 2) Weight Rollup Service

- New service: `src/yuantus/meta_engine/services/bom_rollup_service.py`.
- Uses `BOMService.get_bom_structure()` to build a tree and recursively compute:
  - `own_weight` from `properties.weight`
  - `computed_weight` sum of child weights × quantity
  - `total_weight` prefers `own_weight` when present
- Optional write-back:
  - default `write_back_field=weight_rollup` + `write_back_mode=missing`
  - skips items locked by lifecycle state

## API Additions

- `GET /api/v1/bom/{item_id}/obsolete`
- `POST /api/v1/bom/{item_id}/obsolete/resolve`
- `POST /api/v1/bom/{item_id}/rollup/weight`

## Key Files

- `src/yuantus/meta_engine/services/bom_obsolete_service.py`
- `src/yuantus/meta_engine/services/bom_rollup_service.py`
- `src/yuantus/meta_engine/web/bom_router.py`
- `scripts/verify_bom_obsolete.sh`
- `scripts/verify_bom_weight_rollup.sh`
- `playwright/tests/bom_obsolete_weight.spec.js`

## Notes

- Obsolete detection aligns with Aras/Odoo-style “obsolete lines” while remaining compatible with Yuantus item/version model.
- `new_bom` preserves history by keeping old relationship lines in the DB (`is_current=false`).
- Rollup results include `missing_items` to highlight incomplete weight data.
