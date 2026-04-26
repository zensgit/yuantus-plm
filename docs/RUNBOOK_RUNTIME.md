# YuantusPLM Runtime/Deployment Runbook

This runbook describes how to run the stack with db-per-tenant-org and audit,
and how to roll back safely.

## Scope

- Start/stop docker compose stack
- Enable db-per-tenant-org tenancy
- Enable audit logging
- Roll back to single-tenant or disable audit

## Prerequisites

- Docker Desktop running
- `docker compose` available
- Repo root has `.env`

## CAD extractor in compose

The docker compose stack includes the CAD extractor service. The API/Worker
containers use `http://cad-extractor:8200` by default. If you want to disable
external extraction, set `YUANTUS_CAD_EXTRACTOR_MODE=optional` (or clear the
base URL) and restart the stack.

## Enable db-per-tenant-org + audit (docker compose)

1) Ensure `.env` includes:

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@postgres:5432/yuantus_mt_pg__{tenant_id}__{org_id}
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@postgres:5432/yuantus_identity_mt_pg
YUANTUS_AUDIT_ENABLED=true
```

2) Create tenant/org databases (once per environment):

```bash
bash scripts/mt_pg_bootstrap.sh
```

3) Run migrations for identity and tenant/org databases:

```bash
MODE=db-per-tenant-org \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/mt_migrate.sh
```

4) Start or restart services:

```bash
docker compose -p yuantusplm up -d --build
```

5) Verify:

```bash
curl -s http://127.0.0.1:7910/api/v1/health -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
RUN_CAD_EXTRACTOR_SERVICE=1 bash scripts/verify_all.sh
```

## Roll back to single-tenant

1) Update `.env`:

```bash
YUANTUS_TENANCY_MODE=single
YUANTUS_DATABASE_URL_TEMPLATE=
YUANTUS_IDENTITY_DATABASE_URL=
```

2) Restart services:

```bash
docker compose -p yuantusplm up -d --build
```

Notes:
- Multi-tenant data remains in `yuantus_mt_pg__*` databases.
- Single-tenant data remains in `yuantus` database.
- Switching modes does not merge data.

## Roll back audit only

1) Update `.env`:

```bash
YUANTUS_AUDIT_ENABLED=false
```

2) Restart services:

```bash
docker compose -p yuantusplm up -d --build
```

Notes:
- Existing audit rows remain in the database.
- Disabling audit stops new audit writes.

## Version checkout doc-sync gate policy knobs

Endpoint: `POST /api/v1/versions/items/{item_id}/checkout`

New optional request body fields:
- `doc_sync_strictness_mode`
- `doc_sync_block_on_dead_letter_only`
- `doc_sync_max_pending`
- `doc_sync_max_processing`
- `doc_sync_max_failed`
- `doc_sync_max_dead_letter`

Recommended templates:

`strict` (block on any backlog)
```json
{
  "doc_sync_strictness_mode": "block",
  "doc_sync_site_id": "site-a",
  "doc_sync_window_days": 7,
  "doc_sync_limit": 200,
  "doc_sync_block_on_dead_letter_only": false,
  "doc_sync_max_pending": 0,
  "doc_sync_max_processing": 0,
  "doc_sync_max_failed": 0,
  "doc_sync_max_dead_letter": 0
}
```

`warn` (allow checkout, emit warning header, keep gate context available out-of-band)
```json
{
  "doc_sync_strictness_mode": "warn",
  "doc_sync_site_id": "site-a",
  "doc_sync_window_days": 7,
  "doc_sync_limit": 200,
  "doc_sync_block_on_dead_letter_only": false,
  "doc_sync_max_pending": 0,
  "doc_sync_max_processing": 0,
  "doc_sync_max_failed": 0,
  "doc_sync_max_dead_letter": 0
}
```

`tolerant` (block only on dead-letter backlog)
```json
{
  "doc_sync_strictness_mode": "block",
  "doc_sync_site_id": "site-a",
  "doc_sync_window_days": 7,
  "doc_sync_limit": 200,
  "doc_sync_block_on_dead_letter_only": true,
  "doc_sync_max_pending": 20,
  "doc_sync_max_processing": 10,
  "doc_sync_max_failed": 5,
  "doc_sync_max_dead_letter": 0
}
```

Example call:
```bash
curl -s -X POST \
  "http://127.0.0.1:7910/api/v1/versions/items/{item_id}/checkout" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "version_id": "{version_id}",
    "doc_sync_strictness_mode": "warn",
    "doc_sync_site_id": "site-a",
    "doc_sync_block_on_dead_letter_only": true,
    "doc_sync_max_pending": 20,
    "doc_sync_max_processing": 10,
    "doc_sync_max_failed": 5,
    "doc_sync_max_dead_letter": 0
  }'
```

Operator troubleshooting (`409` + `detail.code=doc_sync_checkout_blocked`):
- `policy.block_on_dead_letter_only=true`: only `dead_letter` is evaluated for blocking.
- `thresholds`: effective numeric limits used by the gate.
- `blocking_reasons`: exact exceeded statuses (`count > threshold`).
- `blocking_counts`: observed totals for all statuses; use this to size backlog.
- `blocking_jobs`: concrete jobs/documents to replay or repair before retry.

If request values are invalid, API returns `400` with `detail.code=doc_sync_checkout_gate_invalid`.

When `doc_sync_strictness_mode=warn`, the checkout proceeds and the API returns
`X-Doc-Sync-Checkout-Warning: Checkout allowed despite doc-sync backlog`.

## Observability — request logging and job metrics (Phase 2)

Phase 2 (PRs #414 P2.1, #415 P2.2) adds structured per-request logging and a
Prometheus-format job-metrics endpoint. The contracts pinned in
`src/yuantus/api/tests/test_phase2_observability_closeout_contracts.py`
guard the schemas below — changes to either schema require a deliberate
update to those contracts.

### Per-request log line schema

`RequestLoggingMiddleware` emits one line per HTTP request via the
`yuantus.request` logger. Field set is fixed (every key present, even
when the value is `None`):

| Field | Source | Notes |
| --- | --- | --- |
| `request_id` | `X-Request-ID` header (configurable via `YUANTUS_REQUEST_ID_HEADER`) or generated `uuid4().hex` | Echoed back in response headers for downstream correlation |
| `tenant_id` | `request.state.tenant_id` (set by `AuthEnforcementMiddleware` on auth-success, or `TenantOrgContextMiddleware` from `x-tenant-id` header) | `null` when no identity context |
| `org_id` | `request.state.org_id` (same producers as `tenant_id`) | `null` when no identity context |
| `user_id` | `request.state.user_id` (set only by `AuthEnforcementMiddleware`) | `null` for unauthenticated requests |
| `method` | HTTP method | — |
| `path` | URL path | Query string excluded |
| `status_code` | Final response status code | Includes 401 short-circuits from auth middleware |
| `latency_ms` | Wall time from middleware entry to response finalisation | Integer milliseconds |
| `error` | Exception class name when the request raised | Conditional — only present on exception paths |

Wire format selectable via `YUANTUS_LOG_FORMAT`:

- `text` (default) — `key1=value1 key2=value2 …` (preserves the legacy
  log shape; safe for existing log consumers).
- `json` — single JSON object per line (recommended for log indexers /
  structured log pipelines).

The `request_id` is propagated through inner middleware via the
`request_id_var` ContextVar; identity values are propagated via
`request.state.*` snapshots set at the moment each upstream middleware
calls `ContextVar.set()` (so the snapshot survives the middleware's
own `finally` reset). See P2.1 `DEV_AND_VERIFICATION` MD §4.5 for the
ContextVar-lifetime remediation history.

### Job lifecycle metrics

`JobService.complete_job` and `JobService.fail_job` record into an
in-process Prometheus-format registry via
`yuantus.observability.metrics.record_job_lifecycle`. The registry is
exposed at `GET /api/v1/metrics` (Prometheus scrapers — no JWT
required; gate at the network/ingress layer).

| Metric | Type | Labels | Notes |
| --- | --- | --- | --- |
| `yuantus_jobs_total` | counter | `task_type, status` | One increment per terminal lifecycle event |
| `yuantus_job_duration_ms` | histogram | `task_type, status` | Wall-clock duration (`completed_at - started_at`) |

Permitted `status` values:

- `success` — emitted from `complete_job(...)`.
- `failure` — terminal failure (`fail_job(retry=False)` or max-attempts
  reached).
- `retry` — transient failure that re-queued to PENDING (`retry=True`
  AND `attempt_count < max_attempts`). Duration is captured BEFORE the
  retry branch resets `started_at` / `completed_at`.

Permitted labels (cardinality contract): only `task_type`, `status`,
and Prometheus's own `le` (histogram bucket boundary). **Do not add
`tenant_id` / `org_id` / `user_id` / `job_id` labels** — they blow up
cardinality and break Prometheus retention. Per-tenant observability
belongs in the log line, not the metric.

Histogram bucket boundaries (milliseconds — long-tail for CAD
conversions):

```
[50, 100, 500, 1000, 5000, 10000, 30000, 60000, 300000]
```

Boundaries are observed by downstream alerts and dashboards
(`histogram_quantile()`). **Do not change without explicit discussion**;
the contract test
`test_histogram_bucket_boundaries_are_pinned` enforces this.

### Settings

| Setting | Default | Purpose |
| --- | --- | --- |
| `YUANTUS_LOG_FORMAT` | `text` | `text` or `json` — wire format for the per-request log line |
| `YUANTUS_REQUEST_ID_HEADER` | `x-request-id` | Inbound header read for upstream-supplied request id |
| `YUANTUS_METRICS_ENABLED` | `true` | When `false`, `GET /api/v1/metrics` returns 404; instrumentation always records in-memory regardless |
| `YUANTUS_METRICS_BACKEND` | `prometheus` | Currently only `prometheus` is supported |

### Middleware chain order (pinned)

The following order is asserted by
`test_middleware_chain_order_is_pinned`:

```
RequestLoggingMiddleware  (outermost — sets request_id, captures final status)
  ↓
AuthEnforcementMiddleware  (snapshots tenant/org/user to request.state on auth-success)
  ↓
TenantOrgContextMiddleware  (header-based fallback; snapshots if upstream did not)
  ↓
AuditLogMiddleware  (innermost — sees populated identity context for AuditLog rows)
```

A reorder via `add_middleware` will surface in PR review via the
contract test — it is correctness-load-bearing.

## Stop services

```bash
docker compose -p yuantusplm down
```

## Repo cache cleanup (optional)

```bash
bash scripts/cleanup_repo_caches.sh
```

## Ops FAQ

### Q: cad-ml 端口冲突怎么办？
默认脚本使用 `18000/19090/16379`。可在启动前覆盖端口：

```bash
CAD_ML_API_PORT=18010 CAD_ML_API_METRICS_PORT=19091 CAD_ML_REDIS_PORT=16380 \
  scripts/run_cad_ml_docker.sh
```

排查占用：

```bash
lsof -nP -iTCP:18000 -sTCP:LISTEN
```

### Q: docker compose 提示 “Found orphan containers”？
这是旧 compose 项目遗留容器。可在停止时清理：

```bash
CAD_ML_REMOVE_ORPHANS=1 scripts/stop_cad_ml_docker.sh
```

或手动执行：

```bash
docker compose -f /path/to/compose.yml down --remove-orphans
```
