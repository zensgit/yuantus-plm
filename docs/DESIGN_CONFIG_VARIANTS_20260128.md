# Configuration / Variant BOM (Design)

Date: 2026-01-28

## Goal

Introduce a minimal configuration/variant layer so BOM structures can be filtered
by option selections (Configuration BOM).

## Scope (Phase 12)

1) Configuration option sets + options (master data)
2) BOM line condition (`config_condition`) stored on relationship items
3) BOM tree filtering by configuration selection

## Data Model

### Option Sets
- Table: `meta_config_option_sets`
- Purpose: groups of selectable options (e.g., Color, Voltage)

Fields:
- `id`, `name`, `label`, `description`
- `item_type_id` (optional scope)
- `is_active`
- `config` (JSON payload)

### Options
- Table: `meta_config_options`
- Purpose: selectable values inside a set

Fields:
- `id`, `option_set_id`
- `key`, `label`, `value`
- `sort_order`, `is_default`, `extra`

## BOM Condition

Relationship item (`meta_items` with `item_type_id=Part BOM`) stores:

```
properties.config_condition
```

### JSON Grammar (MVP)

```
{ "option": "Color", "value": "Red" }
{ "option": "Voltage", "values": ["110", "220"] }
{ "all": [ {...}, {...} ] }
{ "any": [ {...}, {...} ] }
{ "not": {...} }
```

### Simple String (fallback)

```
Color=Red;Voltage=220
```

Parsed as an implicit AND of equality terms.

## BOM Filtering

- New query parameter: `config` (JSON string)
- If provided, BOM tree filters out lines whose `config_condition` evaluates to false.
- If omitted, all lines are returned (no filtering).

Examples:

```
GET /api/v1/bom/{parent}/tree?config={"Color":"Red","Voltage":"220"}
```

## API Endpoints

### Config Option Sets

- `GET /api/v1/config/option-sets`
- `GET /api/v1/config/option-sets/{id}`
- `POST /api/v1/config/option-sets`
- `PATCH /api/v1/config/option-sets/{id}`
- `DELETE /api/v1/config/option-sets/{id}`

### Options

- `POST /api/v1/config/option-sets/{id}/options`
- `PATCH /api/v1/config/option-sets/{id}/options/{option_id}`
- `DELETE /api/v1/config/option-sets/{id}/options/{option_id}`

## Access Control

- Read: any authenticated user
- Write: superuser only (admin)

## Notes

- `config_condition` is intentionally lightweight to keep BOM logic fast.
- For strict variant BOM, use `line_key=relationship_id` or `line_full` in BOM compare.
