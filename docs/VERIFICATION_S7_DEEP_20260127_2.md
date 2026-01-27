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
==> Update quota limits
==> Org quota enforcement
==> User quota enforcement
==> File quota enforcement
==> Job quota enforcement
ALL CHECKS PASSED

==> Audit logs
==============================================
Audit Logs Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity
OK: Seeded identity

==> Login as admin
OK: Admin login

==> Trigger audit log (health request)
OK: Health request logged

==> Fetch audit logs
Audit logs: OK
OK: Audit logs verified

==============================================
Audit Logs Verification Complete
==============================================
ALL CHECKS PASSED

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
OK: Created Part: 5924151f-632f-46a7-a482-ed1ec783911d

==> Search status
OK: Search engine: db

==> Reindex
OK: Reindex completed (indexed=1005)

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
NEW_TENANT: tenant-provision-1769502823
==============================================

==> Seed platform admin identity
OK: Platform admin seeded

==> Login as platform admin
OK: Platform admin login

==> Check platform admin access
OK: Platform admin access OK

==> Verify non-platform admin is blocked
OK: Non-platform admin blocked

==> Create tenant with default org + admin
OK: Tenant created: tenant-provision-1769502823

==> Get tenant
OK: Tenant fetched

==> Create extra org for tenant
OK: Extra org created

==> Login as new tenant admin
OK: New tenant admin login

==> Get tenant info as new admin
OK: Tenant info accessible

==============================================
Tenant Provisioning Verification Complete
==============================================
ALL CHECKS PASSED

==============================================
S7 Deep Verification Complete
==============================================
ALL CHECKS PASSED
