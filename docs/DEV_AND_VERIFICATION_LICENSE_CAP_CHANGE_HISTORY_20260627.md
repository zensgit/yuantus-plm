# L4 Fork B — Seat-cap change-history audit read endpoint (impl + verification)

> Task: backlog line 4 (V2 seats/licensing), Fork B. Branch `claude/license-cap-change-history` · base `origin/main`.

## What
`GET /api/v1/admin/license-cap-history?tenant_id=...` — a superuser HTTP read of a tenant's **seat-cap change history**, derived from the LICENSE audit trail. Today `record_seat_cap_audit` writes each cap change as `AuditLog(method="LICENSE", path="cli:license/seat-cap?max_users={N|cleared}")`, reachable only via the generic `/admin/audit` log query. This dedicated endpoint surfaces it as structured history.

## Behaviour
- Returns newest-first `changes: [{created_at, max_users, cleared}]` + `count`. `max_users` is the int the cap was set to; `cleared=true` (with `max_users=null`) for an explicit clear (`seats: null` → unlimited).
- **superuser-only** (`require_superuser`); **read-only** (`Cache-Control: no-store`).
- **No existence leak**: an unknown tenant → empty list (200), not 404. Blank `tenant_id` → 400. Optional `limit` (1..500).
- Filters strictly to `method="LICENSE"` AND `path LIKE "cli:license/seat-cap%"` AND `tenant_id` — a non-seat-cap LICENSE audit (e.g. `cli:license/import`) is excluded; tenant-isolated.

## route-count (design-lock)
New route ⇒ app-route count **723 → 724**, synced in lockstep across all four pins (phase4 authoritative, breakage, metrics `EXPECTED_TOTAL_ROUTES`, tier_b_3 literal string-pin).

## anti-false-green wiring
`test_license_cap_change_history_router.py` added to the `ci.yml` contracts list (sorted) **and** the new router + test added to the `detect_changes` **entitlement** case (license-surface changes → `run_contracts`). Mirrors the L4-1 `license_status_router` (#881) pattern. DEV/V doc registered in `DELIVERY_DOC_INDEX.md`.

## Verification (local)
`PYTHONPATH=worktree/src YUANTUS_PYTEST_DB=1 pytest` — new router test (9 cases: unknown-tenant empty 200; set caps parsed; cleared→null+flag; non-seat-cap LICENSE audit excluded; tenant isolation; blank→400; non-superuser→403; Cache-Control no-store; one route) + all four route-count pins at 724 + `test_ci_contracts_ci_yml_test_list_order` + `test_ci_change_scope_contracts` + doc-index completeness/sorting/references.

## Scope / follow-up
Read-only audit-history surface (Fork B). It does NOT add a structured cap-change table — it derives from the existing audit trail (append-only, no new write path). Fork C (license revoke) is the sibling slice. A cap-change *UI* (frontend) over this endpoint is a separate consumer-side follow-up.
