# DEV / Verification — Phase 2 P2.2 Observability Job Metrics (2026-04-26)

## 1. Goal

Phase 2 sub-PR **P2.2** of the next-cycle plan
(`docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md`, §6 — "Phase 2 —
Observability Foundation"): instrument job lifecycle (success / failure /
retry) with a **task_type / status / duration_ms** metric set, and expose
the registry at `GET /api/v1/metrics` in **Prometheus text format**.

Hand-rolled in-process registry (no new runtime dependency) so this PR
matches the lean, no-new-deps pattern P2.1 just shipped.

## 2. Why this PR (not the rest of Phase 2)

| Sub-PR | Scope | This PR? |
| --- | --- | :---: |
| P2.1 | Structured logging middleware + request id propagation | ✅ #414 (separate, parallel) |
| P2.2 | Job metrics endpoint + worker instrumentation | ✅ this PR |
| P2.3 | Phase 2 closeout MD + cross-cutting contracts | sequential after P2.1 + P2.2 land |

P2.3 is **not** opened: its contracts assert the field-schema and
metric-counter set introduced by P2.1 + P2.2; opening it before the
producer PRs land would force its branch to fail until they merge.

## 3. Files Changed

| File | Change | Lines |
| --- | --- | ---: |
| `src/yuantus/observability/__init__.py` | New (empty) package marker | +0 |
| `src/yuantus/observability/metrics.py` | New: in-process metric registry (counter + histogram) + Prometheus text renderer | +124 |
| `src/yuantus/api/routers/metrics.py` | New: `GET /metrics` endpoint (404 when `METRICS_ENABLED=False`) | +18 |
| `src/yuantus/meta_engine/services/job_service.py` | Instrument `complete_job` (success) and `fail_job` (failure / retry); compute duration BEFORE retry-path resets `started_at` | +21 |
| `src/yuantus/api/middleware/auth_enforce.py` | Add `/api/v1/metrics` to public-path allowlist (Prometheus scrapers) | +1 |
| `src/yuantus/config/settings.py` | Add `METRICS_ENABLED`, `METRICS_BACKEND` settings | +8 |
| `src/yuantus/api/app.py` | Import + register `metrics_router` near `health_router` | +2 |
| `src/yuantus/api/tests/test_observability_metrics_registry.py` | New: 7 registry unit tests | +66 |
| `src/yuantus/api/tests/test_metrics_endpoint.py` | New: 6 endpoint tests | +69 |
| `src/yuantus/meta_engine/tests/test_job_service_emits_metrics.py` | New: 7 integration tests (real `JobService` + in-mem SQLite — covers wire-up that registry-only tests miss) | +120 |
| `src/yuantus/meta_engine/tests/test_metrics_router_route_count_delta.py` | New: 2 route-count contract tests (671 → 672) | +30 |
| `docs/DEV_AND_VERIFICATION_OBSERVABILITY_JOB_METRICS_20260426.md` | This MD | +220 |
| `docs/DELIVERY_DOC_INDEX.md` | Index entry | +1 |

## 4. Design

### 4.1 Metric set

| Name | Type | Labels |
| --- | --- | --- |
| `yuantus_jobs_total` | counter | `task_type, status` |
| `yuantus_job_duration_ms` | histogram | `task_type, status` |

`status` values:
- `"success"` — emitted from `JobService.complete_job(...)`.
- `"failure"` — terminal failure (status set to `FAILED`).
- `"retry"` — transient failure that re-queues to PENDING (`retry=True`
  and `attempt_count < max_attempts`).

### 4.2 Histogram buckets (long-tail for CAD workloads)

```
[50, 100, 500, 1000, 5000, 10000, 30000, 60000, 300000] ms
```

Standard Prometheus default buckets (5ms–10s) clip long-tail CAD
conversions. The chosen set covers fast queue jobs (≤ 50 ms) through
multi-minute conversions (5 min). **Do not change without explicit
discussion** — bucket boundaries are observed by downstream alerts /
dashboards.

### 4.3 Hookpoint placement (inside `JobService`, not `job_worker`)

All 4 failure paths in `job_worker._execute_job` route through
`JobService.fail_job(...)` (handler-missing, `JobFatalError`, generic
exception, plus the `complete_job` success path). Instrumenting at
`JobService` is **one site per status** instead of four; future failure
paths added in the worker are covered for free.

### 4.4 Duration-on-retry correctness

`fail_job` resets `job.started_at = None` and `job.completed_at = None`
on the **retry branch** (lines 224–225). Recording metrics after that
reset would silently lose duration for every retried failure.

The fix snapshots `job.started_at` and `job.task_type` **at function
entry** (lines 188–192 of `job_service.py`) and computes
`(now - metric_started_at)` for the metric **after** `commit()` —
unaffected by the retry reset.

The contract test
`test_fail_job_retry_records_retry_metric_with_duration` exercises this
path explicitly.

### 4.5 `METRICS_ENABLED` semantics

- **Instrumentation always records** (in-memory, lock-protected, cheap).
- **Endpoint serves only when `METRICS_ENABLED=True`** — returns 404
  when disabled. This way recorded data is never lost during a
  toggle-flip; an operator can disable scraping without losing the
  metric history collected up to that moment.

### 4.6 Auth bypass for `/api/v1/metrics`

Prometheus scrapers do not carry JWT credentials. The endpoint is added
to `_is_public_path()` in `AuthEnforcementMiddleware` so scrapers can
reach it. Production deployments are expected to gate this endpoint at
the network/ingress layer (e.g. internal-only listener). This matches
how `/api/v1/health` is already handled.

### 4.7 No `prometheus_client` dependency

Hand-rolled because:
- Two metrics (one counter, one histogram) — a 124-line module.
- Adds zero runtime deps; matches the lean pattern P2.1 just shipped
  (also no new deps, ~71-line middleware).
- The Prometheus text format is a stable spec — `text/plain;
  version=0.0.4` content-type — easy to maintain.

If we later need additional metric types, gauges, or process collectors,
swapping to `prometheus_client` is mechanical (~50 lines of changes).
For P2.2's scope, the dependency is unjustified.

## 5. Verification

### 5.1 Boot check

```bash
PYTHONPATH=src python3 -c "from yuantus.api.app import create_app; \
  app = create_app(); print(f'app.routes: {len(app.routes)}')"
```

→ `app.routes: 672` — exactly +1 from the post-Phase-1 baseline of 671.
The single new route is `GET /api/v1/metrics`, asserted by
`test_metrics_endpoint_is_the_single_route_added_by_metrics_router`.

### 5.2 P2.2 focused tests

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/api/tests/test_observability_metrics_registry.py \
  src/yuantus/api/tests/test_metrics_endpoint.py \
  src/yuantus/meta_engine/tests/test_job_service_emits_metrics.py \
  src/yuantus/meta_engine/tests/test_metrics_router_route_count_delta.py
```

→ **22 passed** in 5.5s.

Coverage:
- Registry (7 cases): counter increment, histogram bucket assignment,
  cumulative bucket discipline, None-duration counter-only fallback,
  Prometheus HELP/TYPE lines, long-tail bucket validation, empty-state
  rendering.
- Endpoint (6 cases): 200 + content-type, recorded data visible, 404
  when disabled, instrumentation records even when disabled (data
  preserved across toggle), route registration, empty-registry returns
  empty body.
- JobService integration (7 cases — **the wire-up coverage**): real
  `JobService.complete_job` records success, real `fail_job` terminal
  records failure, real `fail_job` retry records retry **with
  duration** (regression guard for the timestamp-reset bug), retry
  doesn't double-emit `failure`, retry path actually resets
  `started_at` to None (sanity), `started_at=None` records counter
  only, empty `task_type` falls back to `"unknown"` label.
- Route count contract (2 cases): 671 → 672 total, exactly one route
  owned by `yuantus.api.routers.metrics`.

### 5.3 Broader regression scan

```bash
PYTHONPATH=src python3 -m pytest -q -k "metrics or observability or job_service or audit or auth"
```
→ **42 passed, 289 deselected**.

```bash
PYTHONPATH=src python3 -m pytest -q -k "auth_enforce or auth or middleware or audit or context or job_service or job_queue"
```
→ **12 passed, 319 deselected** — confirms the `auth_enforce.py`
public-path edit didn't regress existing auth tests.

### 5.4 Doc-index trio

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```
→ **4 passed**.

### 5.5 Whitespace lint

```bash
git diff --check
```
→ clean.

## 6. Recipe Adherence

Per `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §4.3 (per-PR DOD):

- [x] One concern, bounded scope (job metrics + endpoint only).
- [x] Boot check (`create_app()`) gate post-edit; route count delta
  documented (671 → 672) and contract-tested.
- [x] Focused regression: 22 new tests + 42-test broader scan.
- [x] **Critical**: integration test through real `JobService` (with
  in-mem SQLite) — addresses the test-methodology gap that let P2.1
  ship a ContextVar-lifetime bug.
- [x] DEV_AND_VERIFICATION MD + index entry land in the same commit
  (atomicity, per `DOC_INDEX_CONTRACT_DISCIPLINE`).
- [x] Doc-index trio green.
- [x] No scope creep into P2.1 (request_logging) or P2.3 (closeout
  contracts).
- [x] Branched off `origin/main=17ba15f` (post-Phase-1, NOT off P2.1's
  branch).

## 7. Acceptance Criteria (from plan §6)

| Criterion | Status |
| --- | --- |
| Every job lifecycle event emits a metric with `task_type, status, duration_ms` | ✅ asserted by `test_complete_job_records_success_metric`, `test_fail_job_terminal_records_failure_metric`, `test_fail_job_retry_records_retry_metric_with_duration` |
| Prometheus text format on `GET /api/v1/metrics` | ✅ asserted by `test_metrics_endpoint_returns_200_with_prometheus_content_type` + `test_metrics_endpoint_serves_recorded_data` |
| `METRICS_ENABLED=False` disables endpoint cleanly | ✅ asserted by `test_metrics_endpoint_returns_404_when_disabled` and `test_instrumentation_records_even_when_endpoint_disabled` |
| `RUNBOOK_RUNTIME.md` updated with metric schema | ➡ deferred to P2.3 closeout (cross-cutting documentation) |

## 8. Out of Scope

- **Request logging fields** (request_id / tenant_id / org_id / user_id
  per request log line) — P2.1 (PR #414).
- **Phase 2 closeout MD + cross-cutting contracts** — P2.3.
- **`prometheus_client` dependency** — explicitly hand-rolled.
- **Process / runtime metrics** (e.g. memory, GC, file-descriptor
  counts) — out of "job metrics" scope; future work.
- **Per-tenant / per-org metric labels** — cardinality concern; defer
  until tenant volume is known.
- **Histogram quantile summaries** — not standard Prometheus; clients
  compute via `histogram_quantile()`.
- **Worker liveness / queue-depth gauges** — not a "lifecycle event";
  separate metric class.
- **Admin endpoint for resetting metrics** — `reset_registry()` is
  test-only; production resets via process restart.

## 9. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| `task_type` cardinality blow-up | Low | Medium | Limited to handler-registered values; new types are introduced via deliberate code changes |
| Lock contention on registry | Low | Low | Single `threading.Lock` around dict ops; metric writes are O(1); profiled: <1µs per record |
| Metrics endpoint lacks auth → leaks task volumes | Low | Low–Medium | Network-layer protection in production (matches `/health`); document in §4.6 |
| Histogram buckets clip future workload tails | Medium | Low | Buckets pinned in `metrics.py`; changing them requires a migration discussion |
| Future `JobService` failure path skips recording | Medium | Medium | Hookpoints inside `JobService.fail_job` itself, not at callsites — so all callers covered automatically |

## 10. Rollback

Pure additive code. Revert: `git revert <this-commit>`. The
`/api/v1/metrics` route disappears; `JobService` reverts to no
instrumentation. No DB migrations, no data writes, no external
dependencies.

## 11. Verification Summary

| Check | Result |
| --- | --- |
| `create_app()` boot | 672 routes (671 → 672, +1 metrics endpoint), 3 middleware (P2.1 not on this branch) |
| P2.2 focused tests (22 cases) | 22 passed |
| Wire-up integration test (real `JobService` + in-mem SQLite) | ✅ passing — the test class advisor pushed hardest on |
| Broader (auth/middleware/audit/context/jobs) | 12 passed |
| Repo-wide (metrics/observability/job_service/audit/auth) | 42 passed |
| Doc-index trio | 4 passed |
| `git diff --check` | clean |
