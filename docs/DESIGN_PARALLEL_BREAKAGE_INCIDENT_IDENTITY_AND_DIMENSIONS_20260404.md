# Design: Breakage Incident Identity and Dimensions

## Date

2026-04-04

## Goal

Close package 1 from the breakage/helpdesk traceability audit:

- add first-class `bom_id`
- add first-class `mbom_id`
- add first-class `routing_id`
- add generated `incident_code`

This package intentionally does **not** add latest helpdesk ticket summary to
incident rows. That remains the next package.

## Scope

Files changed:

- `migrations/versions/c4d5e6f7a8b9_add_breakage_incident_identity_dimensions.py`
- `src/yuantus/meta_engine/models/parallel_tasks.py`
- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`
- breakage service/router tests

## Implementation

### 1. Model contract

`BreakageIncident` now includes:

- `incident_code`
- `bom_id`
- `mbom_id`
- `routing_id`

Legacy fields remain:

- `version_id`
- `production_order_id`

The package keeps these legacy aliases for compatibility while normalizing the
public contract around the new first-class fields.

### 2. Alias normalization on create

`create_incident()` now accepts both:

- new fields: `bom_id`, `mbom_id`, `routing_id`
- legacy aliases: `version_id`, `production_order_id`

Rules:

- if both new and legacy aliases are provided, they must match
- normalized values are stored into both the first-class fields and the legacy
  alias fields
- new incidents receive generated `incident_code` values like `BRK-000001`

### 3. Incident serialization

Incident-facing surfaces now project:

- `incident_code`
- `bom_id`
- `mbom_id`
- `routing_id`

while still preserving:

- `version_id`
- `production_order_id`

### 4. Metrics / cockpit / grouping

This package extends the breakage analytics contract to include `bom_id` as a
first-class grouped dimension:

- `by_bom_id`
- `top_bom_ids`
- `group_by=bom_id`

It also switches `mbom_id` / `routing_id` grouping away from alias-only mapping
and onto the normalized incident fields.

### 5. Migration

Alembic migration `c4d5e6f7a8b9`:

- adds the 4 new columns
- adds indexes
- backfills:
  - `mbom_id <- version_id`
  - `routing_id <- production_order_id`
  - generated `incident_code` for existing rows

## Compatibility

This package is additive and compatibility-oriented:

- existing callers that still send `version_id` / `production_order_id` continue
  to work
- existing readers that still consume `version_id` / `production_order_id`
  continue to work
- new callers/readers can move to `mbom_id` / `routing_id` / `bom_id` /
  `incident_code`

## Out of Scope

- latest helpdesk ticket summary on incident list/export/cockpit rows
- new list/export filters on `bom_id` / `mbom_id` / `routing_id`
- any helpdesk sync lifecycle changes

## Result

Package 1 is closed.

Remaining next package for this line:

- `breakage-helpdesk-latest-ticket-summary`
