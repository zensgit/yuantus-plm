# S8 Ops Monitoring Design

## Goals
- Expose quota usage across tenants for platform operators.
- Add explicit audit retention visibility and manual prune control.
- Attach tenant/org context metadata to reports summary responses.

## API Additions
- `GET /api/v1/admin/tenants/quotas`
  - Platform admin only.
  - Returns quota + usage per tenant.
  - Optional `org_id` for meta usage in `db-per-tenant-org`.

- `GET /api/v1/admin/audit/retention`
  - Superuser only.
  - Returns retention configuration and last prune timestamp.
  - If `tenant_id` differs from current, requires platform admin.

- `POST /api/v1/admin/audit/prune`
  - Superuser only.
  - Executes retention pruning for target tenant.
  - Uses `YUANTUS_AUDIT_RETENTION_*` settings.

- `GET /api/v1/reports/summary`
  - Adds `meta` with `{tenant_id, org_id, tenancy_mode, generated_at}`.

## Audit Retention Logic
- Retention behavior is centralized in `security/audit_retention.py`.
- Per-tenant prune tracking avoids repeated deletions per interval.
- Tenant scoping is enforced by passing the resolved tenant id into retention calls.

## Security Considerations
- Cross-tenant access is limited to platform admins.
- Tenant-local superusers can only access their own audit retention.

## Multi-Tenancy Notes
- In `db-per-tenant-org`, quota usage for files/jobs requires `org_id`.
- When `org_id` is not provided, meta usage fields remain `null`.
