
## verify_product_detail.sh
```
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
OK: Created Part: 1394d185-c116-4b6c-9235-1b6d50d69c4e

==> Init version
OK: Init version: 8854b9a2-d240-4818-a174-f2fff563e0b0

==> Upload file
OK: Uploaded file: 73bdab2b-7276-4cdd-9a12-06032b802fd6

==> Attach file to item
OK: File attached to item

==> Fetch product detail
Product detail mapping: OK

==============================================
Product Detail Mapping Verification Complete
==============================================
ALL CHECKS PASSED
```
result: 0
status: PASS

## verify_product_ui.sh
```
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
OK: Created Parts: parent=f9d4db2c-7c55-4c8a-8665-00ad44a2490f child=e7c444b6-854e-46df-890e-9ca1bbe1492e

==> Add BOM child
OK: Added BOM line: 982ebe01-e9c6-43c6-a061-ea3275a9231b

==> Fetch parent product detail with BOM summary

==> Fetch child product detail with where-used summary
Product UI aggregation: OK

==============================================
Product UI Aggregation Verification Complete
==============================================
ALL CHECKS PASSED
```
result: 0
status: PASS

## verify_where_used_ui.sh
```
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
OK: Created Parts: grand=6a8be934-921c-4ce3-93bf-213a061ad9ac parent=15a2cb21-c975-43b8-b824-5d7fe8893328 child=e31ae261-2619-4143-8586-89adc74c715c

==> Add BOM lines
OK: Added BOM lines: parent_rel=01dc1bcd-a42c-4d45-8c39-c286047cb174 grand_rel=1b59aa54-b0d2-4d2c-9689-049ba1797e47

==> Where-used (recursive)
Where-used UI payload: OK

==============================================
Where-Used UI Verification Complete
==============================================
ALL CHECKS PASSED
```
result: 0
status: PASS

## verify_bom_ui.sh
```
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
OK: Added substitute: a7e84b95-c9f1-4c06-9190-205fe0f0d271

==> Where-used

==> BOM compare (include child fields)

==> Substitutes list
BOM UI endpoints: OK

==============================================
BOM UI Verification Complete
==============================================
ALL CHECKS PASSED
```
result: 0
status: PASS

## verify_docs_approval.sh
```
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
OK: Created Part: 08a9aecb-0dc2-4739-8ea0-50c47f578a91

==> Upload file with metadata
OK: Uploaded file: 0202cd40-da4e-4717-8347-6a1c1df2d284

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
OK: Created Document: 157bdd75-9f57-4bd1-81bf-5f3bd52a3d6d

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
OK: Created stage: f62434f2-ffdb-44ad-aa0a-c124976d2984

==> Create ECO product
OK: Created product: 351bc50b-0a99-4cc2-a543-9dc7472deb56

==> Create ECO
OK: Created ECO: f9468bb0-811c-4b98-a4a8-00bda610441c

==> Move ECO to approval stage
OK: Moved ECO to stage

==> Approve ECO
OK: Approved ECO: c4cd1379-d4c0-4e66-a8bc-53aeba1224fd

==> Verify ECO state and approvals
Approval flow: OK

==============================================
Docs + Approval Verification Complete
==============================================
ALL CHECKS PASSED
```
result: 0
status: PASS

## verify_docs_eco_ui.sh
```
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
OK: Created Part=19a75439-5ca4-4bdb-926e-0d4e2fadda05 Document=94742927-ae65-4046-bb43-9108fd8f9148

==> Link Document to Part
OK: Created Document relation

==> Create ECO stage and ECO
OK: Created ECO=10fc840f-83ef-4010-88a9-5094c6328732 stage=c297a126-c005-475e-a9e8-739397737d88

==> Fetch product detail with document + ECO summary
Docs + ECO UI summary: OK

==============================================
Docs + ECO UI Summary Verification Complete
==============================================
ALL CHECKS PASSED
```
result: 0
status: PASS
