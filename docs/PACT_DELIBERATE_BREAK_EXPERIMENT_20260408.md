# Pact Deliberate Break Experiment — 2026-04-08

## Purpose

Prove on the first day that the Pact contract gate between Metasheet2 and
Yuantus PLM is real, not theatre. The Pact-First plan
(`docs/PACT_FIRST_INTEGRATION_PLAN_20260407.md` Day 5) calls for one
deliberate break experiment as the canonical proof that CI catches
cross-repo drift.

This document records the experiment, what was changed, what the gate
caught, and how it was reverted.

## Setup

Before the experiment:

- Pact provider verifier wired to `pact-python 3.2.1` and runnable
- Pact artifact: `contracts/pacts/metasheet2-yuantus-plm.json` (synced
  from `metasheet2/packages/core-backend/tests/contract/pacts/`)
- Wave 1 contains 6 P0 interactions; 1 (`/api/v1/health`) was passing
  end-to-end, the other 5 were failing for missing provider state (no
  test user, no test items, no test BOM relationships)
- Baseline failure count: **5**

## Step 1 — Introduce a breaking field rename in the provider

The Yuantus health endpoint was modified to rename a Pact-protected field:

```diff
 # src/yuantus/api/routers/health.py
 @router.get("/health")
 def health() -> dict:
     ctx = get_request_context()
     settings = get_settings()
     return {
         "ok": True,
-        "service": "yuantus-plm",
+        "service_name": "yuantus-plm",
         "version": __version__,
         ...
     }
```

This is exactly the kind of change that:

1. Is plausible during a refactor (rename for clarity)
2. Would silently break Metasheet2's `PLMAdapter` health check
3. Would not be caught by any test in Yuantus alone, because Yuantus's own
   tests would simply update to expect `service_name`

## Step 2 — Run the provider verifier

```bash
./.venv/bin/python -m pytest src/yuantus/api/tests/test_pact_provider_yuantus_plm.py
```

Result: **6 pact failures** (up from baseline 5).

The new failure was reported with a precise message:

```
2) Verifying a pact between Metasheet2 and YuantusPLM
   Given the provider is up - probe service health
   2.1) has a matching body
        $ -> Actual map is missing the following keys: service
```

The other 5 failures were unchanged (missing provider state for
auth/items/BOM, deferred to Wave 1.5 work).

## Step 3 — Revert and re-verify

```diff
 -        "service_name": "yuantus-plm",
 +        "service": "yuantus-plm",
```

Re-running the verifier produced **5 pact failures** again, with the
health interaction back in the passing set:

```
probe service health (2ms loading, 277ms verification)
```

(no entry in the failure list — the interaction passed)

## Result Matrix

| Stage | Total failures | health interaction |
|---|---|---|
| Baseline | 5 | ✅ PASS |
| After deliberate break (`service` → `service_name`) | **6** | ❌ FAIL — `missing keys: service` |
| After revert | 5 | ✅ PASS |

## What This Proves

1. **The pact gate is wired end-to-end.** A field rename in Yuantus is
   visible to the Yuantus-side verifier as a contract violation, not just
   as a Yuantus-internal change.

2. **The failure message is precise.** The diagnostic names the exact
   missing field (`service`), not a generic "shape mismatch". A future
   on-call engineer reading this would know what to fix.

3. **The gate is non-flaky.** Reverting the change immediately restores
   the green state for that interaction, with no manual intervention.

4. **The 5 unrelated state-handler failures did not interfere.** The
   deliberate break added exactly +1 to the failure count, in a clearly
   identifiable position. The signal is not lost in the noise.

5. **Independent evolution is now actually safe.** Before this experiment,
   "Metasheet and Yuantus can evolve independently" was an assumption.
   After this experiment, it is a tested property.

## Known Wave 1.5 Gap — Provider State Handlers

The 5 still-failing interactions all need provider state setup:

| Interaction | Why it fails today | What it needs |
|---|---|---|
| `POST /api/v1/auth/login` | no user `metasheet-svc` exists → 401 | seed test user in identity DB |
| `GET /api/v1/search/` | no auth token / no items → 401 / empty | seed token + at least one Item |
| `POST /api/v1/aml/apply` | item `01H...P1` does not exist → 400 | seed test Part with that ID |
| `GET /api/v1/bom/{id}/tree` | item / BOM does not exist → 400 | seed Part + BOM relationship |
| `GET /api/v1/bom/compare` | items do not exist → 400 | seed two Parts + BOM data |

These should be implemented in
`src/yuantus/api/tests/test_pact_provider_yuantus_plm.py`'s
`_provider_state_handler` once the test database story is decided. They
are NOT part of the Wave 1 deliverable; they are explicitly tracked as
Wave 1.5 work in
`docs/PACT_FIRST_INTEGRATION_PLAN_20260407.md`.

## Verifier Improvements Made During This Session

While running the verifier for the first time, two scaffold bugs were
found in `src/yuantus/api/tests/test_pact_provider_yuantus_plm.py` and
fixed in the same commit as this document:

1. **`add_source(directory)` choked on README.md.** The original code
   passed the entire `contracts/pacts/` directory to pact-python, which
   then tried to parse `README.md` as a Pact JSON file. Fixed by
   iterating discovered `*.json` files individually with
   `add_source(str(path))`.

2. **Yield-body exceptions were swallowed by the readiness loop.** The
   original `_running_provider` context manager wrapped both the
   readiness probe and the yielded test body in the same `try/except`,
   so any exception raised by the test (notably pact-python's "Host
   mismatch: 127.0.0.1 != localhost") was caught as a readiness failure
   and surfaced as the misleading "Pact provider server exited before
   becoming ready". Fixed by splitting `_wait_for_ready()` into its own
   loop that only catches `requests.RequestException`, then yielding
   outside that loop with a plain `try/finally` for shutdown.

3. **`localhost` vs `127.0.0.1` for the Pact verifier transport.**
   pact-python's `Verifier` defaults `self._host = "localhost"` and
   refuses any `add_transport(url=...)` whose hostname differs. The
   default bind host was changed from `127.0.0.1` to `localhost` to
   match. The override is still available via `YUANTUS_PACT_HOST`.

These fixes were necessary preconditions for the deliberate break
experiment to be runnable at all.

## Reproducibility

To re-run this experiment locally:

```bash
# 1. Ensure pact-python is installed
./.venv/bin/pip install pact-python   # 3.2.1 known good

# 2. Confirm the baseline
./.venv/bin/python -m pytest \
   src/yuantus/api/tests/test_pact_provider_yuantus_plm.py 2>&1 \
   | grep "There were"
# Expected: There were 5 pact failures

# 3. Apply the break
sed -i '' 's/"service": "yuantus-plm"/"service_name": "yuantus-plm"/' \
   src/yuantus/api/routers/health.py

# 4. Re-run; expect 6 failures
./.venv/bin/python -m pytest \
   src/yuantus/api/tests/test_pact_provider_yuantus_plm.py 2>&1 \
   | grep "There were"
# Expected: There were 6 pact failures
# Expected new failure: "Actual map is missing the following keys: service"

# 5. Revert
sed -i '' 's/"service_name": "yuantus-plm"/"service": "yuantus-plm"/' \
   src/yuantus/api/routers/health.py

# 6. Re-run; expect baseline 5 failures again
./.venv/bin/python -m pytest \
   src/yuantus/api/tests/test_pact_provider_yuantus_plm.py 2>&1 \
   | grep "There were"
# Expected: There were 5 pact failures
```

## Cross-References

- `docs/PACT_FIRST_INTEGRATION_PLAN_20260407.md` — Day 5 experiment plan
- `docs/PLM_STANDALONE_METASHEET_BOUNDARY_STRATEGY_20260407.md` — strategy
- `docs/METASHEET_REPO_SOURCE_OF_TRUTH_INVESTIGATION_20260407.md` — source-of-truth
- `contracts/pacts/metasheet2-yuantus-plm.json` — Wave 1 pact artifact
- `src/yuantus/api/tests/test_pact_provider_yuantus_plm.py` — provider verifier
- `metasheet2/packages/core-backend/tests/contract/` — consumer side
