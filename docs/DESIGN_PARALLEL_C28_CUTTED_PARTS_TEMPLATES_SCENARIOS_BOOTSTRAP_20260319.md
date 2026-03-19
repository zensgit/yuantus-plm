# C28 -- Cutted Parts Templates / Scenarios Bootstrap -- Design

## Goal
- Extend the `cutted_parts` sub-domain with reusable templates, scenario comparison, and export-ready helpers.
- Keep greenfield isolation: no integration into `app.py`.

## Scope
- `src/yuantus/meta_engine/cutted_parts/service.py`
- `src/yuantus/meta_engine/web/cutted_parts_router.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_service.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_router.py`

## Suggested Service Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `template_overview()` | Dict | Template count, active scenario count, default material breakdown |
| `scenario_summary(plan_id)` | Dict | Per-plan scenario comparison, waste/cost deltas, best-known snapshot |
| `material_templates()` | Dict | Template grouping by material type and stock profile |
| `export_scenarios()` | Dict | Export-ready payload combining template and scenario summaries |

## Suggested API Endpoints

| Method | Path | Handler | Error |
|--------|------|---------|-------|
| GET | `/templates/overview` | `service.template_overview()` | -- |
| GET | `/plans/{plan_id}/scenarios` | `service.scenario_summary(plan_id)` | ValueError -> 404 |
| GET | `/materials/templates` | `service.material_templates()` | -- |
| GET | `/export/scenarios` | `service.export_scenarios()` | -- |

## Implemented Service Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `template_overview()` | Dict | Template count, active/completed scenario counts, default material breakdown |
| `scenario_summary(plan_id)` | Dict | Per-plan scenario: waste/cost deltas vs fleet avg, material cost |
| `material_templates()` | Dict | Template grouping by material type with stock profile |
| `export_scenarios()` | Dict | Export-ready payload combining template + material + scenario summaries |

## Implemented API Endpoints

| Method | Path | Handler | Error |
|--------|------|---------|-------|
| GET | `/templates/overview` | `service.template_overview()` | -- |
| GET | `/plans/{plan_id}/scenarios` | `service.scenario_summary(plan_id)` | ValueError -> 404 |
| GET | `/materials/templates` | `service.material_templates()` | -- |
| GET | `/export/scenarios` | `service.export_scenarios()` | -- |

## Tests Added

### Service (10 tests in TestTemplatesScenarios)
- test_template_overview, test_template_overview_empty
- test_scenario_summary, test_scenario_summary_waste_delta, test_scenario_summary_no_waste, test_scenario_summary_not_found
- test_material_templates, test_material_templates_empty
- test_export_scenarios, test_export_scenarios_empty

### Router (6 tests)
- test_template_overview, test_scenario_summary, test_scenario_summary_not_found_404
- test_material_templates, test_export_scenarios

## Non-Goals
- No changes to `src/yuantus/api/app.py`
- No optimization solver or BOM/manufacturing hot-path integration
