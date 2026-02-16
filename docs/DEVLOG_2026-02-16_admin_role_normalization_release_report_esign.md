# DEVLOG 2026-02-16: Admin Role Normalization (Release/Reports/E-Sign)

## Background

`release-orchestration` already used role checks, but `reports` and `esign` had stricter case-sensitive role matching in some paths.
This could cause false `403` responses for valid admin/superuser callers when role values contained uppercase letters or surrounding spaces.

## Changes

### 1) Report router admin/access checks hardened

File:
- `src/yuantus/meta_engine/web/report_router.py`

Updates:
- `_is_admin(user)` now:
  - accepts `is_superuser=true` directly
  - normalizes `roles` as trimmed lowercase strings
- `_can_access_report(report, user)` now:
  - normalizes both `allowed_roles` and `user.roles` before intersection
  - preserves existing public/private/owner semantics

### 2) E-sign admin guard normalized

File:
- `src/yuantus/meta_engine/web/esign_router.py`

Updates:
- `_ensure_admin(user)` now:
  - normalizes roles (`strip().lower()`)
  - supports missing `is_superuser` attribute safely via `getattr`

### 3) Release orchestration admin guard normalization

File:
- `src/yuantus/meta_engine/web/release_orchestration_router.py`

Updates:
- `_ensure_admin(user)` now trims role strings before lowercase matching

## Regression Tests

Updated/added tests:
- `src/yuantus/meta_engine/tests/test_report_router_permissions.py`
  - allows superuser export without admin role
  - allows case-insensitive/whitespace role match for report export
- `src/yuantus/meta_engine/tests/test_esign_router_permissions.py`
  - allows case-insensitive admin role for audit logs
  - allows superuser for audit summary
  - helper now overrides `get_identity_db` for deterministic permission-route tests
- `src/yuantus/meta_engine/tests/test_release_orchestration_router.py`
  - allows superuser plan access without admin role
  - allows uppercase/whitespace admin role

## Verification

Command:

```bash
./.venv/bin/pytest -q \
  src/yuantus/meta_engine/tests/test_report_router_permissions.py \
  src/yuantus/meta_engine/tests/test_esign_router_permissions.py \
  src/yuantus/meta_engine/tests/test_release_orchestration_router.py
```

Result:

- `21 passed`

