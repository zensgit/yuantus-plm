# OdooPLM 19 CAD-PDM A3 Workstation Checkout Context — Implementation / Verification

Date: 2026-06-10

## Scope

Implements the A3 taskbook's R1 workstation-context slice:

- Adds checkout context fields to `ItemVersion` and `VersionFile`.
- Persists optional `client_host`, `client_workspace_path`, and `client_info` on item-level and file-level checkout.
- Keeps legacy callers compatible: missing context remains allowed and idempotent.
- Rejects same-user idempotent checkout from a different nonempty workstation/workspace context.
- Clears context on checkin, undo checkout, file-lock release, and version release.
- Exposes `lock_context` in checkout/status/lock responses that already surface lock state.
- Forwards workstation context through the CAD desktop helper and Lisp shell checkout path.

No new route is added; the route-count baseline remains unchanged.

## Files

- `src/yuantus/meta_engine/version/checkout_context.py`
- `src/yuantus/meta_engine/version/models.py`
- `src/yuantus/meta_engine/version/service.py`
- `src/yuantus/meta_engine/version/file_service.py`
- `src/yuantus/meta_engine/web/version_lifecycle_router.py`
- `src/yuantus/meta_engine/web/version_file_router.py`
- `src/yuantus/meta_engine/web/cad_checkin_router.py`
- `src/yuantus/meta_engine/services/checkin_service.py`
- `clients/cad-desktop-helper/Helper/HelperRuntime.cs`
- `clients/cad-desktop-helper/Lisp/yuantus_cad_helper.lsp`
- `clients/cad-desktop-helper/verify_lisp_shell_static.py`
- `migrations/versions/a3_checkout_context_001_add_workstation_checkout_context.py`
- `src/yuantus/meta_engine/tests/test_a3_workstation_checkout_context.py`

## Verification Plan

- A3 context tests: item/version checkout, file checkout, router payload/response, conflict mapping, model/migration lock-step.
- Existing checkout blast radius: checkin manager, version checkout/checkin router, version file checkout router/service, doc-sync checkout gate tests.
- CAD helper contracts: C# G1-A document lock test confirms POST body includes workstation/workspace context.
- Lisp static verifier: confirms checkout JSON carries `client_workspace_path` from `DWGPREFIX`.
- Migration: `alembic upgrade head` against a fresh database, single head.
- Doc-index contracts: this DEV/V doc is indexed.

## External Boundary

CI can statically prove helper/Lisp request shaping, but it cannot load the Lisp shell inside a real ZWCAD/GstarCAD host. Native CAD operational signoff remains an external smoke step.
