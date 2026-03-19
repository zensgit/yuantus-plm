# C16 – Quality SPC / Analytics Bootstrap

## Scope
Add Statistical Process Control (SPC) capability indices, control chart analysis,
and quality analytics (defect rates, result distributions, alert aging, point
effectiveness) on top of the C4 quality bootstrap.

## New Files
| File | Purpose |
|------|---------|
| `quality/spc_service.py` | Cp/Cpk/Pp/Ppk, control charts, OOC detection |
| `quality/analytics_service.py` | Defect rates, distributions, alert aging, effectiveness |
| `web/quality_analytics_router.py` | 5 API endpoints |
| `tests/test_quality_spc_service.py` | 10 tests |
| `tests/test_quality_analytics_service.py` | 8 tests |
| `tests/test_quality_analytics_router.py` | 7 tests |

## Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/quality/analytics` | Full analytics report |
| GET | `/quality/analytics/defect-rates` | Per-point defect rates |
| GET | `/quality/analytics/alert-aging` | Open alert age buckets |
| POST | `/quality/spc` | SPC from raw measurements payload |
| GET | `/quality/spc/{point_id}` | SPC from a point's checks |

## Dependencies
- Cherry-picks `12c2066` (C4 quality bootstrap) as foundation.
- No new DB tables; pure-Python analytics over existing model data.
