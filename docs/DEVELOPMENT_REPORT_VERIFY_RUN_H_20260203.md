# Development + Verification Report (verify_run_h)

Date: 2026-02-03

## Summary
- Fixed RBAC/local user provisioning to avoid username collisions when identity user IDs differ from existing seed users.
- Verified the end-to-end `scripts/verify_run_h.sh` flow against the local API.

## Development
### Change
- Ensure `RBACUser` and `LocalUser` are created with the current identity user ID even if the username already exists.
- Guard username updates to avoid unique-constraint conflicts.

### Code
- `src/yuantus/api/dependencies/auth.py`
  - Added helpers to pick a unique username and to avoid updating to a taken username.
  - Updated `_ensure_local_user` and `_ensure_rbac_user` to create users with a unique username when the preferred name is already used by another ID.

## Verification
### Environment
- API: `./.venv/bin/yuantus start --port 7910`
- DB: `YUANTUS_TENANCY_MODE=db-per-tenant-org`, `YUANTUS_DATABASE_URL=sqlite:///yuantus_mt_skip.db`

### Notes
- The existing tenant DB was missing `meta_files.cad_bom_path` / `meta_files.cad_dedup_path` columns. I ran the tenant DB migration helper to apply pending Alembic migrations before verification.

### Commands
```bash
./scripts/migrate_tenant_db.sh tenant-1 org-1
./scripts/verify_run_h.sh http://127.0.0.1:7910 tenant-1 org-1
```

### Result
- `ALL CHECKS PASSED`
