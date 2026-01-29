==============================================
YuantusPLM End-to-End Regression Suite
==============================================
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
CLI: .venv/bin/yuantus
==============================================

==> Pre-flight checks
CLI: OK
Python: OK
Checking API health...
API Health: OK (HTTP 200)

Pre-flight checks passed. Starting tests...
Quota normalization: mode=enforce (set high limits for tests)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: Ops Health
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_ops_health.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
PASS: Ops Health

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: Run H (Core APIs)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_run_h.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==> Seed identity/meta
==> Login
==> Health
Health: OK
==> Meta metadata (Part)
Meta metadata: OK
==> AML add/get
AML add: OK (part_id=8d175084-933a-4851-aa1e-416c6eb04253)
AML get: OK
==> Search
Search: OK
==> RPC Item.create
RPC Item.create: OK (part_id=e8686898-39b3-428a-9b30-ffabd039a2bc)
==> File upload/download
File upload: OK (file_id=4e7262e3-90ff-4c5c-a8c7-38c88b1f4070)
File metadata: OK
File download: OK (http=302->200)
==> BOM effective
BOM effective: OK
==> Plugins
Plugins list: OK
Plugins ping: OK
==> ECO full flow
ECO stage: OK (stage_id=9bfadd44-f763-4bf6-b26f-825ede02278d)
ECO create: OK (eco_id=0d31c235-0914-4423-bcf0-a4a7faa45b35)
ECO new-revision: OK (version_id=8cac3594-252d-43df-9372-967142bdbb35)
ECO approve: OK
ECO apply: OK
==> Versions history/tree
Versions history: OK
Versions tree: OK
==> Integrations health (should be 200 even if services down)
Integrations health: OK (ok=False)

ALL CHECKS PASSED
PASS: Run H (Core APIs)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S2 (Documents & Files)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_documents.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
Documents & Files Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Create Part
OK: Created Part: 097ae066-5242-41cf-a0e5-a8e87e67733f

==> Upload file with metadata
OK: Uploaded file: 3cfe595d-37b6-44ae-af49-db95aea87813

==> Verify file metadata
OK: Metadata verified

==> Upload duplicate file (checksum dedupe)
OK: Dedupe returned same file id

==> Attach file to item
OK: Attachment created

==> Verify item attachment list
OK: Attachment list verified

==> Cleanup
OK: Cleaned up temp file

==============================================
Documents & Files Verification Complete
==============================================
ALL CHECKS PASSED
PASS: S2 (Documents & Files)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: Document Lifecycle
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_document_lifecycle.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
Document Lifecycle Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Create Document
OK: Created Document: bf4bb312-8267-41eb-960d-7f5a6fca933c

==> Initialize version
OK: Initial version 1.A

==> Verify initial state is Draft
OK: State Draft

==> Update Document in Draft
OK: Draft update

==> Promote to Review
OK: State Review

==> Promote to Released
OK: State Released

==> Update after Release should be blocked
OK: Update blocked (409)

==> Attach file after Release should be blocked
OK: Attach blocked (409)

==> Cleanup

==============================================
Document Lifecycle Verification Complete
==============================================
ALL CHECKS PASSED
PASS: Document Lifecycle

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: Part Lifecycle
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_part_lifecycle.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
Part Lifecycle Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Create Parts
OK: Created parent=385cd39e-1fde-45b9-a6a6-bfead36f78c4 child=60ba3f1a-967f-4a6d-a6f6-2b629e3a1a81 child2=a9bb0294-5eef-4580-9f1a-cfb9db21b028

==> Add BOM child in Draft
OK: BOM relationship 47a19b2d-9f93-46be-ac76-59611f4c8e4f

==> Promote to Review
OK: State Review

==> Promote to Released
OK: State Released

==> Update after Release should be blocked
OK: Update blocked (409)

==> BOM add after Release should be blocked
OK: BOM add blocked (409)

==> BOM remove after Release should be blocked
OK: BOM delete blocked (409)

==> Attach file after Release should be blocked
OK: Attach blocked (409)

==> Cleanup

==============================================
Part Lifecycle Verification Complete
==============================================
ALL CHECKS PASSED
PASS: Part Lifecycle

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S1 (Meta + RBAC)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_permissions.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==> Seed identity (admin + viewer)
Created user: admin (superuser)
==> Seed meta schema
==> Login as admin
Admin login: OK
==> Ensure viewer identity (server) is non-superuser
Viewer identity: OK (id=1769676410)
==> Configure PermissionSets
Created PermissionSet: ReadOnly-1769678144
ACE viewer (read-only): OK
ACE admin (full): OK
==> Assign PermissionSet to ItemTypes
Assigned permission to Part: OK
Assigned permission to Part BOM: OK
==> Admin creates Part (should succeed)
Admin AML add Part: OK (part_id=a5e2848c-3e79-4b4e-a223-eedd217a4766)
Admin created child Part: OK (child_id=78085035-182c-4e07-9695-50398ecf7310)
==> Login as viewer
Viewer login: OK
==> Viewer READ operations (should succeed)
Viewer AML get Part: OK (200)
Viewer search: OK (200)
Viewer BOM effective: OK (200)
==> Viewer WRITE operations (should fail with 403)
Viewer AML add Part: BLOCKED (403) - EXPECTED
Viewer BOM add child: BLOCKED (403) - EXPECTED
Viewer AML update Part: BLOCKED (403) - EXPECTED
==> Admin WRITE operations (should succeed)
Admin BOM add child: OK
Admin AML update Part: OK
==> Viewer can read updated BOM tree
Viewer BOM tree with children: OK (200)

ALL CHECKS PASSED
PASS: S1 (Meta + RBAC)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S7 (Quotas)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_quotas.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==> Seed identity + meta
==> Login as admin
==> Read current quota usage
==> Update quota limits
==> Org quota enforcement
==> User quota enforcement
==> File quota enforcement
==> Job quota enforcement
ALL CHECKS PASSED
PASS: S7 (Quotas)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S3.1 (BOM Tree)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_bom_tree.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==> Seed identity
Created admin user
==> Seed meta schema
==> Login as admin
Admin login: OK
==> Create test parts for BOM tree
Created Part A: ee25650c-b405-4a2e-99c6-fe2342b75a44
Created Part B: b28777e9-2df8-43a9-82df-8d97fe7455d1
Created Part C: ac679211-df91-474a-8375-297a336160a0
Created Part D: 9f68fe29-231e-4077-a754-7cd545d5c486
==> Build BOM structure: A -> B -> C, B -> D
Adding B as child of A...
A -> B relationship created: d5ee2299-f5b0-44c5-adc1-1f4b7fb9d940
Adding C as child of B...
B -> C relationship created: 836f335b-bcc2-4807-a1b9-0aa9e9c5cffc
Adding D as child of B...
B -> D relationship created: edb7e7fe-dd2c-4ac8-b7e3-58115190b55d
BOM structure created: OK
==> Test BOM tree query with depth
Full tree (depth=10): Level 1 has 1 child (B): OK
Full tree (depth=10): Level 2 has 2 children (C, D): OK
Limited tree (depth=1): Only shows B with no grandchildren: OK
==> Test cycle detection (C -> A should be 409)
Cycle detection: C -> A returned 409: OK
Cycle error type: CYCLE_DETECTED: OK
Cycle path returned: ['ac679211-df91-474a-8375-297a336160a0', 'ee25650c-b405-4a2e-99c6-fe2342b75a44', 'b28777e9-2df8-43a9-82df-8d97fe7455d1', 'ac679211-df91-474a-8375-297a336160a0']: OK
==> Test self-reference cycle (A -> A should be 409)
Self-reference cycle: A -> A returned 409: OK
==> Test duplicate add (A -> B again should fail)
Duplicate add: A -> B again returned 400: OK
==> Test remove child (B -> D)
Remove child: B -> D deleted: OK
After delete: Level 2 has 1 child (C only): OK
==> Test remove non-existent relationship
Remove non-existent: A -> D (never existed) returned 404: OK

ALL CHECKS PASSED
PASS: S3.1 (BOM Tree)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S3.2 (BOM Effectivity)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_bom_effectivity.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Date context: TODAY=2026-01-29T09:15:48Z, NEXT_WEEK=2026-02-05T09:15:48Z, LAST_WEEK=2026-01-22T09:15:48Z
==> Seed identity (admin + viewer)
Created users: admin (superuser), viewer (no write)
==> Seed meta schema
==> Login as admin
Admin login: OK
==> Configure PermissionSets
Permissions configured: OK
==> Create test parts
Created Part A (parent): acd8ecc4-04bc-4fca-8de6-1b35fdf97893
Created Part B (future child): 83a09ad4-c65d-4211-842f-2039ab6381cf
Created Part C (current child): 3a02bbc9-706f-4cbc-9a94-3baf7d0058c8
Created Part D (expired child): b5e9ad8a-210a-47d7-b759-3e4bb98689cf
==> Build BOM with effectivity dates
Adding B to A (effective from next week)...
A -> B relationship: e48588cf-e54b-47eb-b10c-9d86d413a117, effectivity_id: 0d0b1704-b9f8-42ae-9e22-40a81cacca79
Adding C to A (effective from last week, always visible now)...
A -> C relationship: 3f85944a-eccf-4eff-ba96-05edfa939149
Adding D to A (expired - ended last week)...
A -> D relationship: 1ac80d78-321b-49ee-918a-6b1f37254a7a
BOM with effectivity created: OK
==> Query effective BOM at TODAY (should only see C)
Effective BOM at TODAY: 1 child (C only): OK
==> Query effective BOM at NEXT_WEEK (should see B and C)
Effective BOM at NEXT_WEEK: 2 children (B and C): OK
==> Query effective BOM at LAST_WEEK (should see C and D)
Effective BOM at LAST_WEEK: 2 children (C and D): OK
==> RBAC: Viewer cannot add BOM children (should be 403)
Viewer login: OK
Viewer add BOM child: BLOCKED (403) - EXPECTED
==> RBAC: Viewer can read effective BOM (should be 200)
Viewer read effective BOM: OK (200)
==> Delete BOM line (A -> B) and verify Effectivity CASCADE
Delete A -> B relationship: OK
After delete: NEXT_WEEK shows 1 child (C only): OK

ALL CHECKS PASSED
PASS: S3.2 (BOM Effectivity)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S12 (Config Variants)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_config_variants.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ALL CHECKS PASSED
PASS: S12 (Config Variants)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S3.3 (Versions)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_versions.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==> Seed identity
Created admin user
==> Seed meta schema
==> Login as admin
Admin login: OK
==> Create versionable Part
Created Part: 7ab41bf3-7f71-4800-821b-9aee7ba13238
==> Initialize version (expecting 1.A)
Initial version: 1.A (generation=1, revision=A): OK
==> Revise version (1.A -> 1.B)
Revised version: 1.B: OK
==> Revise version again (1.B -> 1.C)
Revised version: 1.C: OK
==> Get version tree
Version tree has 3 versions (1.A, 1.B, 1.C): OK
Version tree labels: 1.A,1.B,1.C: OK
==> Get version history
Version history has 3 entries: OK
==> Test revision calculation
Letter scheme: A -> B: OK
Letter scheme: Z -> AA: OK
Number scheme: 1 -> 2: OK
==> Test revision comparison
Revision compare: A < C: OK
==> Test iteration within version
Created iteration: 1.C.1: OK
Created iteration: 1.C.2: OK
Latest iteration is 1.C.2: OK
==> Test version comparison
Version comparison (1.A vs 1.B): OK
==> Create revision scheme
Created revision scheme (number, starts at 1): OK
Revision schemes list: 28 scheme(s): OK
==> Test checkout/checkin flow
Checkout: locked by user 1: OK
Checkin: unlocked: OK

==============================================
VERSION SEMANTICS SUMMARY
==============================================
Version Label Format: {generation}.{revision}
  - Generation: 1, 2, 3, ...
  - Revision: A, B, C, ..., Z, AA, AB, ...
  - Example: 1.A, 1.B, 2.A, 2.AA

Iteration Format: {version_label}.{iteration}
  - Example: 1.A.1, 1.A.2, 1.B.1

Revision Schemes:
  - letter (default): A -> B -> ... -> Z -> AA
  - number: 1 -> 2 -> 3 -> ...
  - hybrid: A1 -> A2 -> ... -> A99 -> B1
==============================================

ALL CHECKS PASSED
PASS: S3.3 (Versions)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S4 (ECO Advanced)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_eco_advanced.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
ECO Advanced Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login (admin + viewer)
OK: Login succeeded

==> Create ECO stage (approval_roles=admin)
OK: Stage created: 84788e85-4fe4-481d-b1f7-4175aa4c44db

==> Create product + assembly
OK: Created product: dd7e8ce5-6dfa-4b5c-bee2-e111a23608df
OK: Created assembly: ac68cb83-41ee-4a9a-936d-9b4adbde62d5

==> Init product version
OK: Initial version: 0c2aa937-b0a2-4ac7-aa04-bdb9d4ff8a84

==> Build where-used link (assembly -> product)
OK: Where-used link created

==> Upload file + attach to product
OK: File attached (status=created)

==> Checkout + checkin to sync version files
OK: Version checked in after file binding
Initial version files: OK
OK: Version files synced

==> Create ECO (for product)
OK: ECO1 created: 8a1a9761-903c-4d57-b753-bd66e02266f8

==> Move ECO1 to approval stage
OK: ECO1 moved to stage

==> SLA overdue check + notify
Overdue list: OK
OK: Overdue list validated
Overdue notifications: OK
OK: Overdue notifications sent

==> Create ECO target version
OK: Target version: 3a8ae8ba-d345-43f6-ad50-b4f3d7d926cd

==> Resolve target version timestamp
OK: Target created_at: 2026-01-29T09:15:56.211533

==> ECO apply + verify version files synced to item
OK: ECO1 applied
Item files synced: OK
Target version files: OK
OK: ECO apply file sync validated

==> Add new BOM line effective from target version date
OK: Effective BOM line added

==> ECO BOM diff (expect added child)
BOM diff: OK
OK: BOM diff validated

==> ECO BOM diff (compare_mode=only_product)
BOM diff only_product: OK
OK: BOM diff compare_mode validated

==> ECO impact analysis (include files + bom diff + version diff)
Impact analysis: OK
OK: Impact analysis validated

==> ECO impact export (csv/xlsx/pdf)
Impact export files: OK
OK: Impact export validated

==> Create ECO2 for batch approvals
OK: ECO2 created/moved: 5dda8a60-cba6-483c-ad9e-fa4b76427358

==> Batch approve as admin
Batch approvals (admin): OK
OK: Admin batch approvals validated

==> Verify ECO states are approved
OK: ECO states approved

==> Batch approve as viewer (expect denied)
Batch approvals (viewer denied): OK
OK: Viewer batch approvals denied

==============================================
ECO Advanced Verification Complete
==============================================
ALL CHECKS PASSED
PASS: S4 (ECO Advanced)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S5-A (CAD Pipeline S3)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_cad_pipeline_s3.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
S3 CAD Pipeline Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity (admin user)
OK: Identity seeded

==> Seed meta schema
OK: Meta schema seeded

==> Login as admin
OK: Admin login

==> Create test STL file
OK: Created test file: /tmp/yuantus_cad_s3_test.stl

==> Upload STL via /cad/import
OK: File uploaded: abcecd7a-676c-4b92-a4a6-338965425ebd
Preview job ID: ce8eefab-c1f5-4a44-b92e-04d1e5118f88
Geometry job ID: 977602ae-304b-4bb8-ab85-58ed7dce614d

==> Run worker to process jobs
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
OK: Worker executed

==> Check job statuses
Preview job status: completed
Geometry job status: completed

==> Check file metadata
Preview URL: /api/v1/file/abcecd7a-676c-4b92-a4a6-338965425ebd/preview
Geometry URL: /api/v1/file/abcecd7a-676c-4b92-a4a6-338965425ebd/geometry
Conversion status: completed
OK: Preview path set
OK: Geometry path set

==> Test preview endpoint
OK: Preview endpoint works (HTTP 302)

==> Test geometry endpoint
OK: Geometry endpoint works (HTTP 302)

==> Check storage type
OK: S3 storage detected (302 redirect)
Testing S3 presigned URL follow (no API auth headers)...
OK: S3 presigned URL accessible (followed redirect)

==> Cleanup
OK: Cleaned up test file

==============================================
CAD Pipeline S3 Verification Complete
==============================================

Summary:
  - File upload: OK
  - Job processing: completed / completed
  - Preview endpoint: 302
  - Geometry endpoint: 302

ALL CHECKS PASSED
PASS: S5-A (CAD Pipeline S3)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S5-A (CAD 2D Preview)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_cad_preview_2d.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
CAD 2D Preview Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
CAD_ML_BASE_URL: http://localhost:8001
SAMPLE: /Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Upload CAD file (DWG/DXF)
OK: Uploaded file: 630a312a-628f-40b7-b5cc-5f317536aa5e

==> Run cad_preview job (direct)
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
OK: cad_preview executed

==> Check preview endpoint
OK: Preview endpoint HTTP 302

==> Update CAD properties
OK: CAD properties updated

==> Update CAD view state
OK: CAD view state updated

==> Update CAD review
OK: CAD review updated

==> Check CAD diff
OK: CAD diff ok

==> Check CAD history
OK: CAD history ok

==> Check CAD mesh stats (optional)
OK: CAD mesh stats ok
ALL CHECKS PASSED
PASS: S5-A (CAD 2D Preview)
SKIP: S5-A (CADGF Preview Online) (RUN_CADGF_PREVIEW_ONLINE=0)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S5-B (CAD 2D Connectors)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_cad_connectors_2d.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
CAD 2D Connectors Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Create dummy DWG/DXF files
OK: Created files: /tmp/yuantus_gstarcad_1769678166.dwg, /tmp/yuantus_zwcad_1769678166.dxf, /tmp/yuantus_haochencad_1769678166.dwg, /tmp/yuantus_zhongwang_1769678166.dxf, /tmp/yuantus_cad_auto_1769678166.dwg, /tmp/yuantus_cad_auto_zw_1769678166.dwg

==> Upload gstarcad_1769678166.dwg (GSTARCAD)
OK: Uploaded file: ca2074c2-d4c5-4a3f-aacf-05a30e619aee
Metadata OK
OK: Metadata verified (GSTARCAD)

==> Upload zwcad_1769678166.dxf (ZWCAD)
OK: Uploaded file: 76e1b6ae-984c-4779-a0a7-6e1d0bd75629
Metadata OK
OK: Metadata verified (ZWCAD)

==> Upload haochencad_1769678166.dwg (HAOCHEN)
OK: Uploaded file: c8fcef65-78ff-45d3-8d55-0e11520157b8
Metadata OK
OK: Metadata verified (HAOCHEN)

==> Upload zhongwangcad_1769678166.dxf (ZHONGWANG)
OK: Uploaded file: 92c72799-3bdd-4bd8-946f-cfbcde221227
Metadata OK
OK: Metadata verified (ZHONGWANG)

==> Upload cad_auto_1769678166.dwg (auto-detect)
OK: Uploaded file: e2709585-0c83-48e1-867c-32587cf71200
Metadata OK
OK: Metadata verified (HAOCHEN)

==> Upload cad_auto_zw_1769678166.dwg (auto-detect)
OK: Uploaded file: 7ec57c64-480a-45d0-a339-b7b0026c8953
Metadata OK
OK: Metadata verified (ZWCAD)

==> Cleanup
OK: Cleaned up temp files

==============================================
CAD 2D Connectors Verification Complete
==============================================
ALL CHECKS PASSED
PASS: S5-B (CAD 2D Connectors)
SKIP: S5-B (CAD 2D Real Connectors) (RUN_CAD_REAL_CONNECTORS_2D=0)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S5-B (CAD 3D Connectors)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_cad_connectors_3d.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
CAD 3D Connectors Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Create dummy 3D files
OK: Created files

==> Upload solidworks_part_1769678167.sldprt
OK: Uploaded file: 81d3726c-0e01-4fba-8fb6-967f0b82568b
Metadata OK
OK: Metadata verified (SOLIDWORKS)

==> Upload solidworks_asm_1769678167.sldasm
OK: Uploaded file: 8540fa31-3cf5-466d-9173-8e5f611a3e44
Metadata OK
OK: Metadata verified (SOLIDWORKS)

==> Upload nx_1769678167.prt
OK: Uploaded file: bb310ed4-b415-40b1-af04-b5ffd9d2a4af
Metadata OK
OK: Metadata verified (NX)

==> Upload creo_1769678167.prt
OK: Uploaded file: 4dc59840-3e25-4f5f-a3d0-00a372874d45
Metadata OK
OK: Metadata verified (CREO)

==> Upload catia_1769678167.catpart
OK: Uploaded file: 860e55bf-6296-4e34-a5c7-e3ef9164ba8d
Metadata OK
OK: Metadata verified (CATIA)

==> Upload inventor_1769678167.ipt
OK: Uploaded file: 1d8db6c9-5fa1-4ab6-b95d-b008266a2b4b
Metadata OK
OK: Metadata verified (INVENTOR)

==> Upload auto_1769678167.prt
OK: Uploaded file: 4a72a73f-dca8-4b74-adc9-e79570da9024
Metadata OK
OK: Metadata verified (NX)

==> Cleanup
OK: Cleaned up temp files

==============================================
CAD 3D Connectors Verification Complete
==============================================
ALL CHECKS PASSED
PASS: S5-B (CAD 3D Connectors)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S5-C (CAD Attribute Sync)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_cad_sync.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
CAD Attribute Sync Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Fetch Part ItemType properties
OK: Resolved property IDs

==> Configure CAD sync mapping
OK: CAD sync mapping configured

==> Create Part item
OK: Created Part: 05f0bccd-471b-49ec-861e-811c995d4a09

==> Upload CAD file and enqueue extract job
OK: Uploaded file: 11e4bc91-2ccd-4ebf-a735-31bff0f56939
OK: Created job: 3d9093cb-f4ad-4704-be22-fbfdf275d8f2

==> Run worker and wait for job completion
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
Worker did not complete job (status=pending). Running direct processor...
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
OK: Job completed (direct processor)

==> Verify CAD-synced properties
CAD sync mapping verified
OK: CAD sync mapping verified

==> Verify cad_extract attributes endpoint
cad_extract attributes verified
OK: cad_extract attributes verified

==> Cleanup
OK: Cleaned up temp file

==============================================
CAD Attribute Sync Verification Complete
==============================================
ALL CHECKS PASSED
PASS: S5-C (CAD Attribute Sync)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S5-C (CAD OCR Title Block)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_cad_ocr_titleblock.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
CAD OCR Title Block Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
CAD_ML_BASE_URL: http://localhost:8001
SAMPLE: /var/folders/23/dzwf05nn7nvgxc1fz30kn5gh0000gn/T/yuantus_ocr_sample_XXXXXX.zSlWvOiIAo.png
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Upload image file
OK: Uploaded file: b58b213e-e61e-47db-b424-4871b5a603b7

==> Run cad_ml_vision job (direct)
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
OK: cad_ml_vision executed

==> Fetch merged attributes
OK: Extracted OCR attributes: drawing_no
ALL CHECKS PASSED
PASS: S5-C (CAD OCR Title Block)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S5-C (CAD Filename Parsing)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_cad_filename_parse.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
CAD Filename Parsing Verification
DB: /tmp/yuantus_cad_filename_parse.db
Storage: /tmp/yuantus_cad_filename_storage
==============================================
ALL CHECKS PASSED
==============================================
CAD Filename Parsing Verification Complete
==============================================
PASS: S5-C (CAD Filename Parsing)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S5-C (CAD Attribute Normalization)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_cad_attribute_normalization.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
CAD Attribute Normalization Verification
DB: /tmp/yuantus_cad_attr_norm.db
Storage: /tmp/yuantus_cad_attr_norm_storage
==============================================
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
ALL CHECKS PASSED
==============================================
CAD Attribute Normalization Verification Complete
==============================================
PASS: S5-C (CAD Attribute Normalization)
SKIP: S5-B (CAD 2D Connector Coverage) (RUN_CAD_CONNECTOR_COVERAGE_2D=0)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S5-B (CAD Connectors Config)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_cad_connectors_config.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
CAD Connectors Config Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Reload connectors from config
OK: Reloaded connectors (custom_loaded=1)

==> Verify connector listing
OK: Connector list includes demo-cad

==> Import DEMO CAD file
OK: cad_format/connector_id resolved via config
OK: Imported file: d6711b39-620e-4e0a-ad63-c4b11fc8998d

==============================================
CAD Connectors Config Verification Complete
==============================================
ALL CHECKS PASSED
PASS: S5-B (CAD Connectors Config)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S5-C (CAD Sync Template)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_cad_sync_template.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
CAD Sync Template Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Download CAD sync template
OK: Template downloaded

==> Build update template
OK: Template updated

==> Apply template
OK: Template applied

==> Verify Part ItemType properties
OK: Property mapping verified

==============================================
CAD Sync Template Verification Complete
==============================================
ALL CHECKS PASSED
PASS: S5-C (CAD Sync Template)
SKIP: S5-C (CAD Auto Part) (RUN_CAD_AUTO_PART=0)
SKIP: S5-C (CAD Extractor Stub) (RUN_CAD_EXTRACTOR_STUB=0)
SKIP: S5-C (CAD Extractor External) (RUN_CAD_EXTRACTOR_EXTERNAL=0)
SKIP: S5-C (CAD Extractor Service) (RUN_CAD_EXTRACTOR_SERVICE=0)
SKIP: CAD Real Samples (RUN_CAD_REAL_SAMPLES=0)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: Search Index
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_search_index.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
Search Index Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Create Part item
OK: Created Part: 0db51b90-a418-4d04-aa7b-33adc856447d

==> Search by item_number
OK: Search found item by item_number

==> Update item name and re-search
OK: Search found item after update

==> Delete item and verify search removal
OK: Search removal validated

==============================================
Search Index Verification Complete
==============================================
ALL CHECKS PASSED
PASS: Search Index

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: Search Reindex
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_search_reindex.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
OK: Created Part: 97c28fae-f882-4f4b-8bc7-ee00e8ea9fc4

==> Search status
OK: Search engine: db

==> Reindex
OK: Reindex completed (indexed=2030)

==> Search by item_number
OK: Search found item after reindex

==> Cleanup
OK: Deleted item

==============================================
Search Reindex Verification Complete
==============================================
ALL CHECKS PASSED
PASS: Search Reindex

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: Search ECO
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_search_eco.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
Search ECO Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Search ECO index status
OK: Search ECO engine: db

==> Create ECO product
OK: Created ECO product: 5e99e0aa-d9c8-4acf-afe5-ad80338f64d7

==> Create ECO
OK: Created ECO: 8bd6d8a3-d7d9-40ae-851d-82f29ebc1749

==> Search ECO by name
OK: Search by name

==> Search ECO by state
OK: Search by state

==============================================
Search ECO Verification Complete
==============================================
ALL CHECKS PASSED
PASS: Search ECO

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: Reports Summary
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_reports_summary.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
OK: Created Part: 6346ae12-2bbc-41d5-bb08-4f5f21e4ac90

==> Upload file
OK: Uploaded file: 07bcb271-ed89-4525-af31-1bbf038b928f

==> Create ECO stage + ECO
OK: Created ECO: 8f8f2789-68db-4154-bcf1-06f4449b1daf

==> Create job
OK: Created job: b84d4684-5bd8-462b-b3dd-d91bf6f6adda

==> Fetch reports summary
Summary checks: OK
OK: Summary checks passed

==============================================
Reports Summary Verification Complete
==============================================
ALL CHECKS PASSED
PASS: Reports Summary

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: Audit Logs
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_audit_logs.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
PASS: Audit Logs
SKIP: S8 (Ops Monitoring) (RUN_OPS_S8=0)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S7 (Multi-Tenancy)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_multitenancy.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
PASS: S7 (Multi-Tenancy)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S7 (Tenant Provisioning)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_tenant_provisioning.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
Tenant Provisioning Verification
BASE_URL: http://127.0.0.1:7910
PLATFORM_TENANT: platform
NEW_TENANT: tenant-provision-1769678199
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
OK: Tenant created: tenant-provision-1769678199

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
PASS: S7 (Tenant Provisioning)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: Where-Used API
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_where_used.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
Where-Used API Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity (admin user)
OK: Identity seeded

==> Seed meta schema
OK: Meta schema seeded

==> Login as admin
OK: Admin login

==> Create test items for BOM hierarchy
OK: Created assembly: a60540d8-3b21-470d-9d9e-401e0eebab05
OK: Created sub-assembly: 8df4beea-782c-4920-9707-c5be28141231
OK: Created component: e6e896dd-9405-4097-8ff7-28d65601a51d
OK: Created second assembly: 5c0f273c-b6b9-4f95-b2ac-93d2c4ead60c

==> Build BOM hierarchy
OK: Added sub-assembly to assembly
OK: Added component to sub-assembly
OK: Added component to second assembly

BOM Structure:
  ASSEMBLY (a60540d8-3b21-470d-9d9e-401e0eebab05)
    └── SUB-ASSEMBLY (8df4beea-782c-4920-9707-c5be28141231)
          └── COMPONENT (e6e896dd-9405-4097-8ff7-28d65601a51d)
  ASSEMBLY2 (5c0f273c-b6b9-4f95-b2ac-93d2c4ead60c)
    └── COMPONENT (e6e896dd-9405-4097-8ff7-28d65601a51d)

==> Test Where-Used (non-recursive)
Where-used response:
  item_id: e6e896dd-9405-4097-8ff7-28d65601a51d
  count: 2
OK: Non-recursive where-used: found 2 direct parents
Parent IDs found:
  - 8df4beea-782c-4920-9707-c5be28141231
  - 5c0f273c-b6b9-4f95-b2ac-93d2c4ead60c

==> Test Where-Used (recursive)
Recursive where-used response:
  count: 3
OK: Recursive where-used: found 3 parents
Parents by level:
  Level 1: Sub-Assembly for Where-Used Test 1769678201
  Level 2: Assembly for Where-Used Test 1769678201
  Level 1: Second Assembly for Where-Used Test 1769678201

==> Test Where-Used on top-level item (no parents)
OK: Top-level item has no parents (count=0)

==> Test Where-Used on non-existent item
OK: Non-existent item returns 404 (HTTP 404)

==============================================
Where-Used API Verification Complete
==============================================

Summary:
  - BOM hierarchy creation: OK
  - Non-recursive where-used: OK (found 2 direct parents)
  - Recursive where-used: OK (found 3 total parents)
  - Top-level item (no parents): OK
  - Non-existent item handling: OK (404)

ALL CHECKS PASSED
PASS: Where-Used API

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: UI Product Detail
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_product_detail.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
Product Detail Mapping Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Create Part item
OK: Created Part: ec857cb0-057b-4c7e-b102-7d26881e274a

==> Init version
OK: Init version: f9f6b0d7-3576-4802-afe0-e6371fd022a4

==> Upload file
OK: Uploaded file: 68b7d388-0d23-43cb-9dae-30df0cfcee7c

==> Attach file to item
OK: File attached to item

==> Fetch product detail
Product detail mapping: OK

==============================================
Product Detail Mapping Verification Complete
==============================================
ALL CHECKS PASSED
PASS: UI Product Detail

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: UI Product Summary
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_product_ui.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
Product UI Aggregation Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Create Parts
OK: Created Parts: parent=81696b5d-cbc2-4e01-a387-fd20324f99db child=d7fad37b-0e5a-4570-ba7a-860680c4d1b9

==> Add BOM child
OK: Added BOM line: 849b6da8-e8b1-435c-9920-38c489a32797

==> Fetch parent product detail with BOM summary

==> Fetch child product detail with where-used summary
Product UI aggregation: OK

==============================================
Product UI Aggregation Verification Complete
==============================================
ALL CHECKS PASSED
PASS: UI Product Summary

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: UI Where-Used
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_where_used_ui.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
Where-Used UI Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Create Parts
OK: Created Parts: grand=4689bf7b-22b3-4e02-8758-0857044952ca parent=7f6e1b1a-eadd-4fd9-bd30-be90b2c86fc4 child=15eb4586-bc24-4c7b-a4ba-3582961e7da5

==> Add BOM lines
OK: Added BOM lines: parent_rel=ef612fe1-c7e7-443f-9e33-b479be9e1e87 grand_rel=47f89c3b-3912-4e8a-8294-e8e024422873

==> Where-used (recursive)
Where-used UI payload: OK

==============================================
Where-Used UI Verification Complete
==============================================
ALL CHECKS PASSED
PASS: UI Where-Used

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: UI BOM
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_bom_ui.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
BOM UI Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Create Parts
OK: Created Parts

==> Add children to BOM
OK: Added BOM children

==> Add substitute to BOM line
OK: Added substitute: ab453685-6a9a-40d0-9eaa-907bac77303f

==> Where-used

==> BOM compare (include child fields)

==> Substitutes list
BOM UI endpoints: OK

==============================================
BOM UI Verification Complete
==============================================
ALL CHECKS PASSED
PASS: UI BOM

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: UI Docs Approval
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_docs_approval.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
Docs + Approval Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Documents & Files
==============================================
Documents & Files Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Create Part
OK: Created Part: 28a9fb78-df04-4844-a5b0-66e9504cf396

==> Upload file with metadata
OK: Uploaded file: 5d311a1d-64dd-4083-9728-a8bb64d6f037

==> Verify file metadata
OK: Metadata verified

==> Upload duplicate file (checksum dedupe)
OK: Dedupe returned same file id

==> Attach file to item
OK: Attachment created

==> Verify item attachment list
OK: Attachment list verified

==> Cleanup
OK: Cleaned up temp file

==============================================
Documents & Files Verification Complete
==============================================
ALL CHECKS PASSED
OK: Documents & files verified

==> Document lifecycle
==============================================
Document Lifecycle Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Create Document
OK: Created Document: 2a2e2c32-7cf4-4032-877e-4b87475b6cde

==> Initialize version
OK: Initial version 1.A

==> Verify initial state is Draft
OK: State Draft

==> Update Document in Draft
OK: Draft update

==> Promote to Review
OK: State Review

==> Promote to Released
OK: State Released

==> Update after Release should be blocked
OK: Update blocked (409)

==> Attach file after Release should be blocked
OK: Attach blocked (409)

==> Cleanup

==============================================
Document Lifecycle Verification Complete
==============================================
ALL CHECKS PASSED
OK: Document lifecycle verified

==> Login as admin
OK: Admin login

==> Create approval stage
OK: Created stage: 926bd0c0-1b58-440b-a8e2-62fed096239e

==> Create ECO product
OK: Created product: c4699506-5e5d-4900-8121-d9541cf8999a

==> Create ECO
OK: Created ECO: e266c386-e660-4eb6-86f3-1a7a79d6ff66

==> Move ECO to approval stage
OK: Moved ECO to stage

==> Approve ECO
OK: Approved ECO: 62407ab4-01e9-42f3-a241-ab81cd2ab2d5

==> Verify ECO state and approvals
Approval flow: OK

==============================================
Docs + Approval Verification Complete
==============================================
ALL CHECKS PASSED
PASS: UI Docs Approval

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: UI Docs ECO Summary
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_docs_eco_ui.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
Docs + ECO UI Summary Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Ensure Document ItemTypes
OK: Document ItemTypes ensured

==> Create Part and Document
OK: Created Part=88caae44-d7da-4f6c-b2cd-80e454909b69 Document=f8c27715-7ca3-4fa4-942f-9c4ba3d60625

==> Link Document to Part
OK: Created Document relation

==> Create ECO stage and ECO
OK: Created ECO=c39f0029-6ca3-4d2d-8bf4-852b9ff3962f stage=630c0dbd-aa6d-4ca1-96ef-fc40a476ff08

==> Fetch product detail with document + ECO summary
Docs + ECO UI summary: OK

==============================================
Docs + ECO UI Summary Verification Complete
==============================================
ALL CHECKS PASSED
PASS: UI Docs ECO Summary

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: BOM Compare
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_bom_compare.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
BOM Compare Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Create parent items
OK: Created parents: A=982b7726-0bb5-45e8-bceb-d0fd6ce41a22, B=8f6f392e-f4eb-4c71-8d89-8f5264acbaa2

==> Create child items
OK: Created children: X=3d2f16fe-af7d-4dd5-942f-c5b13b27b77a, Y=28484f47-b288-4596-bfcc-ec8fa968cf7a, Z=10d8b0a1-bc25-436f-ad71-1ebce56b2dc6

==> Build BOM A (baseline)
OK: BOM A created

==> Build BOM B (changed + added)
OK: BOM B created

==> Create substitute for CHILD_X in BOM B
OK: Substitute added: 5be54f53-8d6f-450d-bb21-e68bc3229230

==> Compare BOM
BOM Compare: OK

==> Compare BOM (compare_mode=only_product)
BOM Compare only_product: OK

==> Compare BOM (compare_mode=num_qty)
BOM Compare num_qty: OK

==> Compare BOM (compare_mode=summarized)
BOM Compare summarized: OK

==============================================
BOM Compare Verification Complete
==============================================
ALL CHECKS PASSED
PASS: BOM Compare

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: BOM Compare Field Contract
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_bom_compare_fields.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
BOM Compare Field Contract Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Fetch BOM compare schema
BOM compare schema: OK
OK: Schema verified

==> Create Parts
OK: Created Parts: left=5cdd309e-018f-44a9-90db-0878bbf125d1 right=cb66cae5-3afb-472f-921c-2bc59a0b80e5 child=e041ca3b-2f22-49e1-b74c-6a5579ea4a34 sub=ce29cb57-5ad6-47ae-9cbc-9d03c9b49aba

==> Add BOM lines
OK: Added BOM lines: left_rel=a3defe7e-0a63-4744-824e-057152369fc6 right_rel=337ad990-8260-4cb3-916b-72d5977e3a25

==> Add substitute to left BOM line
OK: Added substitute: 44afefd8-436e-4c85-b139-9f8364a81653

==> Compare BOMs
BOM compare field contract: OK

==============================================
BOM Compare Field Contract Verification Complete
==============================================
ALL CHECKS PASSED
PASS: BOM Compare Field Contract

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: Where-Used Line Schema
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_where_used_schema.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
Where-Used Line Schema Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Fetch where-used line schema
Where-used schema: OK
OK: Schema verified
ALL CHECKS PASSED
PASS: Where-Used Line Schema

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: Baseline
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_baseline.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
Baseline Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Create parent + children
OK: Created parent=340f06ed-0b29-43ee-b3ca-b8f87b489a87 children=901796b3-a388-47ed-9b3b-21da1e6e854e,3407fe71-2d2d-4495-927e-2f833076d626

==> Build BOM (A -> B, C)
OK: BOM created

==> Create baseline
Baseline snapshot validated
OK: Baseline created: 29ec0e2e-0aff-4f24-84ca-8fe29adb3af9

==> Compare baseline vs current (expect no diffs)
No diff as expected
OK: Baseline compare (no diff)

==> Modify BOM (change qty + add new child)
OK: BOM updated

==> Compare baseline vs current (expect added + changed)
Diff validated
OK: Baseline compare (diff)

==> Create new baseline and compare baseline-to-baseline
Baseline-to-baseline diff validated
OK: Baseline2 compare

==============================================
Baseline Verification Complete
==============================================
ALL CHECKS PASSED
PASS: Baseline

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: BOM Substitutes
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_substitutes.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
BOM Substitutes Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Create parent/child/substitute items
OK: Created parent=b4d6b99e-02be-4e86-b02f-dc520b0ba4d3 child=070fb287-20d3-4d9b-a4c1-6f0e02641634 substitutes=a534e324-df84-49bf-9e16-56f65b2f6439,64413a29-e2c5-451b-89eb-b8671d69424a

==> Create BOM line (parent -> child)
OK: Created BOM line: ee961d80-4438-4507-97ae-f15ef85f35b5

==> Add substitute 1
OK: Added substitute 1: 1086480e-a225-4e00-8f93-99007c7050d2

==> List substitutes (expect 1)
OK: List count=1

==> Add substitute 2
OK: Added substitute 2: 674b5ed7-3378-4a44-9409-2767e33c1d12

==> Duplicate add (should 400)
OK: Duplicate add blocked (400)

==> Remove substitute 1
OK: Removed substitute 1

==> List substitutes (expect 1 remaining)
OK: List count=1 after delete

==============================================
BOM Substitutes Verification Complete
==============================================
ALL CHECKS PASSED
PASS: BOM Substitutes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: MBOM Convert
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_mbom_convert.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
MBOM Conversion Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Create EBOM parts
OK: Created EBOM root=3fb8f590-b4bf-46a2-9b8d-a11475c7871b child=06473df2-5990-4a7e-aeaf-ce8df66e57e2 substitute=b7f5457a-fc2f-4ef2-b524-80bff9cf41d8

==> Create EBOM BOM line
OK: EBOM BOM line: 086830a5-3e38-4491-bd42-3afa99a3ebd2

==> Add substitute to EBOM BOM line
OK: EBOM substitute relation: 1d908aca-7ce5-4f45-879d-de63b4a890a9

==> Convert EBOM -> MBOM
OK: MBOM root: ee4cee2e-200e-4856-99e0-b6749d49b309

==> Validate MBOM root via AML
OK: MBOM root AML verified

==> Validate MBOM tree endpoint
OK: MBOM tree endpoint verified

==> Validate MBOM structure in DB
MBOM structure: OK
OK: MBOM structure verified

==============================================
MBOM Conversion Verification Complete
==============================================
ALL CHECKS PASSED
PASS: MBOM Convert

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: Item Equivalents
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_equivalents.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
Equivalent Parts Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Create test parts
OK: Created parts A=28f4b5b3-946e-48c0-bdc1-98ed1e20cd12 B=82261552-9e6e-4e46-860b-515816b340a9 C=87bdda2d-8196-40f7-ac58-60d4492b10fe

==> Add equivalent A <-> B
OK: Added equivalent A-B: ccade4d3-6e10-4f14-bdea-79c0a25ff86a

==> Add equivalent A <-> C
OK: Added equivalent A-C: f3f39fef-fd3f-4be2-82ee-0301ad936c17

==> List equivalents for A (expect 2)
OK: List A count=2 with B,C

==> List equivalents for B (expect 1: A)
OK: List B count=1 with A

==> Duplicate add (B -> A, expect 400)
OK: Duplicate add blocked (400)

==> Self add (A -> A, expect 400)
OK: Self-equivalence blocked (400)

==> Remove equivalent A-B
OK: Removed equivalent A-B

==> List equivalents for B (expect 0)
OK: List B count=0

==> List equivalents for A (expect 1)
OK: List A count=1

==============================================
Equivalent Parts Verification Complete
==============================================
ALL CHECKS PASSED
PASS: Item Equivalents

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: Version-File Binding
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_version_files.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
Version-File Binding Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Login as viewer
OK: Viewer login

==> Create Part item
OK: Created Part: 012a960e-35f2-4664-9b2f-a96bd0f497aa

==> Init version
OK: Init version: 2d2cdfde-2ff1-4a1d-9407-d1416f849b09

==> Upload file
OK: Uploaded file: c7882437-04bb-4fcf-a399-753095b7bcc8

==> Attach file to version without checkout should be blocked (409)
OK: Attach to version blocked without checkout

==> Attach file to item (native_cad)
OK: File attached to item

==> Checkout version (lock files)
OK: Checked out version

==> Attach file to version (owner)
OK: Attached file to version

==> Viewer attach should be blocked (409)
OK: Attach blocked for non-owner

==> Checkin version (sync files)
OK: Checked in version

==> Verify version files
Version files synced: OK

==============================================
Version-File Binding Verification Complete
==============================================
ALL CHECKS PASSED
PASS: Version-File Binding

==============================================
REGRESSION TEST SUMMARY
==============================================

Test Suite                Result
------------------------- ------
Ops Health                PASS
Run H (Core APIs)         PASS
S2 (Documents & Files)    PASS
Document Lifecycle        PASS
Part Lifecycle            PASS
S1 (Meta + RBAC)          PASS
S7 (Quotas)               PASS
S3.1 (BOM Tree)           PASS
S3.2 (BOM Effectivity)    PASS
S12 (Config Variants)     PASS
S3.3 (Versions)           PASS
S4 (ECO Advanced)         PASS
S5-A (CAD Pipeline S3)    PASS
S5-B (CAD 2D Connectors)  PASS
S5-B (CAD 2D Real Connectors) SKIP
S5-B (CAD 2D Connector Coverage) SKIP
S5-C (CAD Attribute Sync) PASS
S5-B (CAD Connectors Config) PASS
S5-C (CAD Sync Template)  PASS
S5-C (CAD Auto Part)      SKIP
S5-C (CAD Extractor Stub) SKIP
S5-C (CAD Extractor External) SKIP
S5-C (CAD Extractor Service) SKIP
CAD Real Samples          SKIP
Search Index              PASS
Search Reindex            PASS
Search ECO                PASS
Reports Summary           PASS
Audit Logs                PASS
S8 (Ops Monitoring)       SKIP
S7 (Multi-Tenancy)        PASS
S7 (Tenant Provisioning)  PASS
Where-Used API            PASS
UI Product Detail         PASS
UI Product Summary        PASS
UI Where-Used             PASS
UI BOM                    PASS
UI Docs Approval          PASS
UI Docs ECO Summary       PASS
BOM Compare               PASS
Baseline                  PASS
BOM Substitutes           PASS
MBOM Convert              PASS
Item Equivalents          PASS
Version-File Binding      PASS

----------------------------------------------
PASS: 44  FAIL: 0  SKIP: 9
----------------------------------------------

ALL TESTS PASSED
