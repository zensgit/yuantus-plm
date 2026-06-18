# Dev & Verification: CAD-PDM C3 date-BOM auto-obsolete — wiring (Slice 2)

Date: 2026-06-18
Status: **IMPLEMENTED** — pending review + merge. **Default-OFF.**
Builds on Slice 1 (#797, the unwired mechanism). Taskbook #792.

## 1. What's wired (default-off → no behavior change until a deployment opts in)

- **Settings** (`config/settings.py`, restart-only): `DATE_EFFECTIVITY_OBSOLETE_ENABLED`
  (default false — the global kill-switch), `…_POLL_INTERVAL_SECONDS` (300),
  `…_BATCH_SIZE` (100), `…_SYSTEM_USER_ID` (0 — the user recorded for the obsolete promote;
  unset → the promote is recorded as `child_obsolete_failed`, only the parent flag is written).
- **Polling worker** `DateObsoleteWorker` (`services/date_obsolete_worker.py`) — **scan-based**
  (no outbox), mirroring `EcmPublicationOutboxWorker`'s lifecycle (`run_once` /
  `run_once_with_session` / `run_forever`). It drains the **whole** expired set each tick
  (`process_expired` is idempotent, so re-processing an already-Obsolete item is a cheap no-op) —
  a per-tick head slice would NOT converge, so `batch_size` is only a **backlog-warning threshold**,
  not a correctness cap. **Two gates, both required**: the global setting **and** the per-tenant
  `EntitlementService.is_entitled("cadpdm_date_obsolete")` — that key is **registered in
  `FEATURE_APP_NAMES`** (SKU `plm.cadpdm_date_obsolete`) so a provisioned tenant can actually opt
  in; a mis-registered key surfaces loudly (logged), not as a silent False. One bad row never stops
  the sweep.
- **Admin-gated ops routes** (`web/date_obsolete_ops_router.py`, +3 → route count **716 → 719**):
  `GET /api/v1/cadpdm/date-obsolete-impacts[?state]`, `GET .../{id}`,
  `POST .../{id}/acknowledge` (open → acknowledged). Read + ack only; never re-triggers obsolete.
- Router registered in `api/app.py`. The `meta_date_obsolete_impacts` table already shipped in the
  tenant baseline (Slice 1 #797), so the booted-app drift-guard stays consistent.

## 2. Verification (`test_date_obsolete_wiring.py`, 10 pass; + Slice-1 11 = 21)

Worker (REAL entitlement path — seeds an Active `AppLicense`, not a monkeypatched stub): disabled →
no-op; enabled-but-no-license → no-op; enabled+licensed → drains and flags the depth-1 parent
(proving the gate can flip true); `run_once` short-circuits without opening a session when the
kill-switch is off; **batch_size=1 with 2 expired → ONE tick flags BOTH parents** (convergence —
batch is not a hard cap). Ops: list + `?state` filter; invalid state `422`; get `404`; acknowledge
(open→acknowledged, records `acknowledged_by_id`/`_at`); acknowledge `404`; all admin-gated. **Route
count 719** (4 pins); tenant-baseline drift-guard green in a 52-test shared-process run;
migration-coverage + CI list-order green; the new SKU does not trip the FEATURE_APP_NAMES contracts;
CI dual-registered.

## 3. Boundary

C3 is now feature-complete behind a **default-off** flag: the worker + ops surface use the Slice-1
mechanism. Enabling needs the setting on, a per-tenant entitlement, and a real
`DATE_EFFECTIVITY_OBSOLETE_SYSTEM_USER_ID` for the promote. Still out of scope: BOM-line
(`item_id`-scoped) effectivities, and a standalone worker-daemon CLI entrypoint (the worker class
is ready; packaging it as a managed process is operational). The pre-existing
`find_effective_version` NULL-start narrowness (noted in Slice 1) remains a separate fix.
