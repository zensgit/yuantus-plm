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

## Implemented Service Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `benchmark_overview()` | Dict | Plan counts, cost/waste ranges, best-plan identification |
| `quote_summary(plan_id)` | Dict | Per-plan quote: material cost, yield_pct, cost_per_good_part |
| `material_benchmarks()` | Dict | Benchmark aggregation by material: avg waste, cost totals |
| `export_quotes()` | Dict | Export-ready benchmark + material benchmarks + per-plan quotes |

## Implemented API Endpoints

| Method | Path | Handler | Error |
|--------|------|---------|-------|
| GET | `/benchmark/overview` | `service.benchmark_overview()` | -- |
| GET | `/plans/{plan_id}/quote-summary` | `service.quote_summary(plan_id)` | ValueError -> 404 |
| GET | `/materials/benchmarks` | `service.material_benchmarks()` | -- |
| GET | `/export/quotes` | `service.export_quotes()` | -- |

## Tests Added

### Service (11 tests in TestBenchmarkQuote)
- test_benchmark_overview, test_benchmark_overview_empty, test_benchmark_overview_no_waste_data
- test_quote_summary, test_quote_summary_no_material, test_quote_summary_no_cuts, test_quote_summary_not_found
- test_material_benchmarks, test_material_benchmarks_empty
- test_export_quotes, test_export_quotes_empty

### Router (5 tests)
- test_benchmark_overview, test_quote_summary, test_quote_summary_not_found_404
- test_material_benchmarks, test_export_quotes

## Non-Goals
- No changes to `src/yuantus/api/app.py`
- No optimization solver or BOM/manufacturing hot-path integration
