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
==============================================
Enabled: RUN_UI_AGG RUN_TENANT_PROVISIONING RUN_OPS_S8 RUN_CAD_EXTRACTOR_STUB RUN_CAD_AUTO_PART RUN_CAD_REAL_CONNECTORS_2D RUN_CAD_CONNECTOR_COVERAGE_2D RUN_CAD_EXTRACTOR_EXTERNAL RUN_CAD_EXTRACTOR_SERVICE RUN_CAD_REAL_SAMPLES
Disabled: RUN_CADGF_PREVIEW_ONLINE (CADGF router not configured)
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
AML add: OK (part_id=83fe7b0b-29e8-4d68-9038-3da19a4f0291)
AML get: OK
==> Search
Search: OK
==> RPC Item.create
RPC Item.create: OK (part_id=0f8598ca-f86a-4b09-ba68-bbd85c0187bf)
==> File upload/download
File upload: OK (file_id=ef4ca7d6-7a7c-4acd-9ac9-3d60c17856b3)
File metadata: OK
File download: OK (http=302->200)
==> BOM effective
BOM effective: OK
==> Plugins
Plugins list: OK
Plugins ping: OK
==> ECO full flow
ECO stage: OK (stage_id=9234c9d7-46ba-41e6-a1a9-943f5c148c95)
ECO create: OK (eco_id=331c8481-68f5-4591-a616-ac9680edf79c)
ECO new-revision: OK (version_id=3ec9caa9-b0ec-441f-a4ac-a134accc12a7)
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
OK: Created Part: 0e7f82b4-64e0-4d69-a9a4-9cc7a6d00bbc

==> Upload file with metadata
OK: Uploaded file: d3188d98-af74-4a7e-9f26-7bb1747a491a

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
OK: Created Document: 2320719c-add4-49b8-8071-e48e3a02980d

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
OK: Created parent=14610fb9-0ba0-47c5-ad19-ce83eff59449 child=2760d4f0-2309-4f3b-b848-2087c5ab8adf child2=85c4b6ea-e404-49fa-9395-fdfa00db4d0e

==> Add BOM child in Draft
OK: BOM relationship 5ca2c311-8cdc-436e-9dc9-131e521e3ffd

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
Viewer identity: OK (id=1769505547)
==> Configure PermissionSets
Created PermissionSet: ReadOnly-1769506718
ACE viewer (read-only): OK
ACE admin (full): OK
==> Assign PermissionSet to ItemTypes
Assigned permission to Part: OK
Assigned permission to Part BOM: OK
==> Admin creates Part (should succeed)
Admin AML add Part: OK (part_id=4a7cde65-45ed-4c6b-b3f0-6320b4172eeb)
Admin created child Part: OK (child_id=0c9e9d18-8af3-417f-8eb7-b2dbf3c94cd6)
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
Created Part A: 840d0472-1cd4-435c-8d67-7a98a544737c
Created Part B: 319d5fa9-1818-4b81-ac8c-908cada5e015
Created Part C: 816c8c59-5391-404c-8a1f-4d8c3937da21
Created Part D: 11357f98-3ad9-4294-a524-3480b440c0fd
==> Build BOM structure: A -> B -> C, B -> D
Adding B as child of A...
A -> B relationship created: c4f32b29-69da-4674-bfa0-be35a1de126b
Adding C as child of B...
B -> C relationship created: 5891a2a5-f93a-4b57-8746-d315ed24b3b1
Adding D as child of B...
B -> D relationship created: 0e103089-feac-4401-9a33-2a01d9243935
BOM structure created: OK
==> Test BOM tree query with depth
Full tree (depth=10): Level 1 has 1 child (B): OK
Full tree (depth=10): Level 2 has 2 children (C, D): OK
Limited tree (depth=1): Only shows B with no grandchildren: OK
==> Test cycle detection (C -> A should be 409)
Cycle detection: C -> A returned 409: OK
Cycle error type: CYCLE_DETECTED: OK
Cycle path returned: ['816c8c59-5391-404c-8a1f-4d8c3937da21', '840d0472-1cd4-435c-8d67-7a98a544737c', '319d5fa9-1818-4b81-ac8c-908cada5e015', '816c8c59-5391-404c-8a1f-4d8c3937da21']: OK
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
Date context: TODAY=2026-01-27T09:38:42Z, NEXT_WEEK=2026-02-03T09:38:42Z, LAST_WEEK=2026-01-20T09:38:42Z
==> Seed identity (admin + viewer)
Created users: admin (superuser), viewer (no write)
==> Seed meta schema
==> Login as admin
Admin login: OK
==> Configure PermissionSets
Permissions configured: OK
==> Create test parts
Created Part A (parent): 5286e59f-3c9c-4e63-a405-3a5152845231
Created Part B (future child): 8d487193-ab8c-4b58-a6a7-7f545439aaf8
Created Part C (current child): d767ef8d-0177-4ed1-ad7b-dfaef46aca15
Created Part D (expired child): cf9f4054-e18a-42e7-9c01-5e84113f8004
==> Build BOM with effectivity dates
Adding B to A (effective from next week)...
A -> B relationship: bcb02f69-5b0c-4346-9885-9dce54ee948e, effectivity_id: a3491b48-330f-4b8c-83d4-f933f3487262
Adding C to A (effective from last week, always visible now)...
A -> C relationship: f9dec519-c497-49c6-8116-9119eda01b0c
Adding D to A (expired - ended last week)...
A -> D relationship: b6ad689c-e16d-4fd0-8c93-651273805881
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
Created Part: 26b49dd3-6712-4c0c-ad1f-5687ae5d67d5
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
Revision schemes list: 16 scheme(s): OK
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
OK: Stage created: 7043bcf4-6556-4631-92ca-932229d6be62

==> Create product + assembly
OK: Created product: 5569f460-7715-459a-983c-86a29f407ae6
OK: Created assembly: 54f76b96-062d-41b2-aea1-6db4321cefad

==> Init product version
OK: Initial version: 0cead487-5009-4a4d-bec0-d5de5bab2b5f

==> Build where-used link (assembly -> product)
OK: Where-used link created

==> Upload file + attach to product
OK: File attached (status=created)

==> Checkout + checkin to sync version files
OK: Version checked in after file binding
Initial version files: OK
OK: Version files synced

==> Create ECO (for product)
OK: ECO1 created: 354abac7-29c3-4f70-9d28-153947951f61

==> Move ECO1 to approval stage
OK: ECO1 moved to stage

==> SLA overdue check + notify
Overdue list: OK
OK: Overdue list validated
Overdue notifications: OK
OK: Overdue notifications sent

==> Create ECO target version
OK: Target version: 10cea475-e65f-46ab-ae56-6420f8f6423b

==> Resolve target version timestamp
OK: Target created_at: 2026-01-27T09:38:48.171011

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
OK: ECO2 created/moved: a0931ac8-9114-4b2a-89cf-d80e348a8305

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
Preview job ID: 32b8fb04-9111-4916-8077-056b4b0e83ff
Geometry job ID: ecb65212-b6f7-4628-8ee5-5c78837dbdec

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
OK: Created files: /tmp/yuantus_gstarcad_1769506736.dwg, /tmp/yuantus_zwcad_1769506736.dxf, /tmp/yuantus_haochencad_1769506736.dwg, /tmp/yuantus_zhongwang_1769506736.dxf, /tmp/yuantus_cad_auto_1769506736.dwg, /tmp/yuantus_cad_auto_zw_1769506736.dwg

==> Upload gstarcad_1769506736.dwg (GSTARCAD)
OK: Uploaded file: d5f26a6e-e7e8-4e21-bb11-76b211327c11
Metadata OK
OK: Metadata verified (GSTARCAD)

==> Upload zwcad_1769506736.dxf (ZWCAD)
OK: Uploaded file: 6ce9a5bf-3515-4588-ac7a-e87998406ed0
Metadata OK
OK: Metadata verified (ZWCAD)

==> Upload haochencad_1769506736.dwg (HAOCHEN)
OK: Uploaded file: 39273867-376b-4661-830d-553839f39db8
Metadata OK
OK: Metadata verified (HAOCHEN)

==> Upload zhongwangcad_1769506736.dxf (ZHONGWANG)
OK: Uploaded file: c5256535-f27a-43fa-8505-4c36c7141922
Metadata OK
OK: Metadata verified (ZHONGWANG)

==> Upload cad_auto_1769506736.dwg (auto-detect)
OK: Uploaded file: a4a12a33-da2d-4be6-b6f8-0566e4b678b8
Metadata OK
OK: Metadata verified (HAOCHEN)

==> Upload cad_auto_zw_1769506736.dwg (auto-detect)
OK: Uploaded file: e5893d54-e4aa-44b0-8bbb-64cc4cfb3169
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
OK: HAOCHEN uploaded (file_id=8d35dc0a-d339-41ef-8b37-6fe6733daa65, job_id=5c6400ac-7f28-41ac-9a42-301eee15b0c6)
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
OK: Job completed
Metadata OK
OK: HAOCHEN metadata verified
Attributes OK
OK: HAOCHEN attributes verified (part_number=J2824002-06)

==> [ZHONGWANG] Upload + cad_extract
OK: ZHONGWANG uploaded (file_id=56e33d28-2cec-4242-83e5-340898b23f47, job_id=c46ada15-83ca-4d7c-94ba-ad9445f91ea6)
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

==> Upload solidworks_part_1769506749.sldprt
OK: Uploaded file: 867903c7-48eb-440f-b4f3-342960d95ab6
Metadata OK
OK: Metadata verified (SOLIDWORKS)

==> Upload solidworks_asm_1769506749.sldasm
OK: Uploaded file: c796a55b-e3b5-447d-8c6f-9badeceea833
Metadata OK
OK: Metadata verified (SOLIDWORKS)

==> Upload nx_1769506749.prt
OK: Uploaded file: 3ba35a82-17d5-4f90-a519-4cfc2b749ef5
Metadata OK
OK: Metadata verified (NX)

==> Upload creo_1769506749.prt
OK: Uploaded file: e8df74c2-672c-42b1-b386-c479053b40bf
Metadata OK
OK: Metadata verified (CREO)

==> Upload catia_1769506749.catpart
OK: Uploaded file: 6601aaeb-09f1-4c26-9eef-91e6509dc5d5
Metadata OK
OK: Metadata verified (CATIA)

==> Upload inventor_1769506749.ipt
OK: Uploaded file: 1b963ef3-39ed-4c7f-af7d-81822209c406
Metadata OK
OK: Metadata verified (INVENTOR)

==> Upload auto_1769506749.prt
OK: Uploaded file: 3bc9dca1-4d09-4bfd-8a07-09ed745d8005
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
OK: Created Part: edad3bd6-511a-4d50-94f2-da9159656c85

==> Upload CAD file and enqueue extract job
OK: Uploaded file: 7bef82d1-8502-4216-9eb2-17de8ffbffa9
OK: Created job: 3bed146f-a6d5-4d90-8b77-f00c4961e07b

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
SAMPLE: /var/folders/23/dzwf05nn7nvgxc1fz30kn5gh0000gn/T/yuantus_ocr_sample_XXXXXX.RRfpviuQKP.png
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
SAMPLE: /tmp/yuantus_cad_auto_part_1769506771.dwg
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Fetch Part ItemType properties
OK: Resolved property IDs

==> Import CAD with auto_create_part
OK: Created/linked Part: 7d411601-0c90-43d6-81e7-d987cd2fb45b
OK: Imported File: 492acd2c-0fe3-461f-900d-3ab212172e3e
OK: Attachment created: 86d72c20-d25f-47c5-9845-07cfd9d61754

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
EXTRACTOR: http://127.0.0.1:49473
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Upload CAD file and enqueue extract job
OK: Uploaded file: 75baae76-5941-4489-a69e-c77a0c70eb06
OK: Created job: 40152308-14cb-4b16-b16b-c642ee125d72

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
OK: Created job: 693e9878-8aa9-45f6-801a-8a1aaf6b111e

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
OK: Created Part: 4e9e7cc9-8ad9-44b0-b0be-aa515d158a74

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
OK: Created Part: e123458e-98f3-4fae-b6c8-af22ab4f803f

==> Search status
OK: Search engine: db

==> Reindex
OK: Reindex completed (indexed=1103)

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
OK: Created ECO product: 96ac61d3-f073-4247-99dc-8fd38c139064

==> Create ECO
OK: Created ECO: 5ad3d3dd-3ea5-4c0a-a79c-d7b0173768c8

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
OK: Created Part: a47c5115-556e-4b2f-b90a-702b357fd260

==> Upload file
OK: Uploaded file: 46f86476-7ef3-48c5-a526-55a58b0e9450

==> Create ECO stage + ECO
OK: Created ECO: 2d1cb0ca-ba19-4c71-aefc-fe4db531f1c6

==> Create job
OK: Created job: 19dc2a7b-4a8f-4051-afba-d01b3984192e

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
OK: Created Part: c52cd374-f3ab-4dea-a4f2-01e0bbce7c6c

==> Upload file
OK: Uploaded file: 1a915b5b-171d-4961-9037-f62cbcf17955

==> Create ECO stage + ECO
OK: Created ECO: 02a08dae-a7d0-4fb1-b3aa-b892326d81d4

==> Create job
OK: Created job: c5babbd0-7354-47d3-8010-4e9d8f5bc98d

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
NEW_TENANT: tenant-provision-1769506794
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
OK: Tenant created: tenant-provision-1769506794

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
OK: Created assembly: 28c00659-a966-47b4-bf05-f5e4bfb89c5e
OK: Created sub-assembly: db955868-63ab-4402-b111-6a364721c60d
OK: Created component: 76a276ea-aed2-483a-a7c6-d9f14d98773f
OK: Created second assembly: 1244dde4-23d6-4753-80ac-a167337e67f8

==> Build BOM hierarchy
OK: Added sub-assembly to assembly
OK: Added component to sub-assembly
OK: Added component to second assembly

BOM Structure:
  ASSEMBLY (28c00659-a966-47b4-bf05-f5e4bfb89c5e)
    └── SUB-ASSEMBLY (db955868-63ab-4402-b111-6a364721c60d)
          └── COMPONENT (76a276ea-aed2-483a-a7c6-d9f14d98773f)
  ASSEMBLY2 (1244dde4-23d6-4753-80ac-a167337e67f8)
    └── COMPONENT (76a276ea-aed2-483a-a7c6-d9f14d98773f)

==> Test Where-Used (non-recursive)
Where-used response:
  item_id: 76a276ea-aed2-483a-a7c6-d9f14d98773f
  count: 2
OK: Non-recursive where-used: found 2 direct parents
Parent IDs found:
  - db955868-63ab-4402-b111-6a364721c60d
  - 1244dde4-23d6-4753-80ac-a167337e67f8

==> Test Where-Used (recursive)
Recursive where-used response:
  count: 3
OK: Recursive where-used: found 3 parents
Parents by level:
  Level 1: Sub-Assembly for Where-Used Test 1769506796
  Level 2: Assembly for Where-Used Test 1769506796
  Level 1: Second Assembly for Where-Used Test 1769506796

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
OK: Created Part: 2831bd64-d9d5-421f-96b6-06f077176970

==> Init version
OK: Init version: 2da4e6f1-321c-4aed-8916-7efd48e057bc

==> Upload file
OK: Uploaded file: 637b5bed-2674-452c-8159-e8190adb9eaa

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
OK: Created Parts: parent=78351cdc-68e8-4498-b5b3-cc4cd0a8ada7 child=0a8beb03-d1d9-49b1-b449-c73599bb18a2

==> Add BOM child
OK: Added BOM line: c9d95817-57c9-479a-b44e-99e38cfa4d98

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
OK: Created Parts: grand=0555e7ff-cead-434a-9fc5-7807091cc559 parent=4f058845-2313-4abd-b20c-416858230b21 child=f649379a-5258-4a19-91a5-63adf1b2897a

==> Add BOM lines
OK: Added BOM lines: parent_rel=92a4e533-d3be-4034-b423-4bb864c886ef grand_rel=01713ad2-7996-4f2c-a6b2-471aed28db8f

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
OK: Added substitute: 827a1b5a-5007-481c-986f-2bb430bd8ec8

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
OK: Created Part: b380235e-1b4a-46a6-9a28-974b799e82de

==> Upload file with metadata
OK: Uploaded file: 0f470807-c952-437c-9a63-bfc275fbfcc5

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
OK: Created Document: 96fcc074-9771-4748-b16c-8f54d3b38ab1

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
OK: Created stage: d7ee479e-86cc-4878-8f59-afd623dd1403

==> Create ECO product
OK: Created product: 0ec3fcb5-75d0-4d4c-9117-9d9a22245ec7

==> Create ECO
OK: Created ECO: 457fbb2c-8e59-492a-93b9-d69a8e04cb7c

==> Move ECO to approval stage
OK: Moved ECO to stage

==> Approve ECO
OK: Approved ECO: 2ea091e8-e170-4312-8c94-6462b2145584

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
OK: Created Part=dfa92026-8aea-4827-a32b-7ff61c106c6e Document=d4326f60-7877-406c-91fd-b1e675f2c64b

==> Link Document to Part
OK: Created Document relation

==> Create ECO stage and ECO
OK: Created ECO=ce8edb7b-9cf2-4b65-a617-6573b5434d82 stage=4f89f37d-3dbb-4462-889f-4d91d303fb43

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
OK: Created parents: A=29ed0e1d-8426-42ff-87a5-89a28be0c414, B=4dfc2e65-356a-4261-b0a3-c4c3b96a30da

==> Create child items
OK: Created children: X=819b112f-4398-4684-bcbf-04298f9eb1a4, Y=d3a58dc3-2092-4463-94c9-dddbe04f0f72, Z=d257c75e-6597-481f-a9cd-6e2743784510

==> Build BOM A (baseline)
OK: BOM A created

==> Build BOM B (changed + added)
OK: BOM B created

==> Create substitute for CHILD_X in BOM B
OK: Substitute added: 57f65ea3-d0c3-47ba-97cf-b29022310f6f

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
OK: Created Parts: left=15e3d24f-9524-457b-9d71-97ac3ef17e6b right=4e25e588-e485-4dce-b838-4e0fc46dd902 child=b2a23261-52f6-4b96-ad5c-bed574344040 sub=1969db25-fa28-42a1-a807-6e0089c3d9ce

==> Add BOM lines
OK: Added BOM lines: left_rel=438bb22b-504a-48f2-823a-24057f106202 right_rel=9658a3ba-c1b4-4605-a066-ee30d2b6f144

==> Add substitute to left BOM line
OK: Added substitute: 25bb8e4d-291d-490a-93ad-bc06940466ca

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
OK: Created parent=6a33577f-bd01-42cf-8b66-17ea8517d834 children=67b37567-a872-400f-b9da-15a69cd11ddf,513288a0-a292-4527-bd7d-7d295c9fdd65

==> Build BOM (A -> B, C)
OK: BOM created

==> Create baseline
Baseline snapshot validated
OK: Baseline created: a80569d6-c4b4-4075-8d2f-08dbd5adcd63

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
OK: Created parent=62281143-15ef-4318-b86a-6cc621ae6cb0 child=eb416544-2080-4ad8-9e7c-e0753f4a68fb substitutes=dcd406ed-f76d-4147-84e5-7d53c2a17a1c,e0317c8b-1d6e-457d-a1f3-c204d8f845d9

==> Create BOM line (parent -> child)
OK: Created BOM line: f5d4d47b-b3b9-483f-a5f6-834fac10e891

==> Add substitute 1
OK: Added substitute 1: 2f774122-9359-4301-bd0c-8c62f3f1e6b3

==> List substitutes (expect 1)
OK: List count=1

==> Add substitute 2
OK: Added substitute 2: 07b0ae7d-8beb-4ee6-a6d0-3f46de1e7c96

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
OK: Created EBOM root=09e51703-82c2-4b09-ac49-e84003f3ecf8 child=379d5b06-692d-4e37-9355-5e8eeb0c3a55 substitute=58005aeb-fd4a-480c-a37f-1286177768d3

==> Create EBOM BOM line
OK: EBOM BOM line: 11b3c82f-a315-4b96-b62f-cb74e3c4fd1d

==> Add substitute to EBOM BOM line
OK: EBOM substitute relation: 4fdc47e9-65cc-4bfd-bad3-23f7c5461c47

==> Convert EBOM -> MBOM
OK: MBOM root: 31ca96d2-9df9-4199-a00d-a378a1c2fd0f

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
OK: Created parts A=3fdb3311-cf73-482a-86f7-fa4b604fbbaa B=7b8882cb-44a4-474d-8727-7a9de1c1ed58 C=2efb23f8-5df5-4679-aa7a-24ca758f96ea

==> Add equivalent A <-> B
OK: Added equivalent A-B: 3b7b8cb4-ba64-4212-92a4-d3dd4d078510

==> Add equivalent A <-> C
OK: Added equivalent A-C: 96d9e56f-8ff5-42a1-8f77-50f66463aa1a

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
OK: Created Part: e2a4e9ca-7d40-4b02-a495-ed8bad57f72e

==> Init version
OK: Init version: e9e26b39-85cc-46cc-b054-ad17aa4b4be1

==> Upload file
OK: Uploaded file: 806943c1-3695-4d90-9386-65a18a457e54

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
PASS: 51  FAIL: 0  SKIP: 1
----------------------------------------------

ALL TESTS PASSED
