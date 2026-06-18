# Dev & Verification: MES audit tenant attribution (Consumption R2.2 follow-up)

Date: 2026-06-17
Status: **IMPLEMENTED** — pending gate review + merge
Closes the deferred nit from the R2.2 security review
(`DEV_AND_VERIFICATION_ODOO18_CONSUMPTION_MES_INGEST_CREDENTIAL_20260617.md` §3.1).
Roadmap: `DEVELOPMENT_ROADMAP_AND_TODO_20260617.md` §2 (MES audit-attribution follow-up).

## 1. Problem

The MES ingest route is whitelisted from JWT, so `AuthEnforcementMiddleware` skips it and
`TenantOrgContextMiddleware` set `tenant_id_var` from the **untrusted `x-tenant-id` header**. The
`AuditLogMiddleware` reads `get_request_context().tenant_id` (= `tenant_id_var`), so a caller
could put an **arbitrary string** in the audit row's `tenant_id` for that path — attribution-only
(the data path is isolated by the credential-pinned schema), but a forensics blemish on a
security boundary.

## 2. Fix (minimal, contained)

`TenantOrgContextMiddleware` now skips header-derived tenant/org for the **machine** MES path
(reusing `auth_enforce._is_mes_ingest_path`): `tenant_id`/`org_id` are forced to `None` rather
than read from the header. So the audit log records **no caller-supplied tenant** for the MES
route. Data isolation is unchanged — the credential dependency still pins the bound tenant on its
own session (the contextvar value during the request never affected the schema; see R2.2 §3.1).

Normal (non-MES) routes are untouched: they still derive tenant/org from the header.

Note: this removes the *spoofable* attribution; recording the *bound* `MES_INGEST_TENANT_ID` in
the audit row (rather than `None`) would require threading the config tenant into the
request-context (the credential dep runs in a separate threadpool context) — a larger, separate
refinement, intentionally not in this minimal fix.

## 3. Verification (`test_consumption_mes_ingest_credential.py`, 14 pass)

- a `POST …/mes-actuals` with `x-tenant-id: tenant-EVIL` → the in-request `tenant_id_var` is
  `None` (header ignored) → audit records no caller tenant.
- a normal route with `x-tenant-id: tenant-T` → `tenant_id_var == "tenant-T"` (unchanged).
- no import cycle (`context` ← `auth_enforce`); app builds; route count **713**; 16 auth/
  middleware/tenant tests green; R2.2 credential behavior unchanged.

## 4. Files

`api/middleware/context.py` · `tests/test_consumption_mes_ingest_credential.py` ·
`docs/DELIVERY_DOC_INDEX.md` (this doc).
