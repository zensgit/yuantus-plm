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
AML add: OK (part_id=42d12c4b-c73d-41fe-8d6d-38019d87dd8d)
AML get: OK
==> Search
Search: OK
==> RPC Item.create
RPC Item.create: OK (part_id=40d36a00-7623-4504-8d26-c1df8a7aef4a)
==> File upload/download
File upload: OK (file_id=732d2337-7e3e-4aa8-b531-f79495d07d65)
File metadata: OK
File download: OK (http=302->200)
==> BOM effective
BOM effective: OK
==> Plugins
Plugins list: OK
Plugins ping: OK
==> ECO full flow
ECO stage: OK (stage_id=7a80d10a-d846-41f7-af01-4c97727fa781)
ECO create: OK (eco_id=2f798da0-f6ab-489a-9025-fa2bfac28131)
ECO new-revision: OK (version_id=8a8dd47d-f449-4e3e-a758-8f9bd13e13c6)
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
OK: Created Part: 3a336afb-4df9-4a16-b246-8a47cd485947

==> Upload file with metadata
OK: Uploaded file: c20fba53-fd4f-43f5-a91c-e776e77b2d49

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
OK: Created Document: 572352a7-6a4a-49f4-bf49-b5b96ab9f9d6

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
OK: Created parent=5102d310-7cb5-4336-9671-d8370c2986fa child=3cce67fe-2975-43ce-aaf4-244d854c4f10 child2=f95e97ea-04ce-4b6f-b9b5-9932f5f15f61

==> Add BOM child in Draft
OK: BOM relationship 3d0a8d3b-3da5-4406-83b4-08d7112207e6

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
Viewer identity: OK (id=1769678200)
==> Configure PermissionSets
Created PermissionSet: ReadOnly-1769690802
ACE viewer (read-only): OK
ACE admin (full): OK
==> Assign PermissionSet to ItemTypes
Assigned permission to Part: OK
Assigned permission to Part BOM: OK
==> Admin creates Part (should succeed)
Admin AML add Part: OK (part_id=d26697ca-15e5-45e7-a9f7-d2e05b6b9b61)
Admin created child Part: OK (child_id=4a624397-eda1-48b1-9fc4-ccd55ac6d9b6)
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
Created Part A: 6f401cd4-42d9-4857-95b6-a419c200b9d3
Created Part B: cea66b52-1d97-404f-9628-d81e525dc07d
Created Part C: f6e2323b-e0e3-4d2a-b17c-213eb2159b9a
Created Part D: 83484395-6e39-43c5-b1d2-26525dfa5d23
==> Build BOM structure: A -> B -> C, B -> D
Adding B as child of A...
A -> B relationship created: 8c1515e0-10cf-4733-b79a-c96a58d78f72
Adding C as child of B...
B -> C relationship created: 715248e4-c46a-4a20-8b2d-ce337dcab262
Adding D as child of B...
B -> D relationship created: 2145bf91-83b3-4382-b868-5d4a491e9ed7
BOM structure created: OK
==> Test BOM tree query with depth
Full tree (depth=10): Level 1 has 1 child (B): OK
Full tree (depth=10): Level 2 has 2 children (C, D): OK
Limited tree (depth=1): Only shows B with no grandchildren: OK
==> Test cycle detection (C -> A should be 409)
Cycle detection: C -> A returned 409: OK
Cycle error type: CYCLE_DETECTED: OK
Cycle path returned: ['f6e2323b-e0e3-4d2a-b17c-213eb2159b9a', '6f401cd4-42d9-4857-95b6-a419c200b9d3', 'cea66b52-1d97-404f-9628-d81e525dc07d', 'f6e2323b-e0e3-4d2a-b17c-213eb2159b9a']: OK
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
Date context: TODAY=2026-01-29T12:46:47Z, NEXT_WEEK=2026-02-05T12:46:47Z, LAST_WEEK=2026-01-22T12:46:47Z
==> Seed identity (admin + viewer)
Created users: admin (superuser), viewer (no write)
==> Seed meta schema
==> Login as admin
Admin login: OK
==> Configure PermissionSets
Permissions configured: OK
==> Create test parts
Created Part A (parent): a5feeaa1-2e2c-473e-8995-008592f7c85c
Created Part B (future child): 803f2fdb-f9b9-419b-bc92-e1b2e17f216e
Created Part C (current child): af29e9e2-bf30-4ec9-9d78-0c095c7aec80
Created Part D (expired child): 7343bf58-ad14-458e-aa12-4940bd57f221
==> Build BOM with effectivity dates
Adding B to A (effective from next week)...
A -> B relationship: ceb38412-d3ad-49c6-a93d-a5694be0261d, effectivity_id: 494a85e5-406f-4a06-bef3-5390693dd8ae
Adding C to A (effective from last week, always visible now)...
A -> C relationship: 51971599-f06f-4a0d-b216-a8e717fba374
Adding D to A (expired - ended last week)...
A -> D relationship: 1390773d-b5ce-4cce-953a-087c5236a957
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
Created Part: da485ddb-5254-4908-b816-645c0db36e4c
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
Revision schemes list: 29 scheme(s): OK
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
OK: Stage created: 0ac0c998-1671-45d4-bfbe-ab0504e10752

==> Create product + assembly
OK: Created product: 07bcc9b9-79e7-41a0-ba92-258eed56770c
OK: Created assembly: 945e3369-406e-48cf-899a-8ad547f6eb75

==> Init product version
OK: Initial version: 19c2f7a9-0d8f-4ff5-ad88-e6be84340701

==> Build where-used link (assembly -> product)
OK: Where-used link created

==> Upload file + attach to product
OK: File attached (status=created)

==> Checkout + checkin to sync version files
OK: Version checked in after file binding
Initial version files: OK
OK: Version files synced

==> Create ECO (for product)
OK: ECO1 created: bfb6238d-d3f8-4d75-8e28-998fc3a8ddbe

==> Move ECO1 to approval stage
OK: ECO1 moved to stage

==> SLA overdue check + notify
Overdue list: OK
OK: Overdue list validated
Overdue notifications: OK
OK: Overdue notifications sent

==> Create ECO target version
OK: Target version: 90d08a43-51b3-469d-bf18-585213cc6949

==> Resolve target version timestamp
OK: Target created_at: 2026-01-29T12:46:55.527118

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
OK: ECO2 created/moved: 0e34a354-1b95-4890-b57e-d4ea705d270d

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
Preview job ID: 6d219de2-7f01-4a5f-b762-4d5ec74438fc
Geometry job ID: a5ae1bdd-a823-4ad4-9799-39ed01576a0b

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
OK: Created files: /tmp/yuantus_gstarcad_1769690827.dwg, /tmp/yuantus_zwcad_1769690827.dxf, /tmp/yuantus_haochencad_1769690827.dwg, /tmp/yuantus_zhongwang_1769690827.dxf, /tmp/yuantus_cad_auto_1769690827.dwg, /tmp/yuantus_cad_auto_zw_1769690827.dwg

==> Upload gstarcad_1769690827.dwg (GSTARCAD)
OK: Uploaded file: 9db08430-c3dc-43f6-99f2-99d4ef77ca01
Metadata OK
OK: Metadata verified (GSTARCAD)

==> Upload zwcad_1769690827.dxf (ZWCAD)
OK: Uploaded file: 732a4c58-5f91-40fc-97a7-d895deced202
Metadata OK
OK: Metadata verified (ZWCAD)

==> Upload haochencad_1769690827.dwg (HAOCHEN)
OK: Uploaded file: 009310cb-9928-4ad6-9503-6cfc77a90050
Metadata OK
OK: Metadata verified (HAOCHEN)

==> Upload zhongwangcad_1769690827.dxf (ZHONGWANG)
OK: Uploaded file: a5d565c7-b2eb-40a3-84f3-27364e84e77f
Metadata OK
OK: Metadata verified (ZHONGWANG)

==> Upload cad_auto_1769690827.dwg (auto-detect)
OK: Uploaded file: 43df7a1e-1822-493f-8a77-510475aed17c
Metadata OK
OK: Metadata verified (HAOCHEN)

==> Upload cad_auto_zw_1769690827.dwg (auto-detect)
OK: Uploaded file: e2bc68a5-46e0-43f5-bf3b-ff27b5482d63
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

==> Upload solidworks_part_1769690829.sldprt
OK: Uploaded file: bd25f288-11ed-4c74-bf2f-4b5c64ac4155
Metadata OK
OK: Metadata verified (SOLIDWORKS)

==> Upload solidworks_asm_1769690829.sldasm
OK: Uploaded file: f1b4e92d-c86c-4b44-9603-07f9775c8415
Metadata OK
OK: Metadata verified (SOLIDWORKS)

==> Upload nx_1769690829.prt
OK: Uploaded file: 1120af0f-715f-42ab-97c1-2a805c1b1d88
Metadata OK
OK: Metadata verified (NX)

==> Upload creo_1769690829.prt
OK: Uploaded file: 5826cc6f-e84c-4abc-95b4-3d8c30c1bdae
Metadata OK
OK: Metadata verified (CREO)

==> Upload catia_1769690829.catpart
OK: Uploaded file: 7cdd1e8b-bb15-4860-ab2c-dcffb99247f5
Metadata OK
OK: Metadata verified (CATIA)

==> Upload inventor_1769690829.ipt
OK: Uploaded file: 3d63f398-3bcd-4a74-90e2-46dfd71c570a
Metadata OK
OK: Metadata verified (INVENTOR)

==> Upload auto_1769690829.prt
OK: Uploaded file: f2ea126b-4305-487e-98d9-fec47e056fb1
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
OK: Created Part: 82c84061-e66a-49db-96d2-9a0aab1fd32b

==> Upload CAD file and enqueue extract job
OK: Uploaded file: 1561afb7-6c30-4be6-8e8f-a0b31a4c3045
OK: Created job: 395ff4da-f5cd-4303-9228-4af96406d558

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
SAMPLE: /var/folders/23/dzwf05nn7nvgxc1fz30kn5gh0000gn/T/yuantus_ocr_sample_XXXXXX.8ApPXptFo1.png
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
OK: Created Part: a6218385-3dfd-4257-9ea2-d12f50e04382

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
OK: Created Part: 95c6b0b5-3d24-44fc-a75f-e057e65c78fc

==> Search status
OK: Search engine: db

==> Reindex
OK: Reindex completed (indexed=2109)

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
OK: Created ECO product: 9120b5ef-a8fc-44e8-b169-1bf3634b391e

==> Create ECO
OK: Created ECO: f3b20afb-651f-457a-af38-28491be95767

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
OK: Created Part: 2977675b-2df6-446b-a4cb-88933eda60c0

==> Upload file
OK: Uploaded file: 1c02146a-6605-41b6-a22f-b182ee26d975

==> Create ECO stage + ECO
OK: Created ECO: 5ad5326b-50f6-441d-a916-2f3719325e6c

==> Create job
OK: Created job: 88e548e9-db2b-48a1-9d97-5f466342d07c

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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S8 (Ops Monitoring)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_ops_s8.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
OK: Created Part: c1e3b3e2-26f1-4ff1-9caa-72940505d35f

==> Upload file
OK: Uploaded file: b7af1f72-3100-4a68-9253-35829a202afa

==> Create ECO stage + ECO
OK: Created ECO: 6f5d7721-9f07-4ccf-b9d3-ce5044a9c728

==> Create job
OK: Created job: ef18eafe-edd2-4117-90b0-67aa7ce76bfe

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
PASS: S8 (Ops Monitoring)

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
NEW_TENANT: tenant-provision-1769690867
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
OK: Tenant created: tenant-provision-1769690867

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
OK: Created assembly: fe5d6623-dc51-44ac-b312-5fe411783a7a
OK: Created sub-assembly: 74f912f9-9c73-45e3-bfc9-bfcbe1f80a0e
OK: Created component: 79c98609-03a5-491f-be78-1f38cb375437
OK: Created second assembly: ab004391-07d2-4a9b-8557-1b0ea14b8c22

==> Build BOM hierarchy
OK: Added sub-assembly to assembly
OK: Added component to sub-assembly
OK: Added component to second assembly

BOM Structure:
  ASSEMBLY (fe5d6623-dc51-44ac-b312-5fe411783a7a)
    └── SUB-ASSEMBLY (74f912f9-9c73-45e3-bfc9-bfcbe1f80a0e)
          └── COMPONENT (79c98609-03a5-491f-be78-1f38cb375437)
  ASSEMBLY2 (ab004391-07d2-4a9b-8557-1b0ea14b8c22)
    └── COMPONENT (79c98609-03a5-491f-be78-1f38cb375437)

==> Test Where-Used (non-recursive)
Where-used response:
  item_id: 79c98609-03a5-491f-be78-1f38cb375437
  count: 2
OK: Non-recursive where-used: found 2 direct parents
Parent IDs found:
  - 74f912f9-9c73-45e3-bfc9-bfcbe1f80a0e
  - ab004391-07d2-4a9b-8557-1b0ea14b8c22

==> Test Where-Used (recursive)
Recursive where-used response:
  count: 3
OK: Recursive where-used: found 3 parents
Parents by level:
  Level 1: Sub-Assembly for Where-Used Test 1769690869
  Level 2: Assembly for Where-Used Test 1769690869
  Level 1: Second Assembly for Where-Used Test 1769690869

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
OK: Created Part: c88532b5-9740-49f6-a278-b4fd164faab4

==> Init version
OK: Init version: db542772-773c-4f1d-8573-a1936a209600

==> Upload file
OK: Uploaded file: e62ebf50-dc5e-43ff-9f4e-51c3935a30e1

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
OK: Created Parts: parent=6e37d9b4-353b-45e7-9cc3-9a830b3fc6a1 child=9eed1fcf-ca11-4f01-bb7c-6b29593e0434

==> Add BOM child
OK: Added BOM line: f1da25b3-7e7f-4bb4-b44b-f0cb5e91da84

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
OK: Created Parts: grand=9cc1bd47-2784-437a-ba57-e98994228377 parent=d9b9fed8-c62b-4c91-80db-743815c3b792 child=74cef0b6-e9be-4154-96b7-808a2a086aaa

==> Add BOM lines
OK: Added BOM lines: parent_rel=bbe02928-1536-47ea-b368-01f1c8fdc4f8 grand_rel=8270dccd-7e61-45d4-8cd8-b2f034d0f9f3

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
OK: Added substitute: c0efb02d-aa7b-496a-9fbe-6adc6804806e

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
OK: Created Part: f4771888-0c87-4650-ba81-e46a740ced1d

==> Upload file with metadata
OK: Uploaded file: e0fe4ab6-939b-445c-949f-04a9becb2279

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
OK: Created Document: 245896b3-9f24-4e4f-973e-3d0050cf7902

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
OK: Created stage: d96776ee-f92f-408d-b3fb-1e426632e2d5

==> Create ECO product
OK: Created product: f962ddb3-c1e7-4979-af78-92a835ff53e2

==> Create ECO
OK: Created ECO: 546dda08-3f76-4263-90bb-5b368f24aa6f

==> Move ECO to approval stage
OK: Moved ECO to stage

==> Approve ECO
OK: Approved ECO: 6f49f6ea-f506-42cb-b187-939b4bdbb4a6

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
OK: Created Part=7d612342-3009-4f86-b3b3-34b7e2d1fdd9 Document=17e03b99-fffe-453b-b4a7-d7988830105e

==> Link Document to Part
OK: Created Document relation

==> Create ECO stage and ECO
OK: Created ECO=83bd6977-c6ba-4028-a6c4-155555c902cd stage=df64e3c9-5bfe-4690-a5b5-584e35709b17

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
OK: Created parents: A=0ff505ef-3e14-4544-9659-c30912343ab2, B=40d002b4-04ce-40cf-a045-444ac70e680e

==> Create child items
OK: Created children: X=781144e4-074f-4c2e-8307-c309a5bcb2cf, Y=b3ab983b-9e2c-40d2-afe3-9c5c8996becc, Z=8522bf56-59e4-4ff2-a8e7-1968c0eccf1f

==> Build BOM A (baseline)
OK: BOM A created

==> Build BOM B (changed + added)
OK: BOM B created

==> Create substitute for CHILD_X in BOM B
OK: Substitute added: eed96214-860c-4574-a302-0b797249ed91

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
OK: Created Parts: left=9c9240a1-f8a2-4054-8673-df06569ae22a right=c0b209d6-d281-42eb-b0d6-185e3670a797 child=dd07d216-f6cd-4dde-afdc-3c36b04e2211 sub=7a131920-a6d6-48b1-9058-db23b1237773

==> Add BOM lines
OK: Added BOM lines: left_rel=a994dfea-8f4c-4656-99f7-1bf2800e5aba right_rel=103aea30-a3c9-4f76-a4a5-db1bf272f743

==> Add substitute to left BOM line
OK: Added substitute: 21e24b8d-22d8-4125-aab4-b5f1d9a6b3be

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
OK: Created parent=3f310977-7c4b-46fd-85d4-3d5cd5919c66 children=0adc9f99-d120-4496-a429-2a893b9cf49b,014cd13b-0f25-4a0b-b4a5-647199902619

==> Build BOM (A -> B, C)
OK: BOM created

==> Create baseline
Baseline snapshot validated
OK: Baseline created: ff490331-bd71-4f66-a591-e54de8f08ca9

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
OK: Created parent=3b6c1fc5-704c-40b3-a306-269714d282aa child=7001c05b-d302-44df-aaa7-2a9c79b4aa33 substitutes=3c618bd5-9a06-47b6-9227-b824d8f3f26d,23bdbfa9-ca60-44f6-bf7a-50a253db0601

==> Create BOM line (parent -> child)
OK: Created BOM line: 44520952-09e7-464b-8e34-1981706786e1

==> Add substitute 1
OK: Added substitute 1: 8d4c200c-e588-41cf-9516-a7d79ece5aef

==> List substitutes (expect 1)
OK: List count=1

==> Add substitute 2
OK: Added substitute 2: 70d031fd-c1e9-4e20-bfc2-464dc0d86e41

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
OK: Created EBOM root=3e32bacc-c35c-41f2-9c28-742d521cd7cb child=bffb9634-8f24-4190-a768-1e465ac7243e substitute=2b9312eb-dc5f-407c-bced-875157a5c01e

==> Create EBOM BOM line
OK: EBOM BOM line: 761ac201-8ea1-436a-9255-6f95d86ebf46

==> Add substitute to EBOM BOM line
OK: EBOM substitute relation: ee79dc8e-9ed0-4c0f-b9ce-824958ddabbf

==> Convert EBOM -> MBOM
OK: MBOM root: 68db098e-f7c6-4d8c-9cd3-db5394469a2c

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
OK: Created parts A=85eac8ea-b6ab-4e0d-9102-a02ebaa51fc3 B=6ff5ce02-ff5c-42af-b0bf-9504858c3e80 C=373c7123-a8cb-4fdc-bf87-902ba580a93b

==> Add equivalent A <-> B
OK: Added equivalent A-B: 6e99fb33-fb71-4506-bf46-134288943baf

==> Add equivalent A <-> C
OK: Added equivalent A-C: ec127c88-c44e-47f8-b0e1-46affd36c947

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
OK: Created Part: 93b8e59c-138e-42e6-ab9b-1cc712b8e5ba

==> Init version
OK: Init version: 56276ca0-f2af-4463-aae0-bae4d205de9f

==> Upload file
OK: Uploaded file: 8d079c98-bac2-4c86-be7e-12b9df5f7abd

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
S8 (Ops Monitoring)       PASS
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
PASS: 45  FAIL: 0  SKIP: 8
----------------------------------------------

ALL TESTS PASSED
