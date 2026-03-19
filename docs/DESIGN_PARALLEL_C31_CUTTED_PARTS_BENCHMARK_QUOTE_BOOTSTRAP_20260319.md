# C31 -- Cutted Parts Benchmark / Quote Bootstrap -- Design

## Goal
- Extend the `cutted_parts` sub-domain with benchmark comparison, quote-ready summaries, and export helpers.
- Keep greenfield isolation: no integration into `app.py`.

## Scope
- `src/yuantus/meta_engine/cutted_parts/service.py`
- `src/yuantus/meta_engine/web/cutted_parts_router.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_service.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_router.py`

## Suggested Service Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `benchmark_overview()` | Dict | Plan benchmark counts, cost/utilization ranges, best-known summary |
| `quote_summary(plan_id)` | Dict | Per-plan quote-ready material/cost/waste summary |
| `material_benchmarks()` | Dict | Benchmark aggregation by material family |
| `export_quotes()` | Dict | Export-ready benchmark + quote payload |

## Suggested API Endpoints

| Method | Path | Handler | Error |
|--------|------|---------|-------|
| GET | `/benchmark/overview` | `service.benchmark_overview()` | -- |
| GET | `/plans/{plan_id}/quote-summary` | `service.quote_summary(plan_id)` | ValueError -> 404 |
| GET | `/materials/benchmarks` | `service.material_benchmarks()` | -- |
| GET | `/export/quotes` | `service.export_quotes()` | -- |

## Non-Goals
- No changes to `src/yuantus/api/app.py`
- No optimization solver or BOM/manufacturing hot-path integration
