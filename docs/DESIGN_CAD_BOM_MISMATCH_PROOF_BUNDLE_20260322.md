# CAD BOM Mismatch Proof Bundle Design

**Date**: 2026-03-22
**Branch**: `feature/codex-cad-bom-mismatch-proof`

## Goal

Extend the current CAD BOM contract so operators can answer one bounded
question without opening raw JSON or rebuilding a compare flow by hand:

- does the imported CAD BOM still match the current live BOM,
- if not, what kind of drift exists,
- which recovery actions are safe,
- and which proof files should be exported before changing anything.

This increment stays read-only on the mismatch side. It does not add a BOM
apply wizard or direct line editing.

## Reference Anchors

- Odoo compare BOM exposes coarse compare modes and difference vocabulary, but
  keeps remediation inside the wizard flow:
  - `references/odoo18-enterprise-main/addons/plm_compare_bom/wizard/compare_bom.py`
- Odoo pack-and-go shows how zip export can become an operator handoff surface,
  but it is not a live CAD BOM mismatch proof contract:
  - `references/odoo18-enterprise-main/addons/plm_pack_and_go/wizard/pack_and_go_wizard.py`
- DocDoku import preview and import status split preview, polling, warnings,
  and errors across separate DTO and UI surfaces:
  - `references/docdoku-plm/docdoku-plm-server/docdoku-plm-server-rest/src/main/java/com/docdoku/plm/server/rest/dto/ImportPreviewDTO.java`
  - `references/docdoku-plm/docdoku-plm-front/app/product-management/js/views/product-instances/product_instances_importer.js`
  - `references/docdoku-plm/docdoku-plm-front/app/js/common-objects/views/part/import_status_view.js`
  - `references/docdoku-plm/docdoku-plm-front/app/js/common-objects/templates/part/import_status.html`

The Yuantus design deliberately goes one step further: keep the raw payload and
summary layers, but also expose one stable mismatch/proof contract that is easy
to automate, export, and attach to incidents or customer verification.

## Scope

### 1. Derive a stable mismatch contract

Add `build_cad_bom_mismatch_analysis(...)` on top of the existing
`prepare_cad_bom_payload(...)` and live BOM compare flow.

The analysis:

- normalizes the CAD BOM payload first
- builds a compare tree by matching CAD part numbers to existing Part items
- compares that tree with the current live BOM using
  `line_key=child_id_find_refdes`
- groups drift into operator-facing counters instead of exposing only raw diff
  rows

Stable statuses:

- `match`
- `mismatch`
- `unresolved`
- `missing`

Stable fields:

- `status`
- `reason`
- `analysis_scope`
- `line_key`
- `recoverable`
- `contract_status`
- `summary`
- `compare_summary`
- `grouped_counters`
- `rows`
- `delta_preview`
- `issue_codes`
- `mismatch_groups`
- `recovery_actions`
- `live_bom`

Even empty/unresolved states return the same shape so export and UI clients do
not have to guess which keys exist.

### 2. Extend the CAD BOM response

`GET /api/v1/cad/files/{file_id}/bom` now includes `mismatch` alongside the
existing:

- `import_result`
- `bom`
- `summary`

This keeps the current derived CAD BOM surface canonical. Clients that already
consume `/bom` do not need a second fetch just to know whether live BOM drift
exists.

### 3. Add a dedicated mismatch endpoint

Add `GET /api/v1/cad/files/{file_id}/bom/mismatch`.

This read-only endpoint returns:

- the stable mismatch analysis
- `file_id`
- `item_id`
- follow-up links for:
  - structured BOM
  - mismatch
  - export
  - review
  - history
  - reimport

This is intentionally narrower than a full compare wizard. It is an operator
inspection surface, not an edit workflow.

### 4. Upgrade the export bundle into a proof bundle

`GET /api/v1/cad/files/{file_id}/bom/export?export_format=zip|json` now exports
the mismatch surface and a proof manifest.

New proof-oriented files:

- `mismatch.json`
- `live_bom.json`
- `mismatch_delta.csv`
- `mismatch_rows.csv`
- `mismatch_issue_codes.csv`
- `mismatch_recovery_actions.csv`
- `mismatch_delta_preview.json`
- `proof_manifest.json`

`proof_manifest.json` captures:

- bundle kind/version
- current mismatch status/reason
- `line_key`
- `analysis_scope`
- recoverability
- grouped counters
- mismatch issue codes
- proof file inventory

This turns the export from a generic support zip into a bounded mismatch proof
artifact.

### 5. Update the operator runbook

`docs/RUNBOOK_CAD_BOM_OPERATIONS.md` must describe:

- when to use `/bom`
- when to use `/bom/mismatch`
- how to interpret `match|mismatch|unresolved|missing`
- when to export the proof bundle before reimport

## Why This Surpasses Reference Detail

This is not broader product scope. It is better operational detail.

- Odoo compare exposes compare intent, but not a reusable mismatch proof
  contract tied to live API responses and export artifacts.
- DocDoku import status exposes pending/success/failure and warnings, but the
  operator has to reconstruct proof context across multiple surfaces.
- Yuantus now provides one read-only mismatch surface plus one bounded proof
  bundle. That is stronger for private deployments, support handoff, and
  regression evidence because the contract is stable and exportable.

## Non-Goals

- No BOM apply/merge endpoint
- No direct modification of live BOM rows from the CAD surface
- No change to raw `GET /api/v1/file/{file_id}/cad_bom`
- No connector payload schema rewrite

## Files

- `src/yuantus/meta_engine/services/cad_bom_import_service.py`
- `src/yuantus/meta_engine/web/cad_router.py`
- `src/yuantus/meta_engine/tests/test_cad_bom_import_service.py`
- `src/yuantus/meta_engine/tests/test_cad_bom_router.py`
- `docs/RUNBOOK_CAD_BOM_OPERATIONS.md`
- `docs/DESIGN_CAD_BOM_MISMATCH_PROOF_BUNDLE_20260322.md`
- `docs/DEV_AND_VERIFICATION_CAD_BOM_MISMATCH_PROOF_BUNDLE_20260322.md`
