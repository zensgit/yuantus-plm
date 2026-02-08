# Roadmap 9.3 Performance Trend

- Generated: `2026-02-09T00:10:23`
- Source dir: `docs/PERFORMANCE_REPORTS`
- Runs: `4` (showing latest `4`)

## Latest Runs

| Started | Git | DB | Overall | Report | Dedup 1000 | Config BOM 500 | MBOM 1000 | Baseline 2000 | Search p95 | E-sign p95 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `2026-02-09T00:10:22.737727+08:00` | `9be8d3d` | `postgres` | PASS | `docs/PERFORMANCE_REPORTS/ROADMAP_9_3_PG_20260209-001013.md` | SKIP | PASS 372.4ms | PASS 1.975s | PASS 1.526s | PASS 22.1ms | PASS 6.1ms |
| `2026-02-09T00:10:13.284867+08:00` | `9be8d3d` | `sqlite` | PASS | `docs/PERFORMANCE_REPORTS/ROADMAP_9_3_20260209-000914.md` | SKIP | PASS 131.7ms | PASS 803.7ms | PASS 545.3ms | PASS 5.9ms | PASS 0.2ms |
| `2026-02-07T14:03:00.786236+08:00` | `2dc3f8f` | `sqlite` | PASS | `docs/PERFORMANCE_REPORTS/ROADMAP_9_3_20260207-135822.md` | PASS 264.239s | PASS 111.7ms | PASS 630.7ms | PASS 484.9ms | PASS 6.4ms | PASS 0.4ms |
| `2026-02-07T13:34:24.890590+08:00` | `1b82b7f` | `sqlite` | PASS | `docs/PERFORMANCE_REPORTS/ROADMAP_9_3_20260207-133420.md` | SKIP | PASS 96.2ms | PASS 532.5ms | PASS 423.8ms | PASS 5.8ms | PASS 0.2ms |

## Notes

- `SKIP` typically indicates missing optional external dependencies (e.g. Dedup Vision sidecar).
- Measured values are copied from each per-run report.
- DB is inferred from the per-run report DB URL.

