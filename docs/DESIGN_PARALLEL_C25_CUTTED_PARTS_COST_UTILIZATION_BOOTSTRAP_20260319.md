# C25 - Cutted Parts Cost / Utilization Bootstrap - Design

## Goal
Extend the isolated `cutted_parts` domain with cost and utilization read helpers without coupling the increment to BOM or manufacturing hot paths.

## Scope
- `src/yuantus/meta_engine/cutted_parts/`
- `src/yuantus/meta_engine/web/cutted_parts_router.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_*.py`

## Deliverables

### Service Methods (5)
| Method | Purpose |
|--------|---------|
| `utilization_overview()` | Fleet-wide utilization: avg %, high/medium/low buckets |
| `material_utilization()` | Per-material consumption vs stock, remaining quantity |
| `plan_cost_summary(plan_id)` | Per-plan: material cost, cost per good part, scrap weight |
| `export_utilization()` | Combined utilization_overview + material_utilization |
| `export_costs()` | All plans with cost summaries, total material cost |

### Router Endpoints (5)
| Method | Path | Handler |
|--------|------|---------|
| GET | `/utilization/overview` | Fleet-wide utilization summary |
| GET | `/materials/utilization` | Material consumption breakdown |
| GET | `/plans/{plan_id}/cost-summary` | Per-plan cost analysis (ValueError→404) |
| GET | `/export/utilization` | Export-ready utilization payload |
| GET | `/export/costs` | Export-ready cost payload |

### Tests
- **Service**: TestCosting class – 11 tests (utilization overview ×3, material utilization ×2, plan cost summary ×3, export utilization, export costs ×2)
- **Router**: 7 tests (one per endpoint + 404 for cost-summary)

## Non-Goals
- no app registration
- no optimization solver
- no BOM/manufacturing hot-path integration
