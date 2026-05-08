# Dev & Verification — Phase 6 P6.2 Circuit Breaker (CAD ML Platform)

Date: 2026-05-08

## 1. Summary

Phase 6 P6.2 lands a circuit breaker for the CAD ML Platform integration
client. **Default-off** per the Phase 6 mitigation principle. When
enabled via `YUANTUS_CIRCUIT_BREAKER_CAD_ML_ENABLED`, repeated outbound
failures within a rolling window short-circuit subsequent calls until a
half-open trial validates that the upstream has recovered.

This PR reuses the `CircuitBreaker` primitive shipped in P6.1
(`src/yuantus/integrations/circuit_breaker.py`) — no changes to the
shared module. The wiring follows the same pattern as P6.1
(`src/yuantus/integrations/dedup_vision.py`):

- Settings: 6 new `YUANTUS_CIRCUIT_BREAKER_CAD_ML_*` env vars.
- `CadMLClient.health` / `vision_analyze_sync` / `ocr_extract_sync` /
  `render_cad_preview_sync` route through the breaker; original logic
  preserved in `_*_inner` methods.
- Failure classification mirrors P6.1's policy
  (`is_cad_ml_breaker_failure`): network errors / 5xx / 408 / 429 count;
  4xx and `OSError` do not.
- `/api/v1/metrics` cold-scrape pre-registers the cad_ml breaker so the
  `yuantus_circuit_breaker_*{name="cad_ml"}` families are visible
  regardless of scrape order.
- `/api/v1/health/deps` exposes a `breaker` block under
  `external.cad_ml`.

Incidental hygiene fix: `cad_ml.py` was using `os.path.basename` without
importing `os`, a latent `NameError` on the `filename=None` path. Added
`import os` since the file is being edited anyway.

## 2. Files Changed

### Code

- `src/yuantus/integrations/cad_ml.py` — adds `is_cad_ml_breaker_failure`,
  `build_cad_ml_breaker`, breaker wrap on the four public methods, and
  the missing `import os`.
- `src/yuantus/config/settings.py` — 6 new `CIRCUIT_BREAKER_CAD_ML_*`
  fields (all default off / status-quo thresholds).
- `src/yuantus/observability/metrics.py` — `render_runtime_prometheus_text`
  pre-registers the cad_ml breaker alongside dedup_vision so cold scrape
  emits `name="cad_ml"` metrics.
- `src/yuantus/api/routers/health.py` — `/health/deps` annotates the
  `cad_ml` external entry with a `breaker` block.

### Tests

- `src/yuantus/integrations/tests/test_cad_ml_circuit_breaker.py` —
  10 integration tests (default-off pass-through, threshold opens,
  shared-breaker across the three sync paths, 4xx don't trip, 5xx do,
  408/429 do, missing-file paths don't open, idempotent build).
- `src/yuantus/api/tests/test_circuit_breaker_cad_ml_contracts.py` —
  7 contract tests (settings + default-off, metric families,
  cold-start metric visibility, `/health/deps` shape, failure
  classification policy, well-formed metric lines).

### Docs

- `docs/DEV_AND_VERIFICATION_CIRCUIT_BREAKER_CAD_ML_20260508.md`
  (this file).
- `docs/RUNBOOK_JOBS_DIAG.md` — adds §7 "CAD ML Platform 断路器"
  paralleling §6 (DedupCAD Vision).
- `docs/DELIVERY_DOC_INDEX.md` — single new entry for this MD,
  alphabetically positioned per the doc-index sort contract.

## 3. Design

P6.2 is intentionally a copy-with-renames of the P6.1 wiring; the
shared `CircuitBreaker` primitive is unchanged and now hosts two
named breakers (`dedup_vision`, `cad_ml`) in the process-wide registry.

### 3.1 Failure classification (P6.2 policy)

Identical to P6.1; pinned by the contract test
`test_failure_classification_pins_breaker_policy`:

| Exception | Counted? | Rationale |
| --- | --- | --- |
| `httpx.RequestError` (any subclass) | ✅ | Transport failure — upstream unreachable. |
| `httpx.HTTPStatusError` 5xx | ✅ | Server-side failure. |
| `httpx.HTTPStatusError` 408 / 429 | ✅ | Recoverable upstream pressure. |
| `httpx.HTTPStatusError` other 4xx | ❌ | Client-side error (validation, auth) — upstream healthy. |
| `OSError` and subclasses | ❌ | Local-side I/O failure (missing/unreadable file). |
| Anything else | ✅ (defensive) | Avoid silently letting outages slip through. |

### 3.2 Cold-start metrics

`render_runtime_prometheus_text()` now warms up two breakers:

```python
build_dedup_vision_breaker()
build_cad_ml_breaker()
```

This guarantees `yuantus_circuit_breaker_*{name="cad_ml"}` is emitted
on a cold scrape — the same regression that #500 fixed for dedup-vision
applies symmetrically here.

### 3.3 Health endpoint

`/api/v1/health/deps` already enumerated all 5 external services;
P6.2 extends the `breaker_field_map` to include `cad_ml`. The block has
the identical shape as `external.dedup_vision.breaker` so ops tooling
that already consumes the dedup-vision form works unchanged for cad_ml.

## 4. Settings

`Settings` declares `env_prefix="YUANTUS_"`; use the env var form
(right column) to toggle on a deployment.

| Settings field | Env var (production) | Default | Notes |
| --- | --- | --- | --- |
| `CIRCUIT_BREAKER_CAD_ML_ENABLED` | `YUANTUS_CIRCUIT_BREAKER_CAD_ML_ENABLED` | `false` | Default-off invariant. |
| `CIRCUIT_BREAKER_CAD_ML_FAILURE_THRESHOLD` | `YUANTUS_CIRCUIT_BREAKER_CAD_ML_FAILURE_THRESHOLD` | `5` | Failures within window before opening. |
| `CIRCUIT_BREAKER_CAD_ML_WINDOW_SECONDS` | `YUANTUS_CIRCUIT_BREAKER_CAD_ML_WINDOW_SECONDS` | `60` | Rolling failure window. |
| `CIRCUIT_BREAKER_CAD_ML_RECOVERY_SECONDS` | `YUANTUS_CIRCUIT_BREAKER_CAD_ML_RECOVERY_SECONDS` | `30` | Base open→half-open delay. |
| `CIRCUIT_BREAKER_CAD_ML_HALF_OPEN_MAX_CALLS` | `YUANTUS_CIRCUIT_BREAKER_CAD_ML_HALF_OPEN_MAX_CALLS` | `1` | Concurrent trial calls in half-open. |
| `CIRCUIT_BREAKER_CAD_ML_BACKOFF_MAX_SECONDS` | `YUANTUS_CIRCUIT_BREAKER_CAD_ML_BACKOFF_MAX_SECONDS` | `600` | Cap for exponential backoff. |

## 5. Acceptance Criteria (from `DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §10)

| Criterion | Status |
| --- | --- |
| External-service outages don't cascade to job-retry storms | Met for cad-ml when flag enabled. |
| Circuit-breaker state visible via metrics and `/api/v1/health/deps` | Met. `external.cad_ml.breaker` JSON; `yuantus_circuit_breaker_*{name="cad_ml"}` Prometheus families on every scrape (including cold). |
| Documented thresholds in `RUNBOOK_JOBS_DIAG.md` | Met (§7 in the runbook). |

## 6. Verification

### 6.1 Focused regression (this PR)

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/integrations/tests/test_cad_ml_circuit_breaker.py \
  src/yuantus/api/tests/test_circuit_breaker_cad_ml_contracts.py
```

Expected: **17 passed** (10 integration + 7 contract).

### 6.2 Adjacent regression (P6.1 must not regress)

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/integrations/tests/test_circuit_breaker.py \
  src/yuantus/integrations/tests/test_dedup_vision_circuit_breaker.py \
  src/yuantus/api/tests/test_circuit_breaker_dedup_vision_contracts.py \
  src/yuantus/integrations/tests/test_contract_schemas.py \
  src/yuantus/api/tests/test_metrics_endpoint.py \
  src/yuantus/api/tests/test_observability_metrics_registry.py \
  src/yuantus/api/tests/test_phase2_observability_closeout_contracts.py \
  src/yuantus/api/tests/test_integrations_router_security.py \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py
```

Expected: passes (P6.1 surface untouched).

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

## 7. Rollout Plan

P6.3 (Athena) is the next mirror. Recipe:

1. `git checkout -b feat/circuit-breaker-athena-2026MMDD origin/main`.
2. Copy `cad_ml.py` breaker scaffolding (factory, `is_*_breaker_failure`,
   `*_BREAKER_NAME`) into `athena.py`; rename `cad_ml` → `athena`.
3. Wrap `AthenaClient` public call methods.
4. Settings: 6 `CIRCUIT_BREAKER_ATHENA_*` fields.
5. `metrics.py`: pre-register `build_athena_breaker()` in
   `render_runtime_prometheus_text`.
6. `health.py`: add `"athena": "athena"` to `breaker_field_map`.
7. Tests: clone P6.2 tests with renames.
8. RUNBOOK §8 + new dev/verification MD; doc-index entry.

P6.4 closeout consolidates the three breakers into a portfolio contract
asserting all three are pre-registered, all share the same metric label
set, and the runbook §6/§7/§8 thresholds are pinned.

## 8. Risks & Mitigations

Same risk register as P6.1; the breaker primitive itself isn't being
modified, so no new risks beyond "wiring drift between dedup_vision and
cad_ml". Mitigated by:

- Identical contract test structure (same metric families, same
  `_PINNED_SETTING_DEFAULTS` shape) makes structural drift visible.
- Failure classification is its own pinned table per breaker so any
  policy divergence (e.g. someone deciding cad_ml needs different 4xx
  semantics) is intentional and reviewable.

## 9. Non-Goals (this PR)

- Wiring `Athena` client (P6.3 / separate PR).
- Phase 6 portfolio contract (P6.4 / separate PR).
- Per-tenant or per-route breaker scoping (out of scope; service-level only).
- Auto-enablement based on observed flakiness (D1 trigger-gated).
- Migrating other 4 integration clients (`cad_extractor`, `cad_connector`,
  `cadgf_router`) — they are out of Phase 6 scope per the plan.

## 10. References

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §10 (Phase 6).
- `docs/DEV_AND_VERIFICATION_CIRCUIT_BREAKER_DEDUP_VISION_20260507.md`
  (P6.1 — the pattern this PR mirrors).
- `docs/RUNBOOK_JOBS_DIAG.md` (updated §7 alongside this PR).
