# CAD Extractor External Verification (2026-01-28 11:42 +0800)

==============================================
CAD Extractor External Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
EXTRACTOR: http://127.0.0.1:8200
SAMPLE: /Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Upload CAD file and enqueue extract job
OK: Uploaded file: 630a312a-628f-40b7-b5cc-5f317536aa5e
OK: Created job: 13d2ede0-5c4c-4924-a11e-5ecb5936f65b

==> Process cad_extract job (direct)
OK: Job completed

==> Verify extracted attributes source=external
OK: External extractor verified

==============================================
CAD Extractor External Verification Complete
==============================================
ALL CHECKS PASSED
