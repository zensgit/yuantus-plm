# Dev & Verification Report - P4/P5/P6 Hardening (2026-02-07)

This delivery tightens permission boundaries and verification coverage for Phase 4/5/6 features while keeping the strict gate green.

## Scope

- P4 Baseline: permissions + pagination stability.
- P5 Search/Reports: DB-fallback verification + report export permission regression test.
- P6 E-sign: key rotation hook + audit hardening.

## Changes

### P4 - Baselines

- Permission enforcement now applies to:
  - `POST /api/v1/baselines/{baseline_id}/validate`
  - `POST /api/v1/baselines/{baseline_id}/release`
  - `POST /api/v1/baselines/{baseline_id}/compare`
  - `POST /api/v1/baselines/compare-baselines`
  - `GET /api/v1/baselines/comparisons/{comparison_id}/details`
  - `GET /api/v1/baselines/comparisons/{comparison_id}/export`
- Stable pagination for baseline members: order by `(level, path, id)` to prevent page drift.

### P5 - Search/Reports

- Search engine fallback (ES not installed/unavailable): add unit coverage to ensure the DB fallback returns stable `{total, hits}` shape.
- Report export permission regression test: ensure `allowed_roles` is enforced when the report is public but role-gated.

### P6 - Electronic Signatures

- Key rotation support for verification:
  - New config: `YUANTUS_ESIGN_VERIFY_SECRET_KEYS` (comma-separated old secrets).
  - Verification accepts any configured key (current + old), while signing uses the primary secret.
- Audit correctness: `verify` audit log records the actual verifier identity (caller), not the original signer.
- Audit endpoints are now admin-only:
  - `GET /api/v1/esign/audit-logs`
  - `GET /api/v1/esign/audit-summary`
  - `GET /api/v1/esign/audit-logs/export`

## Files Changed

- `src/yuantus/meta_engine/web/baseline_router.py`
- `src/yuantus/meta_engine/esign/service.py`
- `src/yuantus/meta_engine/web/esign_router.py`
- `src/yuantus/config/settings.py`
- `src/yuantus/meta_engine/tests/test_baseline_router_permissions.py` (new)
- `src/yuantus/meta_engine/tests/test_esign_router_permissions.py` (new)
- `src/yuantus/meta_engine/tests/test_esign_key_rotation.py` (new)
- `src/yuantus/meta_engine/tests/test_search_service_fallback.py` (new)
- `src/yuantus/meta_engine/tests/test_report_router_permissions.py` (new)

## Verification

Results logged in `docs/VERIFICATION_RESULTS.md`:

- `Run PYTEST-TARGETED-P4P5P6-20260207-0930`
- `Run PYTEST-NON-DB-20260207-0930`
- `Run PYTEST-DB-20260207-0930`
- `Run PLAYWRIGHT-E2E-20260207-0930`
