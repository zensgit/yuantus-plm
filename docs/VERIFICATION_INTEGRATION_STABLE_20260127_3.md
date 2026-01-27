==============================================
Integration Stability Runner
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
CAD_EXTRACTOR_BASE_URL: http://localhost:8200
CAD_CONNECTOR_BASE_URL: http://localhost:8300
CAD_CONNECTOR_COVERAGE_DIR: /Users/huazhou/Downloads/训练图纸/训练图纸
CAD_SAMPLE_DWG: /Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg
CAD_SAMPLE_STEP: /Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/CNC.stp
CAD_SAMPLE_PRT: /Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/model2.prt
YUANTUS_CADGF_ROUTER_BASE_URL: http://127.0.0.1:9000
==============================================
Enabled: RUN_UI_AGG RUN_TENANT_PROVISIONING RUN_OPS_S8 RUN_CAD_EXTRACTOR_STUB RUN_CAD_AUTO_PART RUN_CAD_REAL_CONNECTORS_2D RUN_CAD_CONNECTOR_COVERAGE_2D RUN_CAD_EXTRACTOR_EXTERNAL RUN_CAD_EXTRACTOR_SERVICE RUN_CAD_REAL_SAMPLES RUN_CADGF_PREVIEW_ONLINE
==============================================

==============================================
YuantusPLM End-to-End Regression Suite
==============================================
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
CLI: .venv/bin/yuantus
DB_URL: postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus
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
AML add: OK (part_id=8210da46-70de-4c54-96b6-c778c2ac116b)
AML get: OK
==> Search
Search: OK
==> RPC Item.create
RPC Item.create: OK (part_id=1a97112d-da4e-4349-b96b-c085e168ecec)
==> File upload/download
File upload: OK (file_id=62e84454-65f6-41c9-ad60-ad27e2e1725f)
File metadata: OK
File download: OK (http=302->200)
==> BOM effective
BOM effective: OK
==> Plugins
Plugins list: OK
Plugins ping: OK
==> ECO full flow
ECO stage: OK (stage_id=ef35844f-eff4-4e12-baac-debc018515e8)
ECO create: OK (eco_id=65645337-f47f-4983-a606-adf40e0f42c2)
ECO new-revision: OK (version_id=86125fd2-961a-42d3-ab6b-065ce094f1ed)
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
OK: Created Part: e03300c2-a85f-4436-8006-8c6b37d7546a

==> Upload file with metadata
OK: Uploaded file: 3816e5fe-dedf-4853-9cee-1242168af504

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
OK: Created Document: 4895b367-d7d5-4344-b27d-f079a6a17e72

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
OK: Created parent=81533ab0-645f-4165-adda-2a75d8ad2ee4 child=b00b6f0c-5f90-461c-bfd2-d88ce64f5682 child2=99479fa0-2a64-4294-adf2-c91607d8d8ff

==> Add BOM child in Draft
OK: BOM relationship ca5bb871-6aec-47c7-aeac-c5627609c2d4

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
Viewer identity: OK (id=1769506794)
==> Configure PermissionSets
Created PermissionSet: ReadOnly-1769509034
ACE viewer (read-only): OK
ACE admin (full): OK
==> Assign PermissionSet to ItemTypes
Assigned permission to Part: OK
Assigned permission to Part BOM: OK
==> Admin creates Part (should succeed)
Admin AML add Part: OK (part_id=5c452400-d639-4f52-bd2c-dd6eaae25712)
Admin created child Part: OK (child_id=9821099f-16e4-43d4-9ae1-bc8deacd6073)
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
Created Part A: 91dc1fc3-95f3-4d6c-b94a-5f3adcd4b419
Created Part B: 068ad0a2-d56f-4163-8104-299584c848ac
Created Part C: 56b982e4-16d0-441e-bdbf-3ecfc696efcb
Created Part D: 9c39aa2f-edf4-432b-a234-6cc4d9fa8e54
==> Build BOM structure: A -> B -> C, B -> D
Adding B as child of A...
A -> B relationship created: dd063032-94ad-4001-8213-cb8911f41b14
Adding C as child of B...
B -> C relationship created: 04e9d87a-4ea6-4d5d-8321-eb67dba55ac8
Adding D as child of B...
B -> D relationship created: d828ccbe-5d63-4809-84b8-f8de6568d20b
BOM structure created: OK
==> Test BOM tree query with depth
Full tree (depth=10): Level 1 has 1 child (B): OK
Full tree (depth=10): Level 2 has 2 children (C, D): OK
Limited tree (depth=1): Only shows B with no grandchildren: OK
==> Test cycle detection (C -> A should be 409)
Cycle detection: C -> A returned 409: OK
Cycle error type: CYCLE_DETECTED: OK
Cycle path returned: ['56b982e4-16d0-441e-bdbf-3ecfc696efcb', '91dc1fc3-95f3-4d6c-b94a-5f3adcd4b419', '068ad0a2-d56f-4163-8104-299584c848ac', '56b982e4-16d0-441e-bdbf-3ecfc696efcb']: OK
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
Date context: TODAY=2026-01-27T10:17:18Z, NEXT_WEEK=2026-02-03T10:17:18Z, LAST_WEEK=2026-01-20T10:17:18Z
==> Seed identity (admin + viewer)
Created users: admin (superuser), viewer (no write)
==> Seed meta schema
==> Login as admin
Admin login: OK
==> Configure PermissionSets
Permissions configured: OK
==> Create test parts
Created Part A (parent): 44316ce0-fb96-430c-92db-2999bff1e102
Created Part B (future child): 71df4e52-df9f-424c-beee-2f020869f588
Created Part C (current child): c591fb8c-ec06-4651-aa37-60fe631bb9c3
Created Part D (expired child): af209a1e-bd30-4cb0-919c-cb881e016ccb
==> Build BOM with effectivity dates
Adding B to A (effective from next week)...
A -> B relationship: 2d84efe0-c799-4b5f-8927-5d608fe95e36, effectivity_id: 7fc23ec2-8049-46e9-808c-3c69d70e9271
Adding C to A (effective from last week, always visible now)...
A -> C relationship: 002121de-5cf0-48ce-8e02-6b9e8dac2acb
Adding D to A (expired - ended last week)...
A -> D relationship: 1cddd159-8993-40ff-b151-2722ccf044eb
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
Running: S3.3 (Versions)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_versions.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==> Seed identity
Created admin user
==> Seed meta schema
==> Login as admin
Admin login: OK
==> Create versionable Part
Created Part: b713a92c-a4d9-475a-bcef-238d07a9a6b2
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
Revision schemes list: 17 scheme(s): OK
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
OK: Stage created: 4c81a7b8-3eef-4a63-b192-fa40f30dba59

==> Create product + assembly
OK: Created product: fe29c690-6007-4692-b930-1b37de2abab6
OK: Created assembly: 6aec7de7-d2b8-4076-9744-6d07ae6dae57

==> Init product version
OK: Initial version: bff0834c-c395-465f-b301-103fa3f5f379

==> Build where-used link (assembly -> product)
OK: Where-used link created

==> Upload file + attach to product
OK: File attached (status=created)

==> Checkout + checkin to sync version files
OK: Version checked in after file binding
Initial version files: OK
OK: Version files synced

==> Create ECO (for product)
OK: ECO1 created: 26cbfc0f-773c-4ba6-afd6-08add595dac7

==> Move ECO1 to approval stage
OK: ECO1 moved to stage

==> SLA overdue check + notify
Overdue list: OK
OK: Overdue list validated
Overdue notifications: OK
OK: Overdue notifications sent

==> Create ECO target version
OK: Target version: 1e7e4c52-c30c-4563-91fa-088ac193b127

==> Resolve target version timestamp
OK: Target created_at: 2026-01-27T10:17:24.053803

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
OK: ECO2 created/moved: 1f0de19d-f041-49f9-89c5-a428c9b4a946

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
Preview job ID: a55c8c49-be56-4a5f-afe7-d7cc87b0e5c3
Geometry job ID: 07533900-147f-4213-b00c-37c035cf6a79

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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S5-A (CADGF Preview Online)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_cad_preview_online.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
report: /tmp/cadgf_preview_online_report.md
PASS: S5-A (CADGF Preview Online)

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
OK: Created files: /tmp/yuantus_gstarcad_1769509054.dwg, /tmp/yuantus_zwcad_1769509054.dxf, /tmp/yuantus_haochencad_1769509054.dwg, /tmp/yuantus_zhongwang_1769509054.dxf, /tmp/yuantus_cad_auto_1769509054.dwg, /tmp/yuantus_cad_auto_zw_1769509054.dwg

==> Upload gstarcad_1769509054.dwg (GSTARCAD)
OK: Uploaded file: 1d54828a-7be1-4834-bba8-55e49f745738
Metadata OK
OK: Metadata verified (GSTARCAD)

==> Upload zwcad_1769509054.dxf (ZWCAD)
OK: Uploaded file: 90491e91-1e4a-4d20-912b-40d1b47e7225
Metadata OK
OK: Metadata verified (ZWCAD)

==> Upload haochencad_1769509054.dwg (HAOCHEN)
OK: Uploaded file: d9b9da21-ecf0-48d5-9428-863785032b34
Metadata OK
OK: Metadata verified (HAOCHEN)

==> Upload zhongwangcad_1769509054.dxf (ZHONGWANG)
OK: Uploaded file: 43957e2c-435f-470f-b878-f6fc441a1e83
Metadata OK
OK: Metadata verified (ZHONGWANG)

==> Upload cad_auto_1769509054.dwg (auto-detect)
OK: Uploaded file: 3b4776ab-ba90-4b8b-bf6a-d4db7ac46786
Metadata OK
OK: Metadata verified (HAOCHEN)

==> Upload cad_auto_zw_1769509054.dwg (auto-detect)
OK: Uploaded file: 79c4c656-96c3-4cec-9100-24a92f2044ec
Metadata OK
OK: Metadata verified (ZWCAD)

==> Cleanup
OK: Cleaned up temp files

==============================================
CAD 2D Connectors Verification Complete
==============================================
ALL CHECKS PASSED
PASS: S5-B (CAD 2D Connectors)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S5-B (CAD 2D Real Connectors)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_cad_connectors_real_2d.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
CAD 2D Real Connectors Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
HAOCHEN: /Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg
ZHONGWANG: /Users/huazhou/Downloads/训练图纸/训练图纸/J2825002-09下轴承支架组件v2.dwg
CAD_EXTRACTOR_BASE_URL: http://localhost:8200
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> [HAOCHEN] Upload + cad_extract
OK: HAOCHEN uploaded (file_id=8d35dc0a-d339-41ef-8b37-6fe6733daa65, job_id=93b293fa-94f7-468e-bf98-bf06f4622e3f)
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
Worker did not complete job (status=pending). Running direct processor...
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
Metadata OK
OK: HAOCHEN metadata verified
Attributes OK
OK: HAOCHEN attributes verified (part_number=J2824002-06)

==> [ZHONGWANG] Upload + cad_extract
OK: ZHONGWANG uploaded (file_id=56e33d28-2cec-4242-83e5-340898b23f47, job_id=a4c21824-7373-4376-b131-407c1f7abae0)
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
OK: Job completed
Metadata OK
OK: ZHONGWANG metadata verified
Attributes OK
OK: ZHONGWANG attributes verified (part_number=J2825002-09)

==============================================
CAD 2D Real Connectors Verification Complete
==============================================
ALL CHECKS PASSED
PASS: S5-B (CAD 2D Real Connectors)

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

==> Upload solidworks_part_1769509068.sldprt
OK: Uploaded file: 6c868d7f-7799-4554-a245-e6441068ff3f
Metadata OK
OK: Metadata verified (SOLIDWORKS)

==> Upload solidworks_asm_1769509068.sldasm
OK: Uploaded file: 1f9d81bf-e9af-491d-9ba6-08be9ee9f03c
Metadata OK
OK: Metadata verified (SOLIDWORKS)

==> Upload nx_1769509068.prt
OK: Uploaded file: eff5f27b-3c9c-4681-bb95-4b9f3502e153
Metadata OK
OK: Metadata verified (NX)

==> Upload creo_1769509068.prt
OK: Uploaded file: 6f875ecd-d241-403d-80be-796f084f2430
Metadata OK
OK: Metadata verified (CREO)

==> Upload catia_1769509068.catpart
OK: Uploaded file: c8353765-c13f-4aa4-bf96-a3e52b4e8e34
Metadata OK
OK: Metadata verified (CATIA)

==> Upload inventor_1769509068.ipt
OK: Uploaded file: 20a687d9-d68c-4c37-b761-c2bd4696a6d4
Metadata OK
OK: Metadata verified (INVENTOR)

==> Upload auto_1769509068.prt
OK: Uploaded file: 8274e798-c4bc-4bc4-885e-7677766d7a72
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
OK: Created Part: 20bfe720-c0f4-44c5-af6b-fab55d709a2b

==> Upload CAD file and enqueue extract job
OK: Uploaded file: 06c4488d-156c-420d-aab6-46231af71380
OK: Created job: 7480d426-b864-49c1-bf31-504a58de8f99

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
SAMPLE: /var/folders/23/dzwf05nn7nvgxc1fz30kn5gh0000gn/T/yuantus_ocr_sample_XXXXXX.OauWpuDnSr.png
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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S5-B (CAD 2D Connector Coverage)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_cad_connector_coverage_2d.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
CAD 2D Connector Coverage (offline)
Dir: /Users/huazhou/Downloads/训练图纸/训练图纸
Extensions: dwg
Max files: 0
Force unique: 0
==============================================
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
==============================================
CAD 2D Connector Coverage Complete
Haochen: /Users/huazhou/Downloads/Github/Yuantus/docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_HAOCHEN.md
Zhongwang: /Users/huazhou/Downloads/Github/Yuantus/docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_ZHONGWANG.md
==============================================
PASS: S5-B (CAD 2D Connector Coverage)

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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S5-C (CAD Auto Part)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_cad_auto_part.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
CAD Auto Part Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
SAMPLE: /tmp/yuantus_cad_auto_part_1769509088.dwg
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Fetch Part ItemType properties
OK: Resolved property IDs

==> Import CAD with auto_create_part
OK: Created/linked Part: 3981408d-09c1-4f0f-9472-2ba4d2a18a3a
OK: Imported File: 4fff0152-7360-4677-8339-e7e7d4ded58c
OK: Attachment created: 5e118dd4-8f94-45a1-96db-81f94a6e7b01

==> Verify Part properties
Part properties verified
OK: Part properties verified

==> Verify attachment list
Attachment verified
OK: Attachment verified

==> Cleanup
OK: Cleaned up temp file

==============================================
CAD Auto Part Verification Complete
==============================================
ALL CHECKS PASSED
PASS: S5-C (CAD Auto Part)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S5-C (CAD Extractor Stub)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_cad_extractor_stub.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
CAD Extractor Stub Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
EXTRACTOR: http://127.0.0.1:61488
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Upload CAD file and enqueue extract job
OK: Uploaded file: 75baae76-5941-4489-a69e-c77a0c70eb06
OK: Created job: e93021c1-32dc-468b-ba71-e94d9f961b19

==> Process cad_extract job (direct)
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
OK: Job completed

==> Verify extracted attributes source=external
OK: External extractor verified

==============================================
CAD Extractor Stub Verification Complete
==============================================
ALL CHECKS PASSED
PASS: S5-C (CAD Extractor Stub)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S5-C (CAD Extractor External)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_cad_extractor_external.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
CAD Extractor External Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
EXTRACTOR: http://localhost:8200
SAMPLE: /Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Upload CAD file and enqueue extract job
OK: Uploaded file: 630a312a-628f-40b7-b5cc-5f317536aa5e
OK: Created job: 01eea427-bb7c-4735-b0ee-86c8b81bdfdc

==> Process cad_extract job (direct)
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
OK: Job completed

==> Verify extracted attributes source=external
OK: External extractor verified

==============================================
CAD Extractor External Verification Complete
==============================================
ALL CHECKS PASSED
PASS: S5-C (CAD Extractor External)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S5-C (CAD Extractor Service)
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_cad_extractor_service.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
CAD Extractor Service Verification
BASE_URL: http://localhost:8200
START_SERVICE: 0
==============================================
OK: Health check
OK: Extract response

==============================================
CAD Extractor Service Verification Complete
==============================================
ALL CHECKS PASSED
PASS: S5-C (CAD Extractor Service)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: CAD Real Samples
Script: /Users/huazhou/Downloads/Github/Yuantus/scripts/verify_cad_real_samples.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
==============================================
CAD Real Samples Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
DWG: /Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg
STEP: /Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/CNC.stp
PRT: /Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/model2.prt
CAD_EXTRACTOR_BASE_URL: http://localhost:8200
==============================================
OK: Seeded identity/meta
OK: Admin login

==> [DWG] Import + auto_create_part
OK: DWG imported (file_id=630a312a-628f-40b7-b5cc-5f317536aa5e, item_id=b9e86fee-4237-4b3a-a707-659008e44ead)
==> [DWG] Run cad_extract
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
OK: DWG cad_extract OK
==> [DWG] Run cad_preview
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
OK: DWG cad_preview OK
==> [DWG] Verify preview endpoint
OK: DWG preview endpoint HTTP 302
==> [DWG] Verify extracted attributes
OK: DWG attributes OK
==> [DWG] Verify auto-created Part
OK: DWG Part properties OK (item_number=J2824002-06)

==> [STEP] Import + auto_create_part
OK: STEP imported (file_id=fe94aaec-ddab-4bfd-af5f-5f991056bad1, item_id=e2319abc-d882-48ff-a84b-41d3da8afd79)
==> [STEP] Run cad_extract
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
OK: STEP cad_extract OK
==> [STEP] Run cad_preview
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
OK: STEP cad_preview OK
==> [STEP] Verify preview endpoint
OK: STEP preview endpoint HTTP 302
==> [STEP] Verify extracted attributes
OK: STEP attributes OK
==> [STEP] Verify auto-created Part
OK: STEP Part properties OK (item_number=CNC)

==> [PRT] Import + auto_create_part
OK: PRT imported (file_id=7298f196-062d-48df-be75-266b4375b44a, item_id=c1339c14-ba15-4e68-b9b6-d4705c9394a1)
==> [PRT] Run cad_extract
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
OK: PRT cad_extract OK
==> [PRT] Run cad_preview
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
OK: PRT cad_preview OK
==> [PRT] Verify preview endpoint
OK: PRT preview endpoint HTTP 302
==> [PRT] Verify extracted attributes
OK: PRT attributes OK
==> [PRT] Verify auto-created Part
OK: PRT Part properties OK (item_number=model2)

==============================================
CAD Real Samples Verification Complete
==============================================
ALL CHECKS PASSED
PASS: CAD Real Samples

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
OK: Created Part: 9ee99db6-867c-4c5a-8f57-4f7fdaccb4dd

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
OK: Created Part: ea879ff6-ed58-4799-8d3a-af495fe2076e

==> Search status
OK: Search engine: db

==> Reindex
OK: Reindex completed (indexed=1175)

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
OK: Created ECO product: 7da3bbf5-0b50-4df8-8aa9-06dd2d188780

==> Create ECO
OK: Created ECO: a5c5ad6f-5a2a-466e-b740-c75d61476ca2

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
OK: Created Part: 6ee3ee47-f3d4-483d-a961-678f6add454c

==> Upload file
OK: Uploaded file: 3e64a346-7bf2-4b93-b860-5882efef5774

==> Create ECO stage + ECO
OK: Created ECO: 6bcab3ed-e069-48aa-ab9f-5dbfb99272ff

==> Create job
OK: Created job: 01d54c8b-fb39-4460-bc7a-8e4f98bb234b

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
OK: Created Part: 3f1e2257-3784-4fb8-b827-60a117cfb81c

==> Upload file
OK: Uploaded file: 47db4fa6-9310-43fb-8b8c-6a559ca56be0

==> Create ECO stage + ECO
OK: Created ECO: 409b5d95-f135-4ce7-9eb2-29ac15c5ffa2

==> Create job
OK: Created job: bd1c44a3-fb8d-44a5-b20c-ce4f250739e2

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
NEW_TENANT: tenant-provision-1769509109
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
OK: Tenant created: tenant-provision-1769509109

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
OK: Created assembly: 99f53786-e56f-419d-b100-6b1f4bd77a83
OK: Created sub-assembly: 72e7e909-73e8-4ec0-9b16-12f4e06408a4
OK: Created component: 99b8bf12-b7ca-4c47-8582-c47c4dc959b3
OK: Created second assembly: 3c60469b-f235-423c-ba44-3bd3428b3da3

==> Build BOM hierarchy
OK: Added sub-assembly to assembly
OK: Added component to sub-assembly
OK: Added component to second assembly

BOM Structure:
  ASSEMBLY (99f53786-e56f-419d-b100-6b1f4bd77a83)
    └── SUB-ASSEMBLY (72e7e909-73e8-4ec0-9b16-12f4e06408a4)
          └── COMPONENT (99b8bf12-b7ca-4c47-8582-c47c4dc959b3)
  ASSEMBLY2 (3c60469b-f235-423c-ba44-3bd3428b3da3)
    └── COMPONENT (99b8bf12-b7ca-4c47-8582-c47c4dc959b3)

==> Test Where-Used (non-recursive)
Where-used response:
  item_id: 99b8bf12-b7ca-4c47-8582-c47c4dc959b3
  count: 2
OK: Non-recursive where-used: found 2 direct parents
Parent IDs found:
  - 3c60469b-f235-423c-ba44-3bd3428b3da3
  - 72e7e909-73e8-4ec0-9b16-12f4e06408a4

==> Test Where-Used (recursive)
Recursive where-used response:
  count: 3
OK: Recursive where-used: found 3 parents
Parents by level:
  Level 1: Second Assembly for Where-Used Test 1769509111
  Level 1: Sub-Assembly for Where-Used Test 1769509111
  Level 2: Assembly for Where-Used Test 1769509111

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
OK: Created Part: bf7666f1-3508-478c-b296-42f2ea3ef714

==> Init version
OK: Init version: aea1b5a5-5764-48d7-b7f1-10916e9484fb

==> Upload file
OK: Uploaded file: d054e1d4-4598-46b0-ac1c-5f56617de7ef

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
OK: Created Parts: parent=1ae326db-1fda-480d-ad73-4b37f3cc1816 child=a97a7104-117b-4a14-b787-ba42ba0938b4

==> Add BOM child
OK: Added BOM line: 67bbea18-e28a-4f55-9788-db39c827b673

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
OK: Created Parts: grand=b0bcbfd8-d4b8-4761-8873-0ff4858ca11c parent=8ede14f2-0db4-421e-977b-1662a9af5cf7 child=0d5eed20-cb06-4a5a-a21a-58da65ce2710

==> Add BOM lines
OK: Added BOM lines: parent_rel=a31233a6-5a86-48fa-bf8b-5041ed73d99b grand_rel=99cab66b-13ea-4c0f-b008-3f868563369b

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
OK: Added substitute: 76479604-fcf4-481c-ac31-1c43dddffbe3

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
OK: Created Part: 3f6b7e49-fdd6-4e11-8ebc-a4b7c4bcce63

==> Upload file with metadata
OK: Uploaded file: 0dc01a66-a2ab-4580-a17e-81e765517f85

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
OK: Created Document: 32b9ceac-8acf-4797-9376-08f42833346b

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
OK: Created stage: 1abc725b-7ebf-4cca-b39b-4b5d77919084

==> Create ECO product
OK: Created product: 0af899a2-7227-4b3a-9496-4e65a693ca12

==> Create ECO
OK: Created ECO: 06b2d852-dda4-4d2f-8daf-28c20fac7a2a

==> Move ECO to approval stage
OK: Moved ECO to stage

==> Approve ECO
OK: Approved ECO: 6ff3682c-1ecd-42a9-8357-f78d683a4733

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
OK: Created Part=9c764dc8-84d8-4275-9aa9-b8d592d4b59c Document=c0c9f877-18f1-41c8-9109-a422a79e398c

==> Link Document to Part
OK: Created Document relation

==> Create ECO stage and ECO
OK: Created ECO=5f20c732-a334-4876-a090-232844c6fbc9 stage=8a8c8d70-6f7e-453b-8020-60fe0044f762

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
OK: Created parents: A=749f710f-98c6-45bd-9d54-6e13953099ef, B=540dacc5-2288-4fb8-8cf0-98745904dd5c

==> Create child items
OK: Created children: X=ebb2b198-b726-45ff-ba98-a8dafe60f315, Y=99160349-106b-4b26-9c79-3580893f11fc, Z=98cc6128-3d57-4409-adb4-aac6f18d6f09

==> Build BOM A (baseline)
OK: BOM A created

==> Build BOM B (changed + added)
OK: BOM B created

==> Create substitute for CHILD_X in BOM B
OK: Substitute added: d746e170-da2d-4e6b-9e5d-8c8ea3d2b645

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
OK: Created Parts: left=0a514cb8-e180-467e-8a8b-9d9b30b8f3c5 right=b549e72c-ccdf-4e85-9637-8ae10f984239 child=e2b9856a-eb2b-44de-93de-5efdc2f9fe13 sub=62a410c4-e57f-40dd-8a77-b8a34a00a1af

==> Add BOM lines
OK: Added BOM lines: left_rel=2ab43df4-d448-47a4-850f-b88be5c5f58b right_rel=8021dc4b-10a0-4e92-bf38-e72d3d44de92

==> Add substitute to left BOM line
OK: Added substitute: 0ca8a8af-23d7-450e-8708-f3e28e0a5ebf

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
OK: Created parent=3fc9286e-1cca-4959-84db-5b6941463a09 children=2c394474-3eea-45a4-b85f-e5985d45e396,33ba7ca3-2cfe-4a88-971a-6233d18b1a14

==> Build BOM (A -> B, C)
OK: BOM created

==> Create baseline
Baseline snapshot validated
OK: Baseline created: 8ae75ff5-6767-437b-b08b-edf1692665c5

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
OK: Created parent=32afadc2-c6f5-467a-a6e3-35e880260e8a child=fb9cbd57-7ebd-4a99-a3de-78b853325768 substitutes=194f5a01-c0ca-4e31-9db3-ce1225e85b39,c13f92d6-7a35-4dc1-8eac-2fb97fc7742e

==> Create BOM line (parent -> child)
OK: Created BOM line: d92525cb-0b7e-497a-9971-9ddb45ef8fef

==> Add substitute 1
OK: Added substitute 1: fd8c67ee-df9a-48be-aef2-0ea6a8acaaa3

==> List substitutes (expect 1)
OK: List count=1

==> Add substitute 2
OK: Added substitute 2: 67b898bf-0a07-499c-9b06-5e2a0572517f

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
OK: Created EBOM root=d5ea8f7a-92f8-4638-bcb0-eddd2888ec3c child=93d40f38-a3b8-4fac-b2d1-e8426ccdfa24 substitute=4f94e5da-ed37-4d5c-9244-ab94684bda69

==> Create EBOM BOM line
OK: EBOM BOM line: 8f199257-2622-4cb9-a866-000b8d665a3e

==> Add substitute to EBOM BOM line
OK: EBOM substitute relation: 941983e4-5c0f-4e2b-acda-9e5c2bc0e0cb

==> Convert EBOM -> MBOM
OK: MBOM root: 1da813eb-1e2d-4d2e-87cc-80b7f6c50e7b

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
OK: Created parts A=3f64b8e5-f4f7-4d07-b9eb-9338d794ea34 B=e12159ab-d10d-4964-8dd0-b81d536483d2 C=b821f290-9b4e-445b-9f21-b9a27d90a676

==> Add equivalent A <-> B
OK: Added equivalent A-B: 2f747db6-db39-4127-ac62-da0c109a705a

==> Add equivalent A <-> C
OK: Added equivalent A-C: c7947574-2d70-4066-aa96-64956224c6f7

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
OK: Created Part: e1e84513-da22-4dcb-b067-0e6f0339434c

==> Init version
OK: Init version: 0f35d6aa-f349-4c47-b687-1d4e6ddca6fc

==> Upload file
OK: Uploaded file: 6d9c0dea-7a62-4207-b294-3df700fd2db6

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
S3.3 (Versions)           PASS
S4 (ECO Advanced)         PASS
S5-A (CAD Pipeline S3)    PASS
S5-B (CAD 2D Connectors)  PASS
S5-B (CAD 2D Real Connectors) PASS
S5-B (CAD 2D Connector Coverage) PASS
S5-C (CAD Attribute Sync) PASS
S5-B (CAD Connectors Config) PASS
S5-C (CAD Sync Template)  PASS
S5-C (CAD Auto Part)      PASS
S5-C (CAD Extractor Stub) PASS
S5-C (CAD Extractor External) PASS
S5-C (CAD Extractor Service) PASS
CAD Real Samples          PASS
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
PASS: 52  FAIL: 0  SKIP: 0
----------------------------------------------

ALL TESTS PASSED
