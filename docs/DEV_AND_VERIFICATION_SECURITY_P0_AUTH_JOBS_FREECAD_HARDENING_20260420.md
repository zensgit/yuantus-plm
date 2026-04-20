# DEV_AND_VERIFICATION_SECURITY_P0_AUTH_JOBS_FREECAD_HARDENING_20260420

## Goal

Close the highest-risk findings from the April 20 head review without reopening the broader P1/P2 delivery chain: remove anonymous `user_id=1` fallback, require auth on `/api/v1/jobs`, redact jobs diagnostics path leakage, and stop FreeCAD script generation from embedding unsanitized user-controlled file names or paths.

## Code Changes

1. `src/yuantus/api/dependencies/auth.py`
   - Changed `get_current_user_id_optional()` to return `None` for anonymous requests instead of silently coercing to `1`.
2. `src/yuantus/api/routers/jobs.py`
   - Switched `POST /jobs`, `GET /jobs`, and `GET /jobs/{job_id}` to `Depends(get_current_user_id)`.
   - Reduced diagnostics output to storage metadata and asset-presence booleans.
   - Removed direct exposure of `system_path`, resolved local path, and derived asset paths.
3. `src/yuantus/meta_engine/services/cad_converter_service.py`
   - Added safe filename-stem normalization for generated directories and output files.
   - Reworked FreeCAD conversion/preview scripts to load parameters from a temp JSON file passed via environment variable instead of interpolating raw paths into generated Python.
4. `src/yuantus/meta_engine/tests/test_warning_headers.py`
   - Updated the jobs router override to match the new authenticated dependency.
5. `src/yuantus/meta_engine/tests/test_jobs_router_auth.py`
   - Added focused auth and diagnostics tests for `/jobs`.
6. `src/yuantus/meta_engine/tests/test_cad_converter_service_security.py`
   - Added focused tests for FreeCAD parameterization and filename sanitization.

## Verification

Focused regression command:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_jobs_router_auth.py \
  src/yuantus/meta_engine/tests/test_warning_headers.py \
  src/yuantus/meta_engine/tests/test_cad_converter_service_security.py \
  src/yuantus/meta_engine/tests/test_cad_converter_service_queue_shim.py
```

Documentation index contracts:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

## Expected Security Outcome

1. Anonymous requests no longer inherit `user_id=1`.
2. `/api/v1/jobs` no longer exposes queue contents or job diagnostics to unauthenticated callers.
3. Jobs diagnostics remain operationally useful without leaking internal filesystem or object-storage addresses.
4. FreeCAD worker scripts no longer contain attacker-controlled path literals, and generated artifact names stay within a safe filesystem subset.

## Residual Note

This change intentionally narrows the first security cut to auth helper semantics, `/jobs`, and CAD script generation. Other endpoints still using `get_current_user_id_optional()` now receive `None` instead of `1`; they should be audited incrementally for explicit anonymous behavior versus authenticated-only behavior.
