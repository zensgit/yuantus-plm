# ECM Publish — P1C: Outbox Worker + Null Adapter + Ops Routes (Dev & Verification)

Date: 2026-06-16
Branch: `feat/ecm-p1c-worker-routes` (off `main` after #765)
Scope owner doc: `docs/DEVELOPMENT_ECM_PUBLISH_P0_REFRESH_TASKBOOK_20260616.md` (D5/D6)
Follows: P1A #764 (release provenance), P1B #765 (outbox + enqueue hook)

## 1. What P1C delivers

P1C lights the **dispatch half** of the PLM→ECM pipeline: a worker drains the
`meta_ecm_publication_outbox` (enqueued at release by P1B) and "publishes" each
controlled file via a **no-I/O Null adapter**, plus a minimal admin ops surface.
The **real Athena CMIS adapter is deferred to P1D** (Phase-0-gated); P1C resolves
to Null everywhere so dev/CI never performs a real external write. This completes
the goal's defined "完成" boundary (P0 + P1A + P1B + P1C).

Delivered surface:

- **Adapter layer** `ecm_publication/adapter.py` — `EcmPublicationAdapter` (ABC:
  `build_payload` / `validate_contract` / `send`) + `NullEcmPublicationAdapter` +
  local `ValidationResult` / `SendResult` dataclasses. The Null adapter reads the
  **flat** ECM snapshot (not erp's nested item/version), validates the full
  per-file identity 5-tuple, and returns a **per-file** `remote_id`
  (`null:item:version:file:role`) so multiple controlled files of one version
  never collide. `dry_run` is deliberately NOT on the ABC (structural no-send).
- **Registry** `ecm_publication/adapter_registry.py` — `resolve_adapter(target_system)`
  returns Null in P1C; the settings-gated real-CMIS branch is documented as the
  P1D extension point only (not wired).
- **Service process methods** added to `ecm_publication/service.py` (mirroring
  `erp_publication`): `process` (revalidate → build → validate → send, single
  pre-send attempt increment), `reschedule_retry` (linear backoff, guard #1),
  `replay` (operator pure failed→pending reset), `_fail_adapter_error`,
  `_mark_revalidated_not_eligible`, `_revalidate_allows_send`, `_fresh_version_id`,
  plus `EcmPublicationReplayError` and the `EcmRevalidation` verdict dataclass.
- **Worker** `ecm_publication/worker.py` — `EcmPublicationOutboxWorker`:
  `run_once` / `run_once_with_session`, `_reclaim_stale`, `_claim_batch`
  (PENDING + due + un-stale-claimed, `FOR UPDATE SKIP LOCKED` on postgres),
  `_process_row`, `run_forever` / `stop`. Reuses the generic `PUBLICATION_OUTBOX_*`
  settings (batch/backoff/stale/poll) shared with the erp worker.
- **Ops router** `web/plm_ecm_publication_outbox_router.py` — 3 routes under
  `/api/v1/plm-ecm/publication-outbox`: `GET` (list, optional `?state=`),
  `GET /{id}`, `POST /{id}/replay`. Each gated **admin → `is_entitled('ecm_publish')`**
  (both 403 before any row read). Registered in `api/app.py`.

## 2. The revalidation design choice (no mechanical erp mirror)

erp's worker revalidates via a readiness verdict (`build_publication_readiness`);
ECM has none. P1C's `_revalidate` re-fetches the released `ItemVersion` + the
specific controlled `VersionFile` (+ `FileContainer`) and recomputes the content
fingerprint. The verdict (`EcmRevalidation`) drives `_revalidate_allows_send`:

- version no longer `is_released`, or the controlled file is gone → **SKIPPED /
  not_eligible** (`properties.revalidated_ineligible`).
- recomputed fingerprint drifted from the enqueued `payload_fingerprint` → **SKIPPED /
  not_eligible** with `properties.revalidated_version_mismatch` (a stale snapshot must
  never be published).

The taskbook (D5) is silent on the exact rule; this principled mirror is the P1C
design choice. It is the one part of P1C that is not a verbatim erp copy.

## 3. Safety / correctness invariants

- **No external write in P1C**: the registry returns Null; a worker/route `sent`
  via Null explicitly does NOT mean Athena received anything (P1D is the real send).
- **Bounded retries (guard #1)**: `process` increments `attempt_count` only right
  before `send`; a pre-send adapter error (`build_payload`/`validate_contract`
  raised) is counted once by `reschedule_retry` (detected via `attempt_count_before`)
  so it can't loop forever at attempt 0. Dead-letters at `max_attempts`.
- **Two backoff formulas** (kept distinct): `reschedule_retry` = linear
  `backoff_seconds * attempt_count`; the `_process_row` exception path = flat
  `max(backoff_seconds, 1)` and also self-increments + dead-letters at max with
  `reason=remote_error`.
- **Terminal reasons stay terminal**: only `remote_error`/`adapter_error` are
  retryable; `not_eligible`/`config_missing`/`conflict`/`validation_error` are not
  rescheduled and are not replayable (router → 409).
- **replay** is a PURE state reset (no adapter resend, since the real adapter is
  P1D-deferred); `attempt_count` is reset to 0 so a dead-lettered row gets fresh
  retries (a deliberate, documented P1C choice).
- **Ops routes never bypass the gate**: admin → `is_entitled` runs before any row
  read; on these admin ops routes `is_entitled` is allowed to propagate (not the
  exception-safe enqueue-hook gate — that is the release path, not these routes).

## 4. Verification

Test env: `.venv-wp13` (python3.11); `unset YUANTUS_PYTEST_DB YUANTUS_TEST_DB PYTEST_DB`.

### 4.1 New tests (42 total, all pass)

`test_ecm_publication_adapter.py` (7): Null adapter is an `EcmPublicationAdapter`;
flat-snapshot `build_payload`; `validate_contract` flags each missing identity field
and passes on the full tuple; `send` ok + per-file `remote_id` with no error;
remote_id differs per file of the same version; `resolve_adapter` is always Null in P1C.

`test_ecm_publication_worker.py` (25): pending→sent via Null; sent not re-claimed;
claim stamps worker_id/claimed_at; pending-only claim gating; future `next_attempt_at`
not due; batch-size cap; recently-claimed not stolen; stale reclaim; fingerprint-drift
skip (`revalidated_fingerprint_drift`); unreleased-version skip; deleted-controlled-file
skip; backing-version-gone skip without crash; remote_error reschedule (no double count)
+ dead-letter loop; validation_error terminal; pre-send adapter_error counts +
dead-letters (guard #1); send-raises adapter_error dead-letter; revalidate-raises
exception path (consumes attempt, dead-letters with remote_error); no-override resolves
Null; `run_forever`/`stop`; direct service `process` wrong-state → raise, DRY_RUN_READY
processable, `reschedule_retry` linear backoff scaling; and the **released_at
representation regression** (§4.5).

`test_plm_ecm_publication_outbox_router.py` (10): non-admin → 403; not-entitled → 403;
get-missing → 404; list all + filter by state; invalid state → 422; get returns per-file
identity; replay failed/remote_error → pending (attempt_count reset, `properties.replayed`);
replay non-retryable reason → 409; replay non-failed state → 409; one TestClient HTTP
wiring test.

### 4.2 Route count

P1C adds **3 routes** → app total **709 → 712**. The four total-route pins are bumped
in lockstep (`test_metrics_router_route_count_delta` `EXPECTED_TOTAL_ROUTES`;
`test_phase4_search_closeout_contracts` literal; `test_breakage_design_loopback_metrics`
literal; `test_tier_b_3_breakage_design_loopback_portfolio_contract` substring). The two
**version-router** owner maps (`test_version_lifecycle_router_contracts` MOVED_ROUTES;
`test_version_router_decomposition_closeout_contracts` EXPECTED_OWNERS) are left
unchanged — a pure new-route addition under `/plm-ecm` does not touch the
`/api/v1/versions/*` ownership contracts.

### 4.3 CI registration

The 3 new test files are dual-registered: the `ci.yml` contracts list (sorted, enforced
by `test_ci_contracts_ci_yml_test_list_order`) AND the `conftest.py` `_ALLOWLIST_NO_DB`.
No new DB table (P1C adds none), so the migration-table coverage contract is unaffected.

### 4.4 How to reproduce

```bash
cd Yuantus && . .venv-wp13/bin/activate
unset YUANTUS_PYTEST_DB YUANTUS_TEST_DB PYTEST_DB
python -m pytest \
  src/yuantus/meta_engine/tests/test_ecm_publication_adapter.py \
  src/yuantus/meta_engine/tests/test_ecm_publication_worker.py \
  src/yuantus/meta_engine/tests/test_plm_ecm_publication_outbox_router.py \
  src/yuantus/meta_engine/tests/test_ecm_publication_enqueue.py \
  src/yuantus/meta_engine/tests/test_metrics_router_route_count_delta.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py -q
```

### 4.5 Adversarial verify (and the bug it caught)

A 4-dimension adversarial review was run over this slice (worker state machine,
gate/safety, route-count/CI pin integrity, test blind spots). It surfaced several
coverage gaps, clarity fixes, and one fingerprint-robustness hardening — all resolved:

- **`released_at` fingerprint-representation hardening** (fixed; defensive, not a
  live prod bug). The worker recomputes the content fingerprint in a *separate*
  session, so the fingerprint must not depend on a datetime's serialized
  representation: a value that round-trips with a different `isoformat()` (naive
  `…T00:00:00` vs tz-aware `…T00:00:00+00:00`) would look like content drift and
  wrongly SKIP the row. **Verified**: `ItemVersion.released_at` is a *naive*
  `Column(DateTime)` (TIMESTAMP WITHOUT TIME ZONE) in the model and every migration,
  so it round-trips naive on Postgres and this drift does **not** occur today — the
  reviewer's "tz-aware reload → silent no-op on Postgres" was a false positive about
  the column type. The fix is kept as hygiene: `released_at` is immutable provenance,
  not file content (the real drift signal is `content_fingerprint_basis`), so it is
  excluded from the fingerprint, making it robust to a future `timestamptz` migration
  or any reloaded datetime added to `build_snapshot`. The dead
  `_VOLATILE_SNAPSHOT_KEYS={'snapshotted_at'}` guard (excluded a key `build_snapshot`
  never emits) is corrected. `test_released_at_representation_change_does_not_spuriously_skip`
  pins the invariant (verified red without the fix, green with it).
- **Audit-label clarity** (fixed): content drift on the same version now sets
  `revalidated_fingerprint_drift` (not the misleading `revalidated_version_mismatch`,
  whose `revalidated_version_id` would equal `row.version_id`).
- **Coverage** (added): the worker-exception path, deleted-controlled-file skip,
  remote_error/adapter_error dead-letter loops, `run_forever`/`stop`, and direct
  service guards (wrong-state, DRY_RUN_READY, linear-backoff scaling).
- **Hardening** (added): the list route validates `?state=` (422 on invalid) and is
  bounded (`limit`, default 200, cap 1000).

## 5. Boundary / deferred

- **P1D** — the real Athena CMIS adapter (the `resolve_adapter` non-Null branch),
  gated on Phase 0 (U1–U5) against a live Athena. Until then `sent` is Null-only.
- v1 publishes on the release/promote path only (D1); ECO-apply remains out of scope.
- **No production drainer yet**: `EcmPublicationOutboxWorker` is a library class with
  `run_forever`, but nothing starts it (no CLI command, unlike the erp worker's
  `cli.py` `publication-worker`). Until a daemon/CLI entrypoint is wired, enqueued
  rows are not auto-dispatched; the ops `replay` route only resets to PENDING for a
  worker that must be run. Wiring the entrypoint + an ops re-enqueue route are
  follow-ons.
- **Unbounded replay** is a deliberate, documented P1C choice: `replay` resets
  `attempt_count` to 0 (pinned by a test) so an operator can force fresh retries; it
  does not enforce the dead-letter ceiling. A replay cap can be added with the real
  P1D adapter if needed.
- The ci.yml path-filter does not self-trigger the contracts job on
  `ecm_publication`-only source changes (same convention as `erp_publication`); a PR
  touching only that source must edit ci.yml or carry the full-CI label.
