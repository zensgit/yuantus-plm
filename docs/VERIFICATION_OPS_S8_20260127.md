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
OK: Created Part: 2eaf3fd7-d3f4-4908-a820-62bf5070efdd

==> Upload file
OK: Uploaded file: a0fd0c2f-7e6b-4aa7-8432-91b8abe14854

==> Create ECO stage + ECO
OK: Created ECO: ccb42c12-1250-471d-8076-aceb30e35771

==> Create job
OK: Created job: a2da9c65-770f-4a96-ab90-265f4daf16ba

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
