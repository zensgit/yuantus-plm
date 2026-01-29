==============================================
S8 Ops Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Quota monitoring
==> Seed identity + meta
==> Login as admin
==> Read current quota usage
==> Platform admin quota monitoring
Quota monitoring: OK
==> Update quota limits
==> Org quota enforcement
==> User quota enforcement
==> File quota enforcement
==> Job quota enforcement
ALL CHECKS PASSED

==> Audit retention endpoints
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

==> Retention endpoints
Retention endpoints: OK
Audit prune endpoint: OK
OK: Retention endpoints verified

==============================================
Audit Logs Verification Complete
==============================================
ALL CHECKS PASSED

==> Reports summary meta
==============================================
Reports Summary Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Create Part item
OK: Created Part: 4b08f811-63fe-4121-b7c6-d0bbb5e0e2ec

==> Upload file
OK: Uploaded file: 98723cb2-dab1-4e67-8e70-c2bf898dadb8

==> Create ECO stage + ECO
OK: Created ECO: 25725c6e-e76c-459c-aebb-4d5cc9e6a6e2

==> Create job
OK: Created job: a745b26e-666f-4c80-a0bd-be108e1ed6fa

==> Fetch reports summary
Summary checks: OK
OK: Summary checks passed

==============================================
Reports Summary Verification Complete
==============================================
ALL CHECKS PASSED

==============================================
S8 Ops Verification Complete
==============================================
ALL CHECKS PASSED
