# Dev & Verification — Phase 6 P6.1 Circuit Breaker (DedupCAD Vision)

Date: 2026-05-07

## 1. Summary

Phase 6 P6.1 lands a circuit breaker for the DedupCAD Vision integration
client. The breaker is **default-off** per the Phase 6 mitigation principle
("status-quo behavior; enable per service after acceptance"). When enabled
via the `CIRCUIT_BREAKER_DEDUP_VISION_ENABLED` flag, repeated outbound
failures within a rolling window short-circuit subsequent calls until a
half-open trial validates that the upstream has recovered.

This PR is intentionally bounded:

- Adds the generic `CircuitBreaker` primitive that P6.2 (`cad-ml`) and
  P6.3 (`Athena`) will reuse.
- Wires it into `DedupVisionClient.health` / `search_sync` / `index_add_sync`.
- Surfaces breaker state via `/api/v1/health/deps` and the existing
  `/api/v1/metrics` endpoint.
- Pins the settings + metric + health surface with a contract test so
  P6.4 (Phase 6 closeout) can extend, not redefine.

Non-goals (deferred to P6.2–P6.4):
- Wiring `cad-ml` and `Athena` clients (each 0.5 day, separate PRs).
- `RUNBOOK_JOBS_DIAG.md` cross-service consolidation table (lands in P6.4).
- Production enablement plan (D1 trigger-gated).

## 2. Files Changed

### Code

- `src/yuantus/integrations/circuit_breaker.py` — new generic breaker module
  + process-wide registry.
- `src/yuantus/integrations/dedup_vision.py` — wraps each public call with
  the breaker; exposes `build_dedup_vision_breaker()` for surfaces that need
  to pre-register the instance.
- `src/yuantus/config/settings.py` — adds 6 `CIRCUIT_BREAKER_DEDUP_VISION_*`
  fields (all default-off / status-quo thresholds).
- `src/yuantus/observability/metrics.py` — new
  `render_circuit_breaker_metrics(...)` rendering, wired into
  `render_runtime_prometheus_text()`.
- `src/yuantus/api/routers/health.py` — `/health/deps` annotates the
  `dedup_vision` external entry with a `breaker` block sourced from the
  breaker registry.

### Tests

- `src/yuantus/integrations/tests/test_circuit_breaker.py` — 9 unit tests
  covering closed → open → half-open → closed/reopen, exponential backoff
  cap, async path, registry idempotency, status key contract.
- `src/yuantus/integrations/tests/test_dedup_vision_circuit_breaker.py` —
  5 tests covering default-off pass-through, threshold opens, sync paths
  (`index_add_sync`), public name + idempotent build helper.
- `src/yuantus/api/tests/test_circuit_breaker_dedup_vision_contracts.py` —
  7 contract tests pinning the settings keys, default-off invariant,
  metric families/labels, runtime Prometheus inclusion, `/health/deps`
  shape, and metric line well-formedness.

### Docs

- `docs/DEV_AND_VERIFICATION_CIRCUIT_BREAKER_DEDUP_VISION_20260507.md`
  (this file).
- `docs/RUNBOOK_JOBS_DIAG.md` — adds a "DedupCAD Vision circuit breaker"
  section under runtime diagnostics with thresholds + ops procedure.
- `docs/DELIVERY_DOC_INDEX.md` — single new entry for this MD, sorted
  alphabetically per the doc-index atomicity rule.

## 3. Design

### 3.1 State machine

```
            failures >= threshold within window
   closed ─────────────────────────────────────► open
     ▲                                              │
     │                                              │ elapsed >= recovery_seconds
     │ success                                      ▼
   closed ◄────────── half_open  ◄─────────────── half_open
                        │
                        │ failure
                        ▼
                       open  (recovery_seconds *= 2, capped)
```

Recovery window doubles on each consecutive open cycle (1×, 2×, 4×, …)
up to `backoff_max_seconds`. A successful close resets the cycle counter,
so a brief flap does not leave a long backoff in place.

### 3.2 Thread / async safety

`CircuitBreaker` holds a single `threading.Lock`. `call_sync` and
`call_async` both go through the same `_before_call` / `_after_*`
state-transition helpers, so concurrency on either path is safe. The
in-flight count for half-open trials is bounded by
`half_open_max_calls` (default 1).

### 3.3 Registry

`get_or_create_breaker(config)` returns a process-shared instance keyed by
`config.name`. Configuration changes during a process lifetime do not
re-create the breaker; the codebase explicitly calls
`build_dedup_vision_breaker()` from two warm-up sites:

- `render_runtime_prometheus_text()` — guarantees a Prometheus cold-scrape
  of `/api/v1/metrics` emits the `yuantus_circuit_breaker_*` families even
  before any client call or health probe has occurred in this process.
  Without this, scrape order would silently hide the metrics.
- `/api/v1/health/deps` — same guarantee for the JSON `breaker` block.

### 3.4 Exception handling

The breaker catches `Exception` for failure accounting (transport errors,
upstream HTTP errors, etc. count toward the failure window). It catches
`BaseException` separately for `_after_interrupt`, which **only** releases
the half-open in-flight slot without counting a failure or transitioning
state. This keeps process-level interrupts —
`KeyboardInterrupt` / `SystemExit` / `asyncio.CancelledError` — from
implicating the upstream service when in fact only the local process is
exiting or cancelling. The half-open slot release is essential: without it,
a single interrupt during a half-open trial would lock subsequent recovery
attempts out indefinitely.

#### 3.4.1 Failure classification (Phase 6 P6.1 policy)

Phase 6's stated goal is **service-side outage protection**, not generic
exception accounting. Naïvely counting every `Exception` would let
client-side errors (HTTP 400 from a bad payload, 401/403 from an expired
token, 404/422 validation failures) trip protection meant for upstream
outages — and a flood of 4xx from a misbehaving caller would short-circuit
**healthy** upstream traffic for everyone.

`CircuitBreakerConfig.is_failure` is an optional predicate per-breaker.
When provided (P6.1 always provides one), only exceptions for which it
returns `True` count; other exceptions are released as if they were
process-level interrupts (re-raised, in-flight slot freed, no state
change, no failure counter increment).

The DedupVision breaker uses `is_dedup_vision_breaker_failure`:

| Exception | Counted? | Rationale |
| --- | --- | --- |
| `httpx.RequestError` (any subclass: `ConnectError`, `ReadTimeout`, `WriteError`, …) | ✅ Yes | Transport failure — upstream unreachable. |
| `httpx.HTTPStatusError` 5xx (500/502/503/504/…) | ✅ Yes | Server-side failure. |
| `httpx.HTTPStatusError` 408 / 429 | ✅ Yes | Recoverable upstream pressure (timeout, rate limit). |
| `httpx.HTTPStatusError` other 4xx (400/401/403/404/409/422/…) | ❌ No | Client-side error; upstream is healthy. |
| `OSError` and subclasses (`FileNotFoundError`, `PermissionError`, `IsADirectoryError`, …) | ❌ No | Local file-system failure (e.g. caller passes a missing/unreadable path). httpx exceptions are not `OSError` subclasses, so this branch only matches genuine local I/O. |
| Anything else | ✅ Yes (defensive) | Fall back to counting so true outages don't slip through. |

Predicate failures (a buggy `is_failure` that itself raises) fall back to
counting the original exception — same defensive principle.

### 3.5 Default-off contract

The `CIRCUIT_BREAKER_DEDUP_VISION_ENABLED` flag defaults to `False`. When
disabled, `CircuitBreaker.call_sync` / `call_async` is a thin pass-through
that does not record metrics, so behaviour is byte-for-byte identical to
the pre-P6.1 client.

### 3.6 Observability surface

Metrics (Prometheus text):

| Metric | Type | Labels |
| --- | --- | --- |
| `yuantus_circuit_breaker_enabled` | gauge | `name` |
| `yuantus_circuit_breaker_state` | gauge | `name`, `state` ∈ {closed,open,half_open} |
| `yuantus_circuit_breaker_opens_total` | counter | `name` |
| `yuantus_circuit_breaker_short_circuited_total` | counter | `name` |
| `yuantus_circuit_breaker_failures_total` | counter | `name` |
| `yuantus_circuit_breaker_successes_total` | counter | `name` |
| `yuantus_circuit_breaker_failures_in_window` | gauge | `name` |

Label cardinality is bounded by the number of registered breakers (one
per integration), keeping Prometheus storage cost negligible.

`GET /api/v1/health/deps` adds a `breaker` block under
`external.dedup_vision` mirroring `CircuitBreaker.status()`. Ops can read
the JSON without scraping metrics.

## 4. Settings

| Field | Default | Notes |
| --- | --- | --- |
| `CIRCUIT_BREAKER_DEDUP_VISION_ENABLED` | `false` | Default-off invariant. Production enablement is per-deployment via env override. |
| `CIRCUIT_BREAKER_DEDUP_VISION_FAILURE_THRESHOLD` | `5` | Failures within window before opening. |
| `CIRCUIT_BREAKER_DEDUP_VISION_WINDOW_SECONDS` | `60` | Rolling failure window. |
| `CIRCUIT_BREAKER_DEDUP_VISION_RECOVERY_SECONDS` | `30` | Base open→half-open delay. |
| `CIRCUIT_BREAKER_DEDUP_VISION_HALF_OPEN_MAX_CALLS` | `1` | Concurrent trial calls in half-open. |
| `CIRCUIT_BREAKER_DEDUP_VISION_BACKOFF_MAX_SECONDS` | `600` | Cap for exponential backoff. |

## 5. Acceptance Criteria (from `DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §10)

| Criterion | Status |
| --- | --- |
| External-service outages don't cascade to job-retry storms | Met for dedup-vision when flag enabled; consumers receive `CircuitOpenError` immediately during `open` state. |
| Circuit-breaker state visible via metrics and `GET /api/v1/health/dependencies` | Met. `/health/deps` returns `external.dedup_vision.breaker`; metrics endpoint emits 7 `yuantus_circuit_breaker_*` families. |
| Documented thresholds in `RUNBOOK_JOBS_DIAG.md` | Met (§4 of this MD lists thresholds; runbook adds the ops procedure). |

> **Endpoint naming note**: the plan's wording `/api/v1/health/dependencies`
> is interpreted as the existing `/api/v1/health/deps` route. Renaming a
> stable health-check route to match an illustrative spec phrase would
> break downstream consumers and is out of scope for P6.1. The contract
> test asserts presence of the `breaker` block under `external.dedup_vision`
> regardless of route name.

## 6. Verification

### 6.1 Focused regression (this PR)

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/integrations/tests/test_circuit_breaker.py \
  src/yuantus/integrations/tests/test_dedup_vision_circuit_breaker.py \
  src/yuantus/api/tests/test_circuit_breaker_dedup_vision_contracts.py
```

Expected: **36 passed** (16 unit + 12 integration + 8 contract).

### 6.2 Adjacent regression (no behaviour change expected)

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/integrations/tests/test_contract_schemas.py \
  src/yuantus/api/tests/test_metrics_endpoint.py \
  src/yuantus/api/tests/test_observability_metrics_registry.py \
  src/yuantus/api/tests/test_phase2_observability_closeout_contracts.py \
  src/yuantus/api/tests/test_integrations_router_security.py
```

Expected: **29 passed** (status-quo for default-off flag).

### 6.3 Doc-index trio

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Expected: passes.

### 6.4 App boot

```bash
.venv/bin/python -c "from yuantus.api.app import create_app; create_app()"
```

Expected: no `ModuleNotFoundError` or registration loss.

### 6.5 Pact provider verification

```bash
.venv/bin/python -m pytest -q src/yuantus/api/tests/test_pact_provider_yuantus_plm.py
```

Expected: passes.

> **Pact scope note**: the local consumer pact
> (`contracts/pacts/metasheet2-yuantus-plm.json`) covers `/api/v1/health`
> but **not** `/api/v1/health/deps`. The shape change in this PR
> (added `external.dedup_vision.breaker`) therefore does not touch any
> Pact-registered interaction. The contract test
> `test_health_deps_surfaces_dedup_vision_breaker_block` is the
> authoritative regression-prevention guard for the `/health/deps`
> shape; downstream consumers that integrate with `/health/deps` should
> consider upgrading to a Pact contract in a future cycle.

## 7. Rollout Plan (for downstream PRs)

1. **P6.2** — reuse `circuit_breaker.py` for `CadMLClient`. Mirror this
   PR's settings/metrics/health pattern, just renaming
   `dedup_vision` → `cad_ml`. Should be a copy-paste-with-renames.
2. **P6.3** — same for `AthenaClient`. Athena's `_resolve_authorization`
   path differs but the breaker integration point is identical.
3. **P6.4** — Phase 6 closeout MD: produce a cross-service summary,
   refresh `RUNBOOK_JOBS_DIAG.md` §"DedupCAD Vision circuit breaker" into
   a generalised "Circuit Breakers" section, add a portfolio contract
   test asserting all three breakers register.

## 8. Risks & Mitigations

| Risk | Mitigation |
| --- | --- |
| Default-off accidentally flipped on in CI/dev | Contract test `test_default_breaker_is_disabled` asserts the default; flips would fail review. |
| Half-open trial flood when `half_open_max_calls > 1` | Default is 1; `_before_call` guards against exceeding the limit and increments `short_circuited_total`. |
| Long backoff stuck after a single transient flap | `consecutive_open_cycles` resets on closed; backoff goes back to base after one clean cycle. |
| Settings drift across breaker instances | All thresholds sourced from `get_settings()`; `build_dedup_vision_breaker()` is idempotent and shared. |

## 9. Non-Goals (this PR)

- Wiring `cad-ml` or `Athena` clients (P6.2 / P6.3).
- Per-tenant or per-route breaker scoping (out of scope; service-level only).
- Auto-enablement based on observed flakiness (D1 trigger-gated).
- Migrating existing 5 integration clients to a `BaseIntegrationClient`
  (§二.2 of the older gap doc; not part of the official next-cycle plan).

## 10. References

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §10 (Phase 6).
- `docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260420.md` §二.3.1 (event/outbox)
  and §二 (resilience) — context only; this PR does not address outbox.
- `docs/RUNBOOK_JOBS_DIAG.md` (updated alongside this PR).
