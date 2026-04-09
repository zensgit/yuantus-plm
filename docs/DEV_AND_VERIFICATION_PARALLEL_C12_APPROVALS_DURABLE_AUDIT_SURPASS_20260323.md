# C12 - Approvals Durable Audit Surpass: Development & Verification (2026-03-23)

## 1. Changed Files

- `src/yuantus/meta_engine/approvals/models.py`
- `src/yuantus/meta_engine/approvals/service.py`
- `src/yuantus/meta_engine/web/approvals_router.py`
- `src/yuantus/meta_engine/bootstrap.py`
- `migrations/versions/a2b2c3d4e7a6_add_approvals_and_subcontracting_tables.py`
- `src/yuantus/meta_engine/tests/test_approvals_service.py`
- `src/yuantus/meta_engine/tests/test_approvals_router.py`
- `src/yuantus/meta_engine/tests/test_bootstrap_domain_model_registration.py`
- `docs/DESIGN_PARALLEL_C12_APPROVALS_DURABLE_AUDIT_SURPASS_20260323.md`

## 2. What Changed

- Added a durable `ApprovalRequestEvent` audit table
- Shifted approvals lifecycle/history reads to persisted events with legacy fallback
- Normalized approvals export formats with case-insensitive parsing
- Aligned approvals and subcontracting tables for `SCHEMA_MODE=migrations`
- Aligned `create_all()` bootstrap registration with the new models

## 3. Verification

- Targeted approvals + bootstrap regression:
  - `44 passed, 19 warnings`
- Cross-domain regression:
  - `105 passed, 53 warnings`
- `py_compile` passed for migration and core approvals files

## 4. Verification Commands

```bash
pytest -q src/yuantus/meta_engine/tests/test_approvals_service.py src/yuantus/meta_engine/tests/test_approvals_router.py src/yuantus/meta_engine/tests/test_bootstrap_domain_model_registration.py
pytest -q src/yuantus/meta_engine/tests/test_file_viewer_readiness.py src/yuantus/meta_engine/tests/test_approvals_service.py src/yuantus/meta_engine/tests/test_approvals_router.py src/yuantus/meta_engine/tests/test_bootstrap_domain_model_registration.py src/yuantus/meta_engine/tests/test_subcontracting_service.py src/yuantus/meta_engine/tests/test_subcontracting_router.py
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile migrations/versions/a2b2c3d4e7a6_add_approvals_and_subcontracting_tables.py src/yuantus/meta_engine/approvals/models.py src/yuantus/meta_engine/approvals/service.py src/yuantus/meta_engine/web/approvals_router.py src/yuantus/meta_engine/bootstrap.py
```

## 5. Result Summary

- Approvals history now survives resubmissions through stored event rows.
- The schema and bootstrap layers are aligned for both runtime `create_all()` and migration-driven deployments.
- Export behavior is less brittle for downstream callers.
