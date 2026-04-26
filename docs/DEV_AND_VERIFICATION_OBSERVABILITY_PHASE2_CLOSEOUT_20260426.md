# DEV / Verification — Phase 2 P2.3 Observability Closeout (2026-04-26)

## 1. Goal

Close out **Phase 2 — Observability Foundation** of the next-cycle plan
(`docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §6) by:

1. Pinning the *downstream-consumer* surface (log field set, metric
   names, label cardinality, histogram boundaries, middleware order)
   that external tools (log indexers, Prometheus dashboards, alert
   rules) depend on — via 6 cross-cutting contract tests.
2. Documenting the field/metric schema in `docs/RUNBOOK_RUNTIME.md` so
   on-call and integration engineers have a single canonical reference.
3. Aggregating Phase 2 verification (P2.1 #414 + P2.2 #415 + P2.3 this
   PR) into one closeout record.

## 2. Strict P2.3 boundary

Per-phase opt-in confirmed by user (2026-04-26): "仅做收口 MD、
runbook/contract 补强、doc-index 和验证，不新增 runtime feature".

✅ in this PR:
- Cross-cutting contract tests (regression-prevention only — every test
  here would have failed against pre-P2.1 / pre-P2.2 code, so each is
  guarding existing behavior, not adding new behavior)
- `RUNBOOK_RUNTIME.md` "Observability" section (field schema, metric
  schema, settings, middleware order — was deferred from P2.1 + P2.2
  closeout MDs as cross-cutting documentation)
- Phase 2 closeout MD (this file)
- Doc-index entry

❌ explicitly out of scope:
- No new middleware
- No new metrics / new metric labels
- No new endpoints
- No new settings
- No `JobService` / `RequestLoggingMiddleware` behavior changes
- No `prometheus_client` dependency (still hand-rolled per P2.2)

## 3. Files Changed

| File | Change | Lines |
| --- | --- | ---: |
| `src/yuantus/api/tests/test_phase2_observability_closeout_contracts.py` | New: 6 cross-cutting closeout contracts | +175 |
| `docs/RUNBOOK_RUNTIME.md` | New "Observability" section (field/metric/settings/middleware-order schema) | +103 |
| `docs/DEV_AND_VERIFICATION_OBSERVABILITY_PHASE2_CLOSEOUT_20260426.md` | This MD | +245 |
| `docs/DELIVERY_DOC_INDEX.md` | Index entry | +1 |

Total: 4 files, ~524 lines, **zero runtime-code changes**.

## 4. Contract Design

### 4.1 What's new vs. redundant with P2.1 / P2.2

P2.1 and P2.2 already have implementation-level contracts (field set,
route count, middleware presence). P2.3 contracts pin the
*downstream-consumer* contract — names, label sets, ordering — that
external tools depend on. No duplication.

| # | Contract | What breaks it |
| --- | --- | --- |
| 1 | `test_real_middleware_chain_log_line_carries_tenant_org_from_headers` | A future `TenantOrgContextMiddleware` refactor that drops the `request.state.tenant_id` snapshot |
| 2 | `test_metric_names_are_pinned_to_phase2_contract` | Renaming `yuantus_jobs_total` or `yuantus_job_duration_ms` |
| 3 | `test_metric_label_set_excludes_high_cardinality_dimensions` | Adding `tenant_id` / `user_id` / `job_id` labels to the metric |
| 4 | `test_histogram_bucket_boundaries_are_pinned` | Changing `_DURATION_BUCKETS_MS` |
| 5 | `test_request_logging_middleware_is_outermost` | Removing or re-positioning `add_middleware(RequestLoggingMiddleware)` |
| 6 | `test_middleware_chain_order_is_pinned` | Reordering `add_middleware` calls |

### 4.2 The load-bearing addition: real-middleware chain test

P2.1's `test_chain_log_carries_tenant_org_user_after_inner_resets_contextvars`
uses a synthetic `_InjectFixedIdentityMiddleware` that *always*
snapshots to `request.state`. If a future refactor of the *real*
`TenantOrgContextMiddleware` drops the snapshot, that synthetic test
still passes — it's testing the contract pattern, not the real
production middleware.

P2.3 adds
`test_real_middleware_chain_log_line_carries_tenant_org_from_headers`
which uses `create_app()` (full middleware stack, real
`TenantOrgContextMiddleware`) + a request with `x-tenant-id` /
`x-org-id` headers in `AUTH_MODE=optional`. The test asserts the
emitted JSON log line carries the header values. A drop of the
`request.state.tenant_id = tenant_id` line in `src/yuantus/api/middleware/context.py` fails this
test.

This is the test that turns "the middleware writes to request.state"
from documented behavior into enforceable contract.

### 4.3 Cardinality contract (label allowlist)

`test_metric_label_set_excludes_high_cardinality_dimensions` parses all
label assignments in the rendered Prometheus output and asserts the set
is a subset of `{task_type, status, le}`. The contract is permissive
about ordering and value ranges but strict about the label *names*
themselves — adding any other label fails the test.

This is critical because: per-tenant labels grow series count
unboundedly (1 tenant × 5 task_types × 3 statuses = 15 series; 10k
tenants → 150k series, breaking Prometheus retention).
Per-tenant observability belongs in the log line, not the metric.

### 4.4 Histogram bucket pinning rationale

P2.2 §4.2 documented the buckets as "do not change without explicit
discussion". P2.3's contract makes that documentation enforceable: a
bucket change is allowed but only via a deliberate update to the
expected list, which surfaces in PR review.

```python
expected = (50, 100, 500, 1000, 5000, 10000, 30000, 60000, 300000)
```

Boundaries:
- `50` ms — fast queue jobs (no I/O)
- `100, 500, 1000` ms — typical CAD metadata extraction
- `5000, 10000` ms — preview generation
- `30000, 60000, 300000` ms — full conversions (long-tail)

### 4.5 Why pin middleware order

The chain
`RequestLogging → AuthEnforcement → TenantOrgContext → AuditLog` is
correctness-load-bearing:

- `RequestLogging` outermost: `request_id` set first; final response
  status (incl. 401s) visible at log emission.
- `AuthEnforcement` before `TenantOrgContext`: authenticated
  tenant/org claims preempt header-based fallbacks (a malicious
  `x-tenant-id` header from a wrong-tenant user is overridden by the
  JWT claim).
- `AuditLog` innermost: sees populated identity context AND the final
  status.

Reordering via `add_middleware` would be a 1-line change but break
several invariants. The contract makes any reorder visible in PR
review.

## 5. RUNBOOK_RUNTIME.md update

New "Observability" section between "Version checkout doc-sync gate
policy knobs" and "Stop services". Documents:

- Per-request log line schema (9 fields, JSON / text wire formats).
- Job lifecycle metrics (counter + histogram, labels, statuses,
  buckets).
- Settings table (4 entries: `LOG_FORMAT`, `REQUEST_ID_HEADER`,
  `METRICS_ENABLED`, `METRICS_BACKEND`).
- Middleware chain order with the rationale for each position.

Cross-references the closeout contract test file by name so future
maintainers find the enforcement points.

## 6. Verification

### 6.1 Boot check (fresh, on `feat/observability-phase2-closeout-20260426` branched off `538a8b9`)

```bash
PYTHONPATH=src python3 -c "from yuantus.api.app import create_app; \
  app = create_app(); print(f'app.routes: {len(app.routes)}'); \
  print(f'middleware count: {len(app.user_middleware)}')"
```
→ `app.routes: 672`, `middleware count: 4`. **Unchanged from post-P2.2 main** (P2.3 adds zero routes / zero middleware).

### 6.2 P2.3 focused contracts

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/api/tests/test_phase2_observability_closeout_contracts.py
```
→ **6 passed** in 3.10s.

### 6.3 Phase 2 aggregate (P2.1 + P2.2 + P2.3)

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/api/tests/test_request_logging_middleware.py \
  src/yuantus/api/tests/test_observability_metrics_registry.py \
  src/yuantus/api/tests/test_metrics_endpoint.py \
  src/yuantus/meta_engine/tests/test_job_service_emits_metrics.py \
  src/yuantus/meta_engine/tests/test_metrics_router_route_count_delta.py \
  src/yuantus/api/tests/test_phase2_observability_closeout_contracts.py
```
→ **39 passed** in 7.05s.

Breakdown:
- P2.1 logging middleware: 11 cases
- P2.2 metrics registry: 7 cases
- P2.2 endpoint: 6 cases
- P2.2 JobService integration (real DB): 7 cases
- P2.2 route-count contract: 2 cases
- P2.3 closeout contracts: 6 cases

### 6.4 Doc-index trio

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```
→ **4 passed**.

### 6.5 Phase 1 portfolio regression

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py
```
→ **5 passed** — Phase 1 invariants intact under Phase 2 closeout.

### 6.6 Whitespace lint

```bash
git diff --check
```
→ clean.

## 7. Recipe Adherence

Per `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §4.4 (per-Phase DOD):

- [x] All sub-PRs of the phase merged: P2.1 #414 (`ff8492d`), P2.2 #415 (`538a8b9`).
- [x] Closeout contracts in place — 6 cross-cutting tests guard the
  downstream-consumer surface.
- [x] Runbook updated (`RUNBOOK_RUNTIME.md` "Observability" section).
- [x] Closeout MD records aggregate verification (this file).
- [x] No runtime-feature additions in the closeout PR.

Per `DOC_INDEX_CONTRACT_DISCIPLINE`:

- [x] DEV_AND_VERIFICATION MD + index entry land in the same commit
  (atomicity).
- [x] Doc-index trio green pre-commit.

Per the explicit user opt-in for P2.3:

- [x] No new runtime feature.
- [x] No P3 / Phase 3 work started.

## 8. Out of Scope

- **`AuthEnforcementMiddleware` snapshot when var was previously not
  None** — `TenantOrgContextMiddleware` only snapshots inside the
  `if ... is None` guard. There's a theoretical edge case where an
  upstream caller has set `tenant_id_var` but not `request.state.tenant_id`;
  in that case the log line would carry `null` for `tenant_id`. In the
  current production middleware chain this can't happen (the only
  upstream var-setter is `AuthEnforcementMiddleware`, which itself
  snapshots). If a future producer breaks this invariant, that's a
  separate PR — not scope creep into P2.3.
- **Phase 3 / Postgres schema-per-tenant** — separate per-phase opt-in.
- **Process / runtime metrics** (memory, GC, fd counts) — not "job
  metrics"; future work.
- **Per-tenant metric labels** — explicitly forbidden by the new
  cardinality contract; tenant correlation belongs in the log line.
- **Sampling / rate limiting of log emit** — current implementation
  logs every request. Sampling is a Phase 6 (observability scaling)
  concern.

## 9. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Closeout contracts ossify a wrong design | Low | Low | Each contract documents what breaks it; deliberate updates are still possible |
| RUNBOOK doc drifts from code | Medium | Low | Schema cross-references the contract test file by name; future PRs that touch schema are reminded by the contract failure to update RUNBOOK |
| Real-middleware chain test fragile to FastAPI/Starlette upgrades | Low | Low | Test uses public Starlette `app.user_middleware` API and standard `TestClient`; upgrade path is well-trodden |

## 10. Rollback

Pure documentation + test-only PR. Revert: `git revert <this-commit>`.
The contracts disappear; no code paths change. RUNBOOK section can be
manually re-added if needed.

## 11. Verification Summary

| Check | Result |
| --- | --- |
| Branch base | `origin/main=538a8b9` |
| `create_app()` boot | 672 routes, 4 middleware (unchanged from post-P2.2) |
| P2.3 closeout contracts (6 cases) | 6 passed |
| Phase 2 aggregate (P2.1 + P2.2 + P2.3, 39 cases) | 39 passed |
| Doc-index trio | 4 passed |
| Phase 1 portfolio regression | 5 passed |
| `git diff --check` | clean |

**Phase 2 status post-this-PR**: 3/3 sub-PRs (P2.1 #414, P2.2 #415, P2.3 this PR) — full closeout. Phase 3 awaits explicit per-phase opt-in.
