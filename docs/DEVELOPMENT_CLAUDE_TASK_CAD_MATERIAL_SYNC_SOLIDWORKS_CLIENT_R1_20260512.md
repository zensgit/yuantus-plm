# Claude Taskbook: CAD Material Sync SolidWorks Client R1

## 1. Purpose

Implement the real Windows SolidWorks client path for CAD Material Sync without
changing the already-merged server plugin contracts.

This taskbook is intentionally implementation-facing. It exists because the
repository now has SDK-free SolidWorks fixtures and Windows evidence gates, but
the real SolidWorks Add-in/COM runtime is still not implemented or accepted.

## 2. Current Baseline

- Server plugin API is already available under `/api/v1/plugins/cad-material-sync`.
- SolidWorks canonical field behavior is pinned by
  `docs/samples/cad_material_solidworks_fixture.json`.
- SolidWorks diff-confirm write package behavior is pinned by
  `docs/samples/cad_material_solidworks_diff_confirm_fixture.json`.
- Windows evidence shape is pinned by
  `docs/CAD_MATERIAL_SYNC_SOLIDWORKS_WINDOWS_VALIDATION_EVIDENCE_TEMPLATE_20260511.md`.
- The TODO parent items remain incomplete until real SolidWorks evidence is
  produced and reviewed.

## 3. Target Output

Create a new SolidWorks client surface under:

`clients/solidworks-material-sync/`

The exact project structure may mirror the AutoCAD client where useful, but it
must not depend on AutoCAD SDK symbols, AutoCAD field names, or AutoCAD command
registration.

Required deliverables:

- SolidWorks Add-in or COM integration project.
- SolidWorks field adapter implementation.
- Local diff preview and confirmation UI.
- Write-back implementation for confirmed `write_cad_fields`.
- Windows smoke evidence filled from the real Add-in/COM path.
- Development and verification MD for the implementation PR.

## 4. R1 Scope

### 4.1 Field Read Add-in/COM Adapter

Implement SolidWorks property and table extraction through the SolidWorks API.

Required behavior:

- Connect to the active SolidWorks document through the supported Add-in/COM
  path.
- Read part-level custom properties through `CustomPropertyManager`.
- Prefer `Get6` when evaluated values are needed; use `GetAll3` or equivalent
  bulk enumeration when collecting the available custom-property key set.
- Read cut-list or table values for length, width, thickness, and other
  profile-relevant material fields when the value is not present at part level.
- Normalize the read output to the same canonical field names asserted by the
  SDK-free fixture.
- Preserve raw SolidWorks keys such as `SW-Material@Part`,
  `SW-Specification@Part`, and cut-list/table source keys for evidence.

### 4.2 Diff Preview And Confirmation UI

Implement the local confirmation path against:

`POST /api/v1/plugins/cad-material-sync/diff/preview`

Required behavior:

- Send `cad_system=solidworks`.
- Render added, changed, cleared, and unchanged fields in a local confirmation
  UI.
- Show the final `write_cad_fields` package before any COM write operation.
- Cancel must be a no-op and must not save the SolidWorks document.
- Confirm must write only keys present in `write_cad_fields`.
- Empty string writes are allowed only when the preview explicitly classifies a
  field as cleared.

### 4.3 COM Write-Back

Required behavior:

- Write part-level custom properties through `CustomPropertyManager`.
- Use the SolidWorks key names returned in `write_cad_fields`.
- Do not translate primary SolidWorks write keys back to AutoCAD labels such as
  `材料`, `规格`, `长`, `宽`, or `厚`.
- Save and reopen the test document during Windows smoke to prove persistence.
- Record before/after values for every changed SolidWorks property.

### 4.4 Windows Smoke Evidence

The implementation PR is not accepted until a real Windows evidence file passes:

`python3 scripts/validate_cad_material_solidworks_windows_evidence.py <filled-evidence.md>`

Minimum smoke:

- Build the SolidWorks client project.
- Load the Add-in or COM integration in SolidWorks.
- Read custom properties from a sanitized part document.
- Read at least one cut-list or table-backed value.
- Call `/api/v1/plugins/cad-material-sync/diff/preview`.
- Confirm one write package.
- Exercise cancel/no-op behavior.
- Save, close, reopen, and verify persisted values.

## 5. Implementation Boundaries

Allowed:

- New files under `clients/solidworks-material-sync/`.
- Tests that run without SolidWorks SDK by validating project structure,
  configuration files, fixture compatibility, and evidence shape.
- Windows-only build notes and scripts when they do not require secrets.
- Reuse of shared client abstractions from the AutoCAD client if copied or
  extracted cleanly.

Forbidden:

- Generated binary artifacts, compiled DLLs, logs, screenshots, or CAD sample
  files committed to the repository.
- Secrets, bearer tokens, tenant tokens, workstation usernames, or internal file
  paths in evidence or docs.
- Marking the SolidWorks TODO parent items complete without accepted real Windows evidence.
- Mock fixture output represented as real SolidWorks evidence.
- Server API behavior changes unless a separate contract justifies them first.
- AutoCAD command names as the SolidWorks primary UX.

## 6. Suggested PR Split

### R1.1 Field Adapter Skeleton

Create the client project, configuration surface, and field adapter with
SDK-free structure tests.

Exit criteria:

- `clients/solidworks-material-sync/` exists.
- Field adapter documents the `CustomPropertyManager` read path.
- Tests prove AutoCAD SDK symbols are not imported by the SolidWorks client.
- No TODO parent item is marked complete.

### R1.2 Diff Preview And Write-Back

Wire the local confirmation UI and confirmed COM write package.

Exit criteria:

- UI consumes `/api/v1/plugins/cad-material-sync/diff/preview`.
- Requests include `cad_system=solidworks`.
- Confirm writes only `write_cad_fields`.
- Cancel is a no-op.
- Tests cover 4xx/error handling and local no-op behavior where SDK-free tests
  can do so.

### R1.3 Windows Evidence Closeout

Run real Windows SolidWorks smoke and fill the evidence template.

Exit criteria:

- Filled evidence passes
  `scripts/validate_cad_material_solidworks_windows_evidence.py`.
- Evidence uses sanitized paths and no secrets.
- The TODO parent items are only checked when real evidence is accepted.

## 7. Required Local Verification

Run from repository root:

```bash
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_fixture_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_diff_confirm_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_windows_evidence_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_client_taskbook_contracts.py
```

```bash
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

```bash
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py
```

```bash
git diff --check
```

## 8. Windows Verification

Run on a Windows workstation with SolidWorks installed:

```powershell
python scripts\validate_cad_material_solidworks_windows_evidence.py `
  evidence\solidworks-cad-material-sync-windows-evidence.md
```

Acceptance requires the validator to print:

`OK: CAD material SolidWorks Windows evidence shape is acceptable`

The evidence must be reviewed before any TODO parent item is marked complete.

## 9. Review Checklist

- `clients/solidworks-material-sync/` contains only source, config, docs, and
  tests.
- Field read path uses SolidWorks `CustomPropertyManager`.
- The adapter handles both part-level properties and cut-list/table-backed
  values.
- `/api/v1/plugins/cad-material-sync/diff/preview` is called with
  `cad_system=solidworks`.
- Confirm writes only `write_cad_fields`.
- Cancel/no-op does not save or mutate the SolidWorks document.
- No AutoCAD primary field labels appear in the SolidWorks write package.
- Evidence is generated from real SolidWorks, not fixture output.
- The TODO parent items stay unchecked until evidence is accepted.

## 10. Non-Goals

- No server-side profile redesign.
- No new database migration.
- No AutoCAD client refactor.
- No CAD binary artifact storage.
- No production rollout toggle.
- No claim that Windows smoke is complete from macOS-only tests.

## 11. Handoff To Claude

Give Claude this taskbook plus the three existing SolidWorks contracts. The
worker may implement R1.1 and R1.2 on macOS if it avoids SDK-dependent builds,
but R1.3 requires a Windows SolidWorks workstation.

The first implementation PR should stop before evidence acceptance if no
Windows machine is available. In that case it must leave both parent TODO items
unchecked and document the blocker explicitly.
