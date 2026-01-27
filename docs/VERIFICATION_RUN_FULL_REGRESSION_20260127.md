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
AML add: OK (part_id=fbddda99-dd82-46b6-b553-8bf51de68421)
AML get: OK
==> Search
Search: OK
==> RPC Item.create
RPC Item.create: OK (part_id=a203a6d2-6f82-47ab-8555-43cbb65c12c1)
==> File upload/download
File upload: OK (file_id=dae135de-2f23-470e-8619-0992fd86c725)
File metadata: OK
File download: OK (http=302->200)
==> BOM effective
BOM effective: OK
==> Plugins
Plugins list: OK
Plugins ping: OK
==> ECO full flow
ECO stage: OK (stage_id=4521d53e-f37d-4ce4-b62d-42ad83cc58d9)
ECO create: OK (eco_id=6363bae6-0a84-4993-8662-c026bf271ada)
ECO new-revision: OK (version_id=854c5910-5ad5-42ed-8ce5-fd9d34f781c4)
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
OK: Created Part: 64590f32-73ac-4b47-8ab2-3a318ae7ae48

==> Upload file with metadata
OK: Uploaded file: f050a18f-f08c-466f-8981-01578cd74270

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
OK: Created Document: 6c4d0605-278f-4a76-91c4-412c51223a6d

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
OK: Created parent=55ab1a00-cb9f-4731-8075-8a555e556c6a child=0620014b-0d26-4905-af06-49199534d70c child2=6b3ae056-eab2-461b-b4f9-98dfd5b9063c

==> Add BOM child in Draft
OK: BOM relationship 6d04585e-cdcb-4090-bd29-4888087f4670

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
Viewer identity: OK (id=1769496546)
==> Configure PermissionSets
Created PermissionSet: ReadOnly-1769502044
ACE viewer (read-only): OK
ACE admin (full): OK
==> Assign PermissionSet to ItemTypes
Assigned permission to Part: OK
Assigned permission to Part BOM: OK
==> Admin creates Part (should succeed)
Admin AML add Part: OK (part_id=4916ecae-a0df-43cf-a8ee-8394d486ba18)
Admin created child Part: OK (child_id=3d355056-cb3f-4007-9471-6dc0f347fe35)
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
Created Part A: 4feab7bb-1fae-4826-a594-15cba874ac15
Created Part B: 326ded41-8afd-4c96-a191-e61c56592e71
Created Part C: be822fc9-f9b4-4ac1-b0a9-61e9e309a5d2
Created Part D: c30911e2-68b3-49d3-a57f-384816951755
==> Build BOM structure: A -> B -> C, B -> D
Adding B as child of A...
A -> B relationship created: b948bc72-42ac-4f8c-a057-43b801f066e2
Adding C as child of B...
B -> C relationship created: 2db2cd72-490d-4dc4-9b48-404da41d494b
Adding D as child of B...
B -> D relationship created: aa4a8f97-99ee-49e0-a62c-a1f45fc219b8
BOM structure created: OK
==> Test BOM tree query with depth
Full tree (depth=10): Level 1 has 1 child (B): OK
Full tree (depth=10): Level 2 has 2 children (C, D): OK
Limited tree (depth=1): Only shows B with no grandchildren: OK
==> Test cycle detection (C -> A should be 409)
Cycle detection: C -> A returned 409: OK
Cycle error type: CYCLE_DETECTED: OK
Cycle path returned: ['be822fc9-f9b4-4ac1-b0a9-61e9e309a5d2', '4feab7bb-1fae-4826-a594-15cba874ac15', '326ded41-8afd-4c96-a191-e61c56592e71', 'be822fc9-f9b4-4ac1-b0a9-61e9e309a5d2']: OK
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
Date context: TODAY=2026-01-27T08:20:48Z, NEXT_WEEK=2026-02-03T08:20:48Z, LAST_WEEK=2026-01-20T08:20:48Z
==> Seed identity (admin + viewer)
Created users: admin (superuser), viewer (no write)
==> Seed meta schema
==> Login as admin
Admin login: OK
==> Configure PermissionSets
Permissions configured: OK
==> Create test parts
Created Part A (parent): 25522335-6399-438a-a061-c584c4a2e657
Created Part B (future child): 67db5162-e324-4a90-ad1b-d540bcfbf690
Created Part C (current child): 1bb7003c-0586-45b1-b126-58f650a3e59c
Created Part D (expired child): 839bb30f-b5de-4f10-8efc-30d5f6f29c8b
==> Build BOM with effectivity dates
Adding B to A (effective from next week)...
A -> B relationship: 642afa02-b63a-49a6-b043-b08afbc4f338, effectivity_id: 63cc8cea-ca95-4252-8ee1-2061eaa2a7b2
Adding C to A (effective from last week, always visible now)...
A -> C relationship: d9182e6b-f591-4670-a699-8bce02f3f6a9
Adding D to A (expired - ended last week)...
A -> D relationship: 7b229a04-4262-43fb-94fd-e4db52285fc6
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
Created Part: 75aa2cfb-5d18-4806-8796-84c6f5ad9290
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
Revision schemes list: 13 scheme(s): OK
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
OK: Stage created: eaa8b2bb-2d66-4d0b-9a1f-f765ebde72f8

==> Create product + assembly
OK: Created product: 8ef48bbc-4994-41f1-8625-339aa6cdc078
OK: Created assembly: e9487194-5922-4a5a-832e-9940b2165e1d

==> Init product version
OK: Initial version: 3f02e5dc-11e1-477d-ba0b-39403991b5d4

==> Build where-used link (assembly -> product)
OK: Where-used link created

==> Upload file + attach to product
OK: File attached (status=created)

==> Checkout + checkin to sync version files
OK: Version checked in after file binding
Initial version files: OK
OK: Version files synced

==> Create ECO (for product)
OK: ECO1 created: bedc2917-baa8-4296-80e6-c516d64da0ee

==> Move ECO1 to approval stage
OK: ECO1 moved to stage

==> SLA overdue check + notify
Overdue list: OK
OK: Overdue list validated
Overdue notifications: OK
OK: Overdue notifications sent

==> Create ECO target version
OK: Target version: 6a347bb7-2a98-48d7-a61a-fd85005662f6

==> Resolve target version timestamp
OK: Target created_at: 2026-01-27T08:20:54.683395

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
OK: ECO2 created/moved: f57bee23-9850-45b5-abfa-8a3ed2d926e4

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
Preview job ID: cd858689-8189-4d5d-a59c-79811f63d05f
Geometry job ID: 1b0d1e26-5929-4bdf-a8c3-04e793679901

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
SKIP: CAD ML Vision not available at http://localhost:8001/api/v1/vision/health (HTTP 000000)
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
OK: Created files: /tmp/yuantus_gstarcad_1769502061.dwg, /tmp/yuantus_zwcad_1769502061.dxf, /tmp/yuantus_haochencad_1769502061.dwg, /tmp/yuantus_zhongwang_1769502061.dxf, /tmp/yuantus_cad_auto_1769502061.dwg, /tmp/yuantus_cad_auto_zw_1769502061.dwg

==> Upload gstarcad_1769502061.dwg (GSTARCAD)
OK: Uploaded file: 23f048e3-22bf-4969-87c9-ba71ceebb345
Metadata OK
OK: Metadata verified (GSTARCAD)

==> Upload zwcad_1769502061.dxf (ZWCAD)
OK: Uploaded file: 65e1311a-1c6d-409c-85d4-7188c0303b89
Metadata OK
OK: Metadata verified (ZWCAD)

==> Upload haochencad_1769502061.dwg (HAOCHEN)
OK: Uploaded file: f9d545c1-273c-4034-9b31-50fb23df5dc2
Metadata OK
OK: Metadata verified (HAOCHEN)

==> Upload zhongwangcad_1769502061.dxf (ZHONGWANG)
OK: Uploaded file: 324a5f11-abcf-4608-a6e3-6b6c5b7828ce
Metadata OK
OK: Metadata verified (ZHONGWANG)

==> Upload cad_auto_1769502061.dwg (auto-detect)
OK: Uploaded file: a0bf3630-da5e-4999-87b7-7990b2ed148a
Metadata OK
OK: Metadata verified (HAOCHEN)

==> Upload cad_auto_zw_1769502061.dwg (auto-detect)
OK: Uploaded file: 9073b762-45b7-4e12-945e-2401fb277f43
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
CAD_EXTRACTOR_BASE_URL: http://127.0.0.1:8200
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> [HAOCHEN] Upload + cad_extract
OK: HAOCHEN uploaded (file_id=8d35dc0a-d339-41ef-8b37-6fe6733daa65, job_id=0d4b8786-0246-44d1-85f7-5cba9aedce94)
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
OK: ZHONGWANG uploaded (file_id=56e33d28-2cec-4242-83e5-340898b23f47, job_id=a74fce9d-b238-4d02-849e-e9690c53693f)
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

==> Upload solidworks_part_1769502074.sldprt
OK: Uploaded file: 79a3e908-dc6f-49f4-8d52-e5d5fad9ade9
Metadata OK
OK: Metadata verified (SOLIDWORKS)

==> Upload solidworks_asm_1769502074.sldasm
OK: Uploaded file: d5e9e3f3-96c3-4d71-80d9-85f2820dcc66
Metadata OK
OK: Metadata verified (SOLIDWORKS)

==> Upload nx_1769502074.prt
OK: Uploaded file: 2e3f05b7-1777-4310-aa42-9177b5c1d746
Metadata OK
OK: Metadata verified (NX)

==> Upload creo_1769502074.prt
OK: Uploaded file: 80206660-f282-45f1-ba50-2640f37b1b33
Metadata OK
OK: Metadata verified (CREO)

==> Upload catia_1769502074.catpart
OK: Uploaded file: 59679dd9-b54c-47ae-ad6d-c92ac143947a
Metadata OK
OK: Metadata verified (CATIA)

==> Upload inventor_1769502074.ipt
OK: Uploaded file: 285e59f8-a7a0-4092-8231-15e18f46f0e3
Metadata OK
OK: Metadata verified (INVENTOR)

==> Upload auto_1769502074.prt
OK: Uploaded file: fda87ad5-6570-406b-b885-32841465fd08
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
OK: Created Part: 1b8f64fb-eb1d-4b93-a60b-0130808aa56d

==> Upload CAD file and enqueue extract job
OK: Uploaded file: 1caffc1f-9d6e-4b91-9b3d-50d3477bcbc3
OK: Created job: d9c4d751-96ba-4635-8905-791998afe59a

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
SKIP: CAD ML Vision not available at http://localhost:8001/api/v1/vision/health (HTTP 000000)
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
SAMPLE: /tmp/yuantus_cad_auto_part_1769502093.dwg
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Fetch Part ItemType properties
OK: Resolved property IDs

==> Import CAD with auto_create_part
OK: Created/linked Part: 50af0302-1df3-47fc-b27d-1e26cc6fab9b
OK: Imported File: d0a1d62f-bfe6-42ad-b90b-640e67511752
OK: Attachment created: 534ef6b3-bba1-4360-831f-1d0d30f407e2

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
EXTRACTOR: http://127.0.0.1:56330
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Upload CAD file and enqueue extract job
OK: Uploaded file: 75baae76-5941-4489-a69e-c77a0c70eb06
OK: Created job: 0ca7f77d-a7b4-4a69-a841-576c886481bd

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
EXTRACTOR: http://127.0.0.1:8200
SAMPLE: /Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Upload CAD file and enqueue extract job
OK: Uploaded file: 630a312a-628f-40b7-b5cc-5f317536aa5e
OK: Created job: b7a087cd-45c3-4628-b64e-afd55bb648bf

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
BASE_URL: http://127.0.0.1:8200
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
CAD_EXTRACTOR_BASE_URL: http://127.0.0.1:8200
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
OK: Created Part: 8e237213-1b2b-4a6c-9ac8-b4d327c8408b

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
OK: Created Part: cdef1e65-d9d7-428c-9247-68cda3f022ba

==> Search status
OK: Search engine: db

==> Reindex
OK: Reindex completed (indexed=902)

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
OK: Created ECO product: aac0832d-195b-49c6-827e-7ca8bc65291e

==> Create ECO
OK: Created ECO: 2c89f5e3-7e2d-4a58-9612-e5611a944d3c

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
OK: Created Part: b91d4a8e-0cf1-4a6d-97d2-154c86c4c755

==> Upload file
OK: Uploaded file: a09887e5-23da-4bb1-8c39-8631e32df68e

==> Create ECO stage + ECO
OK: Created ECO: bf87c1d0-2d1b-495c-8549-e77c33e880d3

==> Create job
OK: Created job: 20039796-7aec-4435-97e8-e61b760306d7

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
NEW_TENANT: tenant-provision-1769502112
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
OK: Tenant created: tenant-provision-1769502112

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
OK: Created assembly: 2ac52bc4-91d3-4ec9-87ec-59e7ce4cf7b5
OK: Created sub-assembly: 3f723e39-3561-4c3f-b5a6-02f668e31ca0
OK: Created component: cf6afa64-d228-4cd4-a5f0-e971f3379e46
OK: Created second assembly: c20817bc-c851-40ec-accf-619a7e572291

==> Build BOM hierarchy
OK: Added sub-assembly to assembly
OK: Added component to sub-assembly
OK: Added component to second assembly

BOM Structure:
  ASSEMBLY (2ac52bc4-91d3-4ec9-87ec-59e7ce4cf7b5)
    └── SUB-ASSEMBLY (3f723e39-3561-4c3f-b5a6-02f668e31ca0)
          └── COMPONENT (cf6afa64-d228-4cd4-a5f0-e971f3379e46)
  ASSEMBLY2 (c20817bc-c851-40ec-accf-619a7e572291)
    └── COMPONENT (cf6afa64-d228-4cd4-a5f0-e971f3379e46)

==> Test Where-Used (non-recursive)
Where-used response:
  item_id: cf6afa64-d228-4cd4-a5f0-e971f3379e46
  count: 2
OK: Non-recursive where-used: found 2 direct parents
Parent IDs found:
  - 3f723e39-3561-4c3f-b5a6-02f668e31ca0
  - c20817bc-c851-40ec-accf-619a7e572291

==> Test Where-Used (recursive)
Recursive where-used response:
  count: 3
OK: Recursive where-used: found 3 parents
Parents by level:
  Level 1: Sub-Assembly for Where-Used Test 1769502114
  Level 2: Assembly for Where-Used Test 1769502114
  Level 1: Second Assembly for Where-Used Test 1769502114

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
SKIP: UI Product Detail (RUN_UI_AGG=0)
SKIP: UI Product Summary (RUN_UI_AGG=0)
SKIP: UI Where-Used (RUN_UI_AGG=0)
SKIP: UI BOM (RUN_UI_AGG=0)
SKIP: UI Docs Approval (RUN_UI_AGG=0)
SKIP: UI Docs ECO Summary (RUN_UI_AGG=0)

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
OK: Created parents: A=84e1b443-a1ac-4d0b-a246-a03041ce8fc8, B=e189d942-13e3-4d94-9c99-faabc9209aca

==> Create child items
OK: Created children: X=8f97015e-9520-4189-a343-8e244291a4a5, Y=93143a09-8445-4820-a04a-98ae118f4955, Z=0adf5ef5-9852-4784-b5f7-a21a9191ab58

==> Build BOM A (baseline)
OK: BOM A created

==> Build BOM B (changed + added)
OK: BOM B created

==> Create substitute for CHILD_X in BOM B
OK: Substitute added: 6b20b02c-4d70-4169-ae7a-aeead6cdf18e

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
OK: Created Parts: left=0807482f-9e70-4012-a055-5c7c44c1fcff right=7630bccc-8d3d-42e5-b3a0-85c289f044d2 child=7ce9c77b-5ad2-451c-ba4b-311d61af33df sub=48097d1b-2a25-41e4-bed1-28cfd45b5cdd

==> Add BOM lines
OK: Added BOM lines: left_rel=fd971fe4-f4c8-4339-95da-67c3fc20893b right_rel=f2958140-6ad9-4d01-ab41-b2f27f64af51

==> Add substitute to left BOM line
OK: Added substitute: 6ed37f07-b7f3-48d8-bb36-6fe1738d2482

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
OK: Created parent=74940ff1-7068-41d8-9848-5054c789b241 children=d486071a-ba05-4fef-983c-b14bb2532d63,970f2768-bbc4-49b9-993d-e2ac142f33df

==> Build BOM (A -> B, C)
OK: BOM created

==> Create baseline
Baseline snapshot validated
OK: Baseline created: 697bc620-975c-479a-ba19-d732bfbe5d16

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
OK: Created parent=679a021a-f6ba-4298-8882-e1d72caf53c8 child=689dc76c-5b68-4b72-8d00-e8f7d766daf5 substitutes=59347d6d-4011-4c34-bae4-0173aa29d5fe,421ebfee-5d49-4bb6-ad26-c641c3de7f66

==> Create BOM line (parent -> child)
OK: Created BOM line: b00cebeb-5e47-42ec-b3e0-9afce2792104

==> Add substitute 1
OK: Added substitute 1: 4753a919-242a-443f-b860-93a6d63b0a81

==> List substitutes (expect 1)
OK: List count=1

==> Add substitute 2
OK: Added substitute 2: 47cf9a03-6dc1-4e8c-9152-77bc6e7621a6

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
OK: Created EBOM root=7bc5e18f-0a03-4ba5-b09c-61d7281cbcac child=45eb59c9-4abe-4147-ae59-e89edd3a2ea9 substitute=8833e24a-7294-4009-b9cd-df66fab0bcd9

==> Create EBOM BOM line
OK: EBOM BOM line: 291a76fc-2fcb-4803-aed6-7101422b88e2

==> Add substitute to EBOM BOM line
OK: EBOM substitute relation: 141677fa-83bc-4448-95e6-75f635a4da92

==> Convert EBOM -> MBOM
OK: MBOM root: 2a126a13-3b0f-4f1a-8f2d-27d05ca63584

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
OK: Created parts A=ef4571ae-9d0c-452b-8d9e-7365cd8230c3 B=8f18eb3a-b379-4d99-824b-182705045dde C=195bcd60-e10a-4be7-a8b7-7c9798b38acc

==> Add equivalent A <-> B
OK: Added equivalent A-B: 3fc1cd8b-20bc-434d-a762-594e319e8a12

==> Add equivalent A <-> C
OK: Added equivalent A-C: 37eda997-4731-48f5-8cc9-e246d8afb92f

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
OK: Created Part: e73de207-6480-40a0-8dda-a52f340ac056

==> Init version
OK: Init version: 2ac719b0-eaef-464b-8078-412f2909cc4d

==> Upload file
OK: Uploaded file: b01cb682-906a-4a45-b586-ef25d20594e7

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
S8 (Ops Monitoring)       SKIP
S7 (Multi-Tenancy)        PASS
S7 (Tenant Provisioning)  PASS
Where-Used API            PASS
UI Product Detail         SKIP
UI Product Summary        SKIP
UI Where-Used             SKIP
UI BOM                    SKIP
UI Docs Approval          SKIP
UI Docs ECO Summary       SKIP
BOM Compare               PASS
Baseline                  PASS
BOM Substitutes           PASS
MBOM Convert              PASS
Item Equivalents          PASS
Version-File Binding      PASS

----------------------------------------------
PASS: 44  FAIL: 0  SKIP: 8
----------------------------------------------

ALL TESTS PASSED
