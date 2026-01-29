==============================================
S7 Deep Verification Runner
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
TENANT_B: tenant-2, ORG_B: org-2
MODE: db-per-tenant-org
DB_URL: postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus
DB_URL_TEMPLATE: postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}
IDENTITY_DB_URL: postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg
RUN_TENANT_PROVISIONING: 1
==============================================

==============================================
S7 Deep Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
TENANT_B: tenant-2, ORG_B: org-2
RUN_TENANT_PROVISIONING: 1
==============================================

==> Ops Hardening (Multi-Tenancy + Quota + Audit + Ops + Search)
==============================================
Ops Hardening Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
TENANT_B: tenant-2, ORG_B: org-2
==============================================

==> Multi-tenancy
==============================================
Multi-Tenancy Verification
BASE_URL: http://127.0.0.1:7910
TENANT_A: tenant-1, TENANT_B: tenant-2
ORG_A: org-1, ORG_B: org-2
==============================================

==> Seed identity/meta for tenant/org combos
OK: Seeded tenant/org schemas

==> Login for each tenant/org
OK: Login succeeded

==> Create Part in tenant A/org A and verify isolation
OK: Org + tenant isolation (A1)

==> Create Part in tenant A/org B and verify isolation
OK: Org isolation (A2)

==> Create Part in tenant B/org A and verify isolation
OK: Tenant isolation (B1)

==============================================
Multi-Tenancy Verification Complete
==============================================
ALL CHECKS PASSED

==> Quotas
==> Seed identity + meta
==> Login as admin
==> Read current quota usage
SKIP: quota mode is 'disabled' (expected enforce)

==> Audit logs
==============================================
Audit Logs Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================
SKIP: audit_enabled=false (set YUANTUS_AUDIT_ENABLED=true)

==> Ops health
==============================================
Ops Health Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> /health
Health: OK
OK: /health ok

==> /health/deps
Health deps: OK
OK: /health/deps ok

==============================================
Ops Health Verification Complete
==============================================
ALL CHECKS PASSED

==> Search reindex
==============================================
Search Reindex Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Create Part item
OK: Created Part: 385727e3-594c-45e4-b1ad-375a6d75abee

==> Search status
OK: Search engine: db

==> Reindex
OK: Reindex completed (indexed=1997)

==> Search by item_number
OK: Search found item after reindex

==> Cleanup
OK: Deleted item

==============================================
Search Reindex Verification Complete
==============================================
ALL CHECKS PASSED

==============================================
Ops Hardening Verification Complete
==============================================
ALL CHECKS PASSED

==> Tenant Provisioning
==============================================
Tenant Provisioning Verification
BASE_URL: http://127.0.0.1:7910
PLATFORM_TENANT: platform
NEW_TENANT: tenant-provision-1769670263
==============================================

==> Seed platform admin identity
OK: Platform admin seeded

==> Login as platform admin
OK: Platform admin login

==> Check platform admin access
SKIP: platform admin disabled

==============================================
S7 Deep Verification Complete
==============================================
ALL CHECKS PASSED
