# C19 Cutted Parts Bootstrap Design

## Goal
- 在独立 `cutted_parts` 子域内建立 cutted-parts bootstrap。

## Scope
- `src/yuantus/meta_engine/cutted_parts/`
- `src/yuantus/meta_engine/web/cutted_parts_router.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_*.py`

## Deliverables
- raw material / cut plan bootstrap model
- list/detail/summary read model
- export-friendly response contract

## Non-Goals
- 不改 `src/yuantus/api/app.py`
- 不改 BOM / manufacturing 热服务

## Data Model

### Enums
- `MaterialType`: sheet, bar, tube, coil, plate
- `CutPlanState`: draft → confirmed → in_progress → completed (cancel from draft/confirmed/in_progress)
- `CutResultStatus`: ok, scrap, rework

### Tables
| Table | Model | Purpose |
|-------|-------|---------|
| `meta_raw_materials` | `RawMaterial` | Stock material with dimensions, weight, cost |
| `meta_cut_plans` | `CutPlan` | Cutting plan with state machine and metrics |
| `meta_cut_results` | `CutResult` | Individual cut piece outcome with status/scrap tracking |

### Key Fields
- **RawMaterial**: name, material_type, grade, length/width/thickness, dimension_unit, weight_per_unit, weight_unit, stock_quantity, cost_per_unit, product_id (FK meta_items), properties (JSONB)
- **CutPlan**: name, description, state, material_id (FK meta_raw_materials), material_quantity, total_parts, ok/scrap/rework counts, waste_pct, properties (JSONB)
- **CutResult**: plan_id (FK), part_id (FK meta_items), length, width, quantity, status, scrap_weight, note

## Service Layer

`CuttedPartsService(session: Session)`:
- Material CRUD: `create_material`, `list_materials` (filter by type/active)
- Plan CRUD: `create_plan`, `get_plan`, `list_plans`, `update_plan`
- State machine: `transition_plan_state` (validated transitions)
- Cut results: `add_cut` (validates status enum), `list_cuts`
- Summary: `plan_summary` (aggregates by_status, total_scrap_weight, total_quantity)

## Router

`cutted_parts_router` — prefix `/cutted-parts`, tags `["Cutted Parts"]`

| Method | Path | Handler |
|--------|------|---------|
| POST | `/plans` | Create plan |
| GET | `/plans` | List (filter: state, material_id) |
| GET | `/plans/{plan_id}` | Get single |
| GET | `/plans/{plan_id}/summary` | Stock usage / waste summary |
| GET | `/plans/{plan_id}/cuts` | List cuts for plan |
| GET | `/materials` | List materials (filter: type, is_active) |

## State Transitions

```
draft → confirmed → in_progress → completed
  ↓        ↓            ↓
cancelled cancelled  cancelled
```

Completed and cancelled are terminal states.
