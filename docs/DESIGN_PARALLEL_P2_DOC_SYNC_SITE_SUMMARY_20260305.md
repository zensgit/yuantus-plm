# DESIGN_PARALLEL_P2_DOC_SYNC_SITE_SUMMARY_20260305

- Date: 2026-03-05
- Scope: document multi-site sync site-level summary API.
- Related code:
  - `src/yuantus/meta_engine/services/parallel_tasks_service.py`
  - `src/yuantus/meta_engine/web/parallel_tasks_router.py`

## 1. Goals

1. Provide an operational summary for `document_sync_*` jobs grouped by site.
2. Support runbook-oriented metrics: status distribution, dead-letter count, direction mix, success/failure rates.
3. Keep implementation lightweight and low-risk without schema changes.

## 2. Service Design

1. New validator:
- `_normalize_window_days(window_days)` in `DocumentMultiSiteService`.
- Valid range: `1..90`.

2. New aggregator:
- `sync_summary(site_id=None, window_days=7)`.
- Data source: `ConversionJob` rows with `task_type like document_sync_%` and `created_at >= since`.
- Aggregation dimensions:
  - per-site `total`
  - per-site `by_status`
  - per-site `dead_letter_total` (failed and retries exhausted)
  - per-site `directions.push/pull`
  - per-site `last_job_at`
  - per-site `success_rate` / `failure_rate`
- Global dimensions:
  - `total_jobs`, `total_sites`
  - `overall_by_status`
  - `overall_dead_letter_total`

3. Filter behavior:
- Optional `site_id` filters aggregation to a single target site.
- Older jobs outside window are excluded.

## 3. API Design

1. New endpoint:
- `GET /api/v1/doc-sync/summary`

2. Query params:
- `site_id` (optional)
- `window_days` (default `7`, validated by service)

3. Response contract:
- service payload + `operator_id`

4. Error contract:
- service validation errors map to:
  - HTTP `400`
  - code `doc_sync_summary_invalid`
  - context `{site_id, window_days}`

## 4. Risk and Rollback

1. Risk: large windows can increase in-memory aggregation volume.
- Mitigation: cap window to 90 days.

2. Risk: payload quality differences across legacy jobs.
- Mitigation: defensive defaults for missing `site_id`, `site_name`, `direction`.

3. Rollback:
- Remove `sync_summary` + endpoint; no DB schema/data migration impact.
