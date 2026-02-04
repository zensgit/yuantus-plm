# Effectivity Extension + Suspended Lifecycle (2026-02-04)

## Background
- DocDoku/PLM references include Date/Lot/Serial effectivities for parts and relationships.
- Odoo PLM adds a suspended/obsolete state for lifecycle control.

## Scope
1) **Effectivity API**: expose Date/Lot/Serial/Unit effectivities for items/versions.  
2) **BOM Effective Filtering**: allow lot/serial/unit context in effective BOM endpoints.  
3) **Lifecycle Suspended**: add Suspended state and suspend/resume transitions for Part/Document lifecycles.  
4) **Verification**: unit tests + integration scripts + verify_all integration.

## API Changes
### New
`POST /api/v1/effectivities`
- Body: `item_id` or `version_id`, `effectivity_type`, optional `start_date/end_date`, `payload`.
- Validates: Date requires start/end; Lot requires `lot_start/lot_end`; Serial requires `serials[]`.

`GET /api/v1/effectivities/{id}`  
`GET /api/v1/effectivities/items/{item_id}`  
`GET /api/v1/effectivities/versions/{version_id}`  
`DELETE /api/v1/effectivities/{id}`

### Updated
`GET /api/v1/bom/{item_id}/effective`
- Added query params: `lot_number`, `serial_number`, `unit_position`.

`GET /api/v1/bom/{parent_id}/tree`
- Added query params: `lot_number`, `serial_number`, `unit_position`.

## Data Model
- Reuses `meta_effectivities`:
  - `effectivity_type`: Date/Lot/Serial/Unit
  - `payload`: Lot `{lot_start, lot_end}`; Serial `{serials[]}`; Unit `{unit_positions[]}`

## Lifecycle Updates
Added **Suspended** state (locked) for Part/Document:
```
Draft -> Review -> Released -> Suspended -> Obsolete
Released -> Suspended (suspend)
Suspended -> Released (resume)
Suspended -> Obsolete (obsolete)
```

## Verification
- Unit: `src/yuantus/meta_engine/tests/test_effectivity.py` (Lot/Serial checks).
- Integration: `scripts/verify_effectivity_extended.sh`, `scripts/verify_lifecycle_suspended.sh`.
- Suite: `scripts/verify_all.sh` includes new scripts.

## Files Changed
- `src/yuantus/meta_engine/web/effectivity_router.py`
- `src/yuantus/api/app.py`
- `src/yuantus/meta_engine/services/bom_service.py`
- `src/yuantus/meta_engine/web/bom_router.py`
- `src/yuantus/meta_engine/tests/test_effectivity.py`
- `src/yuantus/seeder/meta/lifecycles.py`
- `src/yuantus/cli.py`
- `scripts/verify_effectivity_extended.sh`
- `scripts/verify_lifecycle_suspended.sh`
- `scripts/verify_all.sh`
- `docs/DELIVERY_API_EXAMPLES_20260202.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/RELEASE_NOTES_v0.1.3_update_20260203.md`
