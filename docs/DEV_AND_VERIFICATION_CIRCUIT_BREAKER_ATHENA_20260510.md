# Dev & Verification — Phase 6 P6.3 Circuit Breaker (Athena ECM)

Date: 2026-05-10

## 1. Summary

Phase 6 P6.3 lands a circuit breaker for the Athena ECM integration
client, the third and final per-service breaker before the P6.4 Phase 6
closeout. **Default-off** per the Phase 6 mitigation principle.

Reuses the `CircuitBreaker` primitive from P6.1
(`src/yuantus/integrations/circuit_breaker.py`) unchanged. The wiring
mirrors P6.1 (`dedup_vision.py`) and P6.2 (`cad_ml.py`):

- Settings: 6 new `YUANTUS_CIRCUIT_BREAKER_ATHENA_*` env vars.
- `AthenaClient.health` routes through the breaker; original logic
  preserved in `_health_inner`. `health` is the only public outbound
  method on `AthenaClient`, so wrapping it is complete P6.3 coverage.
- Failure classification (`is_athena_breaker_failure`) is identical to
  P6.1/P6.2's policy: network errors / 5xx / 408 / 429 count; 4xx and
  `OSError` do not.
- `/api/v1/metrics` cold-scrape pre-registers the athena breaker.
- `/api/v1/health/deps` exposes a `breaker` block under
  `external.athena`.
- `RUNBOOK_JOBS_DIAG.md` §8 documents the Athena breaker.

### OAuth token-fetch coverage

`AthenaClient.health()` may trigger an OAuth client-credentials token
fetch internally (when no `ATHENA_SERVICE_TOKEN` is configured and
`ATHENA_TOKEN_URL` / `ATHENA_CLIENT_ID` / a resolvable client secret
are present). That token-fetch HTTP call runs **inside** the
breaker-wrapped method, so a flaky OAuth token endpoint counts as
Athena being unreachable. This is intentional: you cannot reach Athena
without auth, so a dead token endpoint is functionally an Athena
outage. The contract test `test_failure_classification_pins_breaker_policy`
and `test_token_fetch_failure_is_covered_through_health` pin this.

`AthenaClient._resolve_client_secret()` already swallows `OSError` from
a missing/unreadable secret file and returns `""`, so the
`OSError`-doesn't-count classification rule is defensive belt-and-braces
for that path rather than load-bearing.

## 2. Files Changed

### Code

- `src/yuantus/integrations/athena.py` — adds `ATHENA_BREAKER_NAME`,
  `is_athena_breaker_failure`, `build_athena_breaker`, breaker init in
  `AthenaClient.__init__`, and `health` → wrapper / `_health_inner`.
- `src/yuantus/config/settings.py` — 6 new `CIRCUIT_BREAKER_ATHENA_*`
  fields (all default off).
- `src/yuantus/observability/metrics.py` — `render_runtime_prometheus_text`
  pre-registers the athena breaker alongside dedup_vision + cad_ml.
- `src/yuantus/api/routers/health.py` — `/health/deps` annotates the
  `athena` external entry with a `breaker` block.

### Tests

- `src/yuantus/integrations/tests/test_athena_circuit_breaker.py` —
  9 integration tests (default-off pass-through, threshold opens on
  RequestError, 5xx / 408 / 429 count, 4xx don't trip, OSError doesn't
  trip, token-fetch failure covered through `health()`, idempotent
  build).
- `src/yuantus/api/tests/test_circuit_breaker_athena_contracts.py` —
  8 contract tests (settings + default-off, metric families, cold-start
  metric visibility, **all-three-breakers pre-registered** invariant,
  `/health/deps` shape, failure classification policy, well-formed
  metric lines).

### Docs

- `docs/DEV_AND_VERIFICATION_CIRCUIT_BREAKER_ATHENA_20260510.md`
  (this file).
- `docs/RUNBOOK_JOBS_DIAG.md` — adds §8 "Athena ECM 断路器".
- `docs/DELIVERY_DOC_INDEX.md` — single new entry, alphabetically
  positioned (before the P6.2 cad-ml entry: `ATHENA` < `CAD_ML`).

## 3. Design

P6.3 is a copy-with-renames of the P6.2 wiring; the shared
`CircuitBreaker` primitive is unchanged and now hosts three named
breakers (`dedup_vision`, `cad_ml`, `athena`) in the process-wide
registry.

### 3.1 Failure classification (P6.3 policy)

Identical to P6.1/P6.2; pinned by
`test_failure_classification_pins_breaker_policy`:

| Exception | Counted? | Rationale |
| --- | --- | --- |
| `httpx.RequestError` (any subclass) | ✅ | Transport failure — Athena or its OAuth endpoint unreachable. |
| `httpx.HTTPStatusError` 5xx | ✅ | Server-side failure. |
| `httpx.HTTPStatusError` 408 / 429 | ✅ | Recoverable upstream pressure. |
| `httpx.HTTPStatusError` other 4xx | ❌ | Client-side error (auth, validation) — upstream healthy. |
| `OSError` and subclasses | ❌ | Local-side I/O (e.g. client-secret file). |
| Anything else | ✅ (defensive) | Avoid silently letting outages slip through. |

### 3.2 Cold-start metrics

`render_runtime_prometheus_text()` now warms up three breakers:

```python
build_dedup_vision_breaker()
build_cad_ml_breaker()
build_athena_breaker()
```

The contract test `test_all_three_breakers_pre_registered_on_cold_scrape`
asserts a cold `/api/v1/metrics` scrape exposes `name="dedup_vision"`,
`name="cad_ml"`, and `name="athena"`. P6.4 will harden this into a
dedicated portfolio contract.

### 3.3 Health endpoint

`/api/v1/health/deps` `breaker_field_map` now lists all three breakers.
The `external.athena.breaker` block has the identical shape as the
dedup-vision and cad-ml forms.

## 4. Settings

`Settings` declares `env_prefix="YUANTUS_"`; use the env var form
(right column) to toggle on a deployment.

| Settings field | Env var (production) | Default | Notes |
| --- | --- | --- | --- |
| `CIRCUIT_BREAKER_ATHENA_ENABLED` | `YUANTUS_CIRCUIT_BREAKER_ATHENA_ENABLED` | `false` | Default-off invariant. |
| `CIRCUIT_BREAKER_ATHENA_FAILURE_THRESHOLD` | `YUANTUS_CIRCUIT_BREAKER_ATHENA_FAILURE_THRESHOLD` | `5` | Failures within window before opening. |
| `CIRCUIT_BREAKER_ATHENA_WINDOW_SECONDS` | `YUANTUS_CIRCUIT_BREAKER_ATHENA_WINDOW_SECONDS` | `60` | Rolling failure window. |
| `CIRCUIT_BREAKER_ATHENA_RECOVERY_SECONDS` | `YUANTUS_CIRCUIT_BREAKER_ATHENA_RECOVERY_SECONDS` | `30` | Base open→half-open delay. |
| `CIRCUIT_BREAKER_ATHENA_HALF_OPEN_MAX_CALLS` | `YUANTUS_CIRCUIT_BREAKER_ATHENA_HALF_OPEN_MAX_CALLS` | `1` | Concurrent trial calls in half-open. |
| `CIRCUIT_BREAKER_ATHENA_BACKOFF_MAX_SECONDS` | `YUANTUS_CIRCUIT_BREAKER_ATHENA_BACKOFF_MAX_SECONDS` | `600` | Cap for exponential backoff. |

## 5. Acceptance Criteria (from `DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §10)

| Criterion | Status |
| --- | --- |
| External-service outages don't cascade to job-retry storms | Met for athena when flag enabled. |
| Circuit-breaker state visible via metrics and `/api/v1/health/deps` | Met. `external.athena.breaker` JSON; `yuantus_circuit_breaker_*{name="athena"}` on every scrape (including cold). |
| Documented thresholds in `RUNBOOK_JOBS_DIAG.md` | Met (§8 in the runbook). |

## 6. Verification

### 6.1 Focused regression (this PR)

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/integrations/tests/test_athena_circuit_breaker.py \
  src/yuantus/api/tests/test_circuit_breaker_athena_contracts.py
```

Expected: **17 passed** (9 integration + 8 contract).

### 6.2 Adjacent regression (P6.1 + P6.2 must not regress)

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/integrations/tests/test_circuit_breaker.py \
  src/yuantus/integrations/tests/test_dedup_vision_circuit_breaker.py \
  src/yuantus/integrations/tests/test_cad_ml_circuit_breaker.py \
  src/yuantus/api/tests/test_circuit_breaker_dedup_vision_contracts.py \
  src/yuantus/api/tests/test_circuit_breaker_cad_ml_contracts.py \
  src/yuantus/api/tests/test_metrics_endpoint.py \
  src/yuantus/api/tests/test_observability_metrics_registry.py \
  src/yuantus/api/tests/test_phase2_observability_closeout_contracts.py \
  src/yuantus/api/tests/test_integrations_router_security.py \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py
```

Expected: passes (P6.1/P6.2 surfaces untouched).

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

## 7. After P6.3 — Phase 6 closeout (P6.4)

Once P6.3 merges and post-merge smoke passes, P6.4 closes Phase 6:

1. Add a portfolio contract test asserting `dedup_vision`, `cad_ml`,
   and `athena` are all pre-registered in cold metrics, all visible in
   `/health/deps`, all share the same `yuantus_circuit_breaker_*` family
   set, and all follow the default-off setting pattern.
2. Phase 6 closeout DEV/verification MD summarising P6.1–P6.3 + the
   post-merge evidence for each.
3. (Optional) Consolidate RUNBOOK §6/§7/§8 into a single "Circuit
   Breakers" section parameterised by service name.

## 8. Risks & Mitigations

The breaker primitive isn't modified, so no new risks beyond "wiring
drift between the three breaker integrations". Mitigated by:

- Identical contract test structure across all three (same metric
  families, same `_PINNED_SETTING_DEFAULTS` shape, same classification
  table) — structural drift fails a test.
- The new `test_all_three_breakers_pre_registered_on_cold_scrape`
  catches a missed pre-registration call in any of the three.

## 9. Non-Goals (this PR)

- Phase 6 portfolio contract / closeout MD (P6.4 / separate PR).
- Per-tenant or per-route breaker scoping (out of scope; service-level only).
- Auto-enablement based on observed flakiness (D1 trigger-gated).
- Wrapping any non-`health` Athena call — `health` is the only public
  outbound method on `AthenaClient`.
- Touching `feat/cad-material-sync-plugin-20260506` or its local commit
  `2d6c600` — separate CAD workstream.
- Starting Phase 3 P3.4 tenant cutover.

## 10. References

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §10 (Phase 6).
- `docs/DEV_AND_VERIFICATION_CIRCUIT_BREAKER_DEDUP_VISION_20260507.md` (P6.1).
- `docs/DEV_AND_VERIFICATION_CIRCUIT_BREAKER_CAD_ML_20260508.md` (P6.2 — the pattern this PR mirrors).
- `docs/RUNBOOK_JOBS_DIAG.md` (updated §8 alongside this PR).
