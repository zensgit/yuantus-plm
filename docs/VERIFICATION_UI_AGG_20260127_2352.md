# UI Aggregation Verification (2026-01-27 23:52 +0800)

## verify_product_detail.sh
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
OK: Created Part: 2c45c687-7150-436c-b6c2-359c90bc55da

==> Init version
OK: Init version: 651f372e-e019-4cb5-aa17-636b25725435

==> Upload file
OK: Uploaded file: d415a923-b061-4504-b8f2-a15b203ff28c

==> Attach file to item
OK: File attached to item

==> Fetch product detail
Product detail mapping: OK

==============================================
Product Detail Mapping Verification Complete
==============================================
ALL CHECKS PASSED

## verify_product_ui.sh
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
OK: Created Parts: parent=c4dd7507-7522-4b47-ba0e-7e29e75f8727 child=48e96d99-a16e-41f0-8e84-203ce5a82769

==> Add BOM child
OK: Added BOM line: e85fe3a2-21c2-4b23-b11e-a0e10230d996

==> Fetch parent product detail with BOM summary

==> Fetch child product detail with where-used summary
Product UI aggregation: OK

==============================================
Product UI Aggregation Verification Complete
==============================================
ALL CHECKS PASSED

## verify_where_used_ui.sh
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
OK: Created Parts: grand=b053a073-a380-4b6b-94c6-f1ab7d72dde3 parent=d9e7dbd4-a7a2-4d58-8f6a-31c9f5ea6ca0 child=76a2b54d-30e7-4967-8ee5-fff3aa227452

==> Add BOM lines
OK: Added BOM lines: parent_rel=8236f4e9-edb5-467c-9b4a-8274acaeb4ec grand_rel=72c92d99-93bb-44e3-9008-6684c724cd8e

==> Where-used (recursive)
Where-used UI payload: OK

==============================================
Where-Used UI Verification Complete
==============================================
ALL CHECKS PASSED

## verify_bom_ui.sh
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
OK: Added substitute: fa544e89-6a66-4a2f-9264-84419bfb4906

==> Where-used

==> BOM compare (include child fields)

==> Substitutes list
BOM UI endpoints: OK

==============================================
BOM UI Verification Complete
==============================================
ALL CHECKS PASSED

## verify_docs_approval.sh
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
OK: Created Part: 13e295d3-9808-42ff-9bd9-4a0e2e4a2c03

==> Upload file with metadata
OK: Uploaded file: 28fc6e7d-745a-4f95-b2e7-836e457950c9

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
OK: Created Document: 531829b4-9bf2-4d9d-a2a8-ef8981129f56

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
OK: Created stage: 584412db-1cb2-4fca-9ccc-0208237963e3

==> Create ECO product
OK: Created product: 7fd0e576-84c2-46f0-a6d6-9654fdda2a42

==> Create ECO
OK: Created ECO: 2a62e914-c6e2-41a6-b804-5ed74ce1a4a4

==> Move ECO to approval stage
OK: Moved ECO to stage

==> Approve ECO
OK: Approved ECO: 3640a482-19d9-405e-b1a7-02d8a8c384b9

==> Verify ECO state and approvals
Approval flow: OK

==============================================
Docs + Approval Verification Complete
==============================================
ALL CHECKS PASSED

## verify_docs_eco_ui.sh
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
OK: Created Part=2977f1b2-2ef7-47d0-a044-61c31698f34f Document=40037ae8-60d5-4bea-a71d-a36602f22540

==> Link Document to Part
OK: Created Document relation

==> Create ECO stage and ECO
OK: Created ECO=289ce731-1219-41a3-87dd-5736e9c95255 stage=f5d9fce6-c35d-47ed-946e-d3a0f81dea7e

==> Fetch product detail with document + ECO summary
Docs + ECO UI summary: OK

==============================================
Docs + ECO UI Summary Verification Complete
==============================================
ALL CHECKS PASSED
