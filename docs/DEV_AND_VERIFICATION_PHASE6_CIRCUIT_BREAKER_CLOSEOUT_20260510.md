# Dev & Verification — Phase 6 Circuit Breaker Closeout

Date: 2026-05-10

## 1. Summary

Phase 6 is now closed for the three planned outbound integration circuit
breakers:

| Slice | Service | PR | Merge commit | Runtime default |
| --- | --- | --- | --- | --- |
| P6.1 | `dedup_vision` / DedupCAD Vision | #500 | `40a0fd6` | off |
| P6.2 | `cad_ml` / CAD ML Platform | #501 | `f68dc92` | off |
| P6.3 | `athena` / Athena ECM | #502 | `8b123ac` | off |

P6.4 adds no runtime behavior. It closes the portfolio with a single
contract file and this development/verification record. The contract pins
the cross-service invariants that matter to operators:

- All three breakers are configured through six uniform
  `CIRCUIT_BREAKER_<SERVICE>_*` settings.
- All three remain default-off.
- Cold `/api/v1/metrics` scrapes expose all three breakers before any
  client call has happened.
- `/api/v1/health/deps` exposes `external.<service>.breaker` for all
  three services.
- The failure-classification policy is identical across services:
  transport errors, 5xx, 408, 429, and unknown `Exception` subclasses
  count; normal 4xx and local `OSError` subclasses do not.
- RUNBOOK and delivery-index entries cover the completed surface.

## 2. Files Changed

Runtime code: none.

Contract and CI wiring:

- `src/yuantus/meta_engine/tests/test_phase6_circuit_breaker_closeout_contracts.py`
  — new portfolio closeout contract.
- `.github/workflows/ci.yml` — adds the closeout contract to the CI
  `contracts` job.

Docs:

- `docs/DEV_AND_VERIFICATION_PHASE6_CIRCUIT_BREAKER_CLOSEOUT_20260510.md`
  — this closeout record.
- `docs/DELIVERY_DOC_INDEX.md` — one alphabetical index entry.

Operational cleanup:

- Deleted merged remote branch
  `feat/circuit-breaker-athena-20260510`.
- Deleted merged local branch
  `feat/circuit-breaker-athena-20260510`.
- Created closeout branch
  `closeout/phase6-circuit-breaker-closeout-20260510` from
  `origin/main=8b123ac`.

## 3. Contract Design

The P6.1/P6.2/P6.3 service-specific contracts remain the detailed
behavioral guardrails. P6.4 deliberately sits above them and guards the
portfolio shape.

### 3.1 Default-off settings

For each service, the following defaults are pinned:

| Suffix | Default |
| --- | --- |
| `ENABLED` | `false` |
| `FAILURE_THRESHOLD` | `5` |
| `WINDOW_SECONDS` | `60` |
| `RECOVERY_SECONDS` | `30` |
| `HALF_OPEN_MAX_CALLS` | `1` |
| `BACKOFF_MAX_SECONDS` | `600` |

Pinned setting families:

- `CIRCUIT_BREAKER_DEDUP_VISION_*`
- `CIRCUIT_BREAKER_CAD_ML_*`
- `CIRCUIT_BREAKER_ATHENA_*`

The portfolio default-off keys are explicitly:

- `CIRCUIT_BREAKER_DEDUP_VISION_ENABLED`
- `CIRCUIT_BREAKER_CAD_ML_ENABLED`
- `CIRCUIT_BREAKER_ATHENA_ENABLED`

### 3.2 Metrics

`render_runtime_prometheus_text()` must pre-register:

- `build_dedup_vision_breaker()`
- `build_cad_ml_breaker()`
- `build_athena_breaker()`

This keeps cold-scrape behavior stable. A Prometheus scrape that occurs
before any outbound client is constructed still emits the
`yuantus_circuit_breaker_*` families for every Phase 6 service.

Pinned metric families:

- `yuantus_circuit_breaker_enabled`
- `yuantus_circuit_breaker_state`
- `yuantus_circuit_breaker_opens_total`
- `yuantus_circuit_breaker_short_circuited_total`
- `yuantus_circuit_breaker_failures_total`
- `yuantus_circuit_breaker_successes_total`
- `yuantus_circuit_breaker_failures_in_window`

### 3.3 Health endpoint

`/api/v1/health/deps` must include:

- `external.dedup_vision.breaker`
- `external.cad_ml.breaker`
- `external.athena.breaker`

The closeout contract pins representative keys from
`CircuitBreaker.status()`:

- `name`
- `enabled`
- `state`
- `failures_in_window`
- `failure_threshold`
- `current_recovery_seconds`
- `opens_total`
- `short_circuited_total`

### 3.4 Failure classification

The same policy is required across all three services.

Counted:

- `httpx.RequestError`
- HTTP 5xx
- HTTP 408
- HTTP 429
- unknown `Exception` subclasses

Not counted:

- HTTP 400 / 401 / 403 / 404 / 409 / 422
- `FileNotFoundError`
- `PermissionError`
- `OSError`

This preserves the Phase 6 intent: protect against upstream outages and
pressure, not against caller-side validation/auth problems or local file
system errors.

## 4. Source Documents

The closeout contract requires this MD to reference the three source PR
records:

- `docs/DEV_AND_VERIFICATION_CIRCUIT_BREAKER_DEDUP_VISION_20260507.md`
- `docs/DEV_AND_VERIFICATION_CIRCUIT_BREAKER_CAD_ML_20260508.md`
- `docs/DEV_AND_VERIFICATION_CIRCUIT_BREAKER_ATHENA_20260510.md`

RUNBOOK coverage remains in `docs/RUNBOOK_JOBS_DIAG.md`:

- §6 DedupCAD Vision breaker
- §7 CAD ML Platform breaker
- §8 Athena ECM breaker

## 5. Non-Goals

- No runtime-code changes.
- No breaker primitive changes.
- No new endpoint.
- No Prometheus metric rename.
- No default enablement in production.
- No P3.4 tenant cutover work.
- No CAD plugin work.

## 6. Verification Commands

### 6.1 New closeout contract

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_phase6_circuit_breaker_closeout_contracts.py
```

Expected: 6 passed.

### 6.2 Phase 6 focused regression

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/integrations/tests/test_athena_circuit_breaker.py \
  src/yuantus/api/tests/test_circuit_breaker_athena_contracts.py \
  src/yuantus/integrations/tests/test_cad_ml_circuit_breaker.py \
  src/yuantus/api/tests/test_circuit_breaker_cad_ml_contracts.py \
  src/yuantus/integrations/tests/test_circuit_breaker.py \
  src/yuantus/integrations/tests/test_dedup_vision_circuit_breaker.py \
  src/yuantus/api/tests/test_circuit_breaker_dedup_vision_contracts.py
```

Expected: 71 passed.

### 6.3 Doc-index trio

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Expected: 4 passed.

### 6.4 App boot and cold metrics smoke

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python - <<'PY'
from yuantus.api.app import create_app
from yuantus.integrations import circuit_breaker
from yuantus.observability.metrics import render_runtime_prometheus_text

circuit_breaker.reset_registry()
app = create_app()
text = render_runtime_prometheus_text()
print("routes", len(app.routes))
for name in ("dedup_vision", "cad_ml", "athena"):
    print(name, f'name="{name}"' in text)
PY
```

Expected: `routes 676` and all three breaker names print `True`.

### 6.5 Diff hygiene

```bash
git diff --check
```

Expected: clean.

## 7. Result Snapshot

Post-implementation verification:

- P6.4 closeout contract:
  `src/yuantus/meta_engine/tests/test_phase6_circuit_breaker_closeout_contracts.py`
  — 6 passed.
- Phase 6 focused regression: 71 passed.
- Doc-index trio: 4 passed.
- App boot and cold metrics smoke: `routes 676`; `dedup_vision`,
  `cad_ml`, and `athena` all present in cold metrics output.
- `py_compile` on the new closeout contract: passed.
- `git diff --check`: clean.

## 8. Next Step

After this P6.4 closeout PR merges, Phase 6 is complete. Further work
should be selected explicitly from a new phase or external trigger; do
not auto-start P3.4 tenant cutover or CAD plugin work from this closeout.
