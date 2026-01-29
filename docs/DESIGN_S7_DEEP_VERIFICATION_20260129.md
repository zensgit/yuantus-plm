# S7 Deep Verification Design (2026-01-29)

## Goal
Validate multi-tenant isolation and ops hardening in `db-per-tenant-org` mode with a deterministic execution order and a single command runner.

## Scope
- Multi-tenant isolation across tenant/org boundaries
- Quota enforcement (org/user/file/job)
- Audit logging integrity
- Ops health endpoints
- Search reindex
- Tenant provisioning (platform admin)

## Execution Order (Authoritative)
1. **Health + tenancy mode gate** (must be `db-per-tenant` or `db-per-tenant-org`)
2. **Ops Hardening**
   - Multi-tenancy isolation checks
   - Quota enforcement checks
   - Audit log checks
   - Ops health checks
   - Search reindex checks
3. **Tenant Provisioning** (platform admin)

This order is enforced by `scripts/run_s7_deep.sh` → `scripts/verify_s7.sh`.

## Runner & Scripts
- Runner: `scripts/run_s7_deep.sh`
- Core orchestration: `scripts/verify_s7.sh`
- Sub-checks:
  - `scripts/verify_ops_hardening.sh`
  - `scripts/verify_multitenancy.sh`
  - `scripts/verify_quota_enforcement.sh`
  - `scripts/verify_audit_logs.sh`
  - `scripts/verify_ops_health.sh`
  - `scripts/verify_search_reindex.sh`
  - `scripts/verify_tenant_provisioning.sh`

## Required Environment
- API running in **db-per-tenant-org** mode
- Postgres identity + tenant DBs accessible
- Platform admin enabled for provisioning (optional)

Defaults used by the runner:
- `DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
- `DB_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}`
- `IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`

## Command (This Run)
```bash
bash scripts/run_s7_deep.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2 \
  | tee docs/VERIFICATION_S7_DEEP_20260129_1504.md
```

## Expected Artifacts
- Verification report (raw): `docs/VERIFICATION_S7_DEEP_20260129_1504.md`

## Pass/Fail Criteria
- All sub-checks emit `ALL CHECKS PASSED`
- Final summary: `S7 Deep Verification Complete` and `ALL CHECKS PASSED`

## Notes
- If tenancy mode is not multi-tenant, the runner exits with a failure and a remediation hint.
- If provisioning is not needed, set `RUN_TENANT_PROVISIONING=0`.
