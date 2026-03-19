# C17 – PLM Box Bootstrap – Design

## Goal
- 在独立 `box` 子域内建立 PLM Box bootstrap。
- Mirrors Odoo 18 `product.packaging` concepts — packaging templates with
  dimensions, weight, material type, and content tracking.

## Scope
- `src/yuantus/meta_engine/box/`
- `src/yuantus/meta_engine/web/box_router.py`
- `src/yuantus/meta_engine/tests/test_box_*.py`

## Deliverables
- box item model (BoxItem + BoxContent)
- list/detail/create bootstrap API (5 endpoints)
- export-ready metadata/read model
- state machine (draft → active → archived)
- content tracking (add/list/remove items in boxes)

## Non-Goals
- 不改 `src/yuantus/api/app.py`
- 不改 `parallel_tasks` / `version` / `benchmark_branches`

## Data Model

### Enums

- `BoxType(str, Enum)`: box, carton, pallet, crate, envelope
- `BoxState(str, Enum)`: draft, active, archived

### BoxItem (`meta_box_items`)

| Column | Type | Notes |
|--------|------|-------|
| id | String PK | UUID |
| name | String(200) | required |
| description | Text | optional |
| box_type | String(30) | default "box" |
| state | String(30) | default "draft" |
| width, height, depth | Float | nullable |
| dimension_unit | String(20) | default "mm" |
| tare_weight | Float | empty weight |
| max_gross_weight | Float | max loaded weight |
| weight_unit | String(20) | default "kg" |
| material | String(200) | e.g. "cardboard" |
| barcode | String(200) | optional |
| max_quantity | Integer | capacity |
| cost | Float | per-unit cost |
| product_id | FK → meta_items.id | optional link |
| properties | JSON/JSONB | extensible |
| is_active | Boolean | default True |
| created_at | DateTime | server_default now |
| created_by_id | FK → rbac_users.id | audit |
| updated_at | DateTime | onupdate |

### BoxContent (`meta_box_contents`)

| Column | Type | Notes |
|--------|------|-------|
| id | String PK | UUID |
| box_id | FK → meta_box_items.id | indexed, not null |
| item_id | FK → meta_items.id | indexed, not null |
| quantity | Float | default 1.0 |
| lot_serial | String(200) | optional |
| note | Text | optional |
| created_at | DateTime | server_default now |

## State Machine

```
draft → active → archived (terminal)
```

## Service Layer

`BoxService(session)`:
- `create_box(...)` — validates box_type enum
- `get_box(box_id)` — by PK
- `list_boxes(box_type, state, product_id)` — filtered query
- `update_box(box_id, **fields)` — partial update
- `transition_state(box_id, target_state)` — validated transitions
- `add_content(box_id, item_id, quantity, ...)` — add content entry
- `list_contents(box_id)` — ordered by created_at
- `remove_content(content_id)` — delete
- `export_meta(box_id)` — full box + contents dict for downstream

## API Endpoints

`box_router = APIRouter(prefix="/box", tags=["PLM Box"])`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/items` | Create box item |
| GET | `/items` | List (filters: box_type, state, product_id) |
| GET | `/items/{box_id}` | Get single |
| GET | `/items/{box_id}/contents` | List contents |
| GET | `/items/{box_id}/export-meta` | Export metadata |

## Error Handling

- `ValueError` → HTTP 400 (invalid enum, bad transition)
- Missing box → HTTP 404
