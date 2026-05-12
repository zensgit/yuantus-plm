# SolidWorks CAD Material Sync Client

This package contains the SDK-free R1.1 SolidWorks client skeleton for CAD
Material Sync.

It does not prove real Windows SolidWorks behavior. Runtime acceptance still
requires the Windows evidence template and validator:

```bash
python3 scripts/validate_cad_material_solidworks_windows_evidence.py \
  evidence/solidworks-cad-material-sync-windows-evidence.md
```

## Architecture

The skeleton separates testable client rules from the Windows-only SolidWorks
API surface:

- `ISolidWorksMaterialDocumentGateway` is the seam that a future Add-in/COM
  adapter must implement.
- `SolidWorksMaterialFieldAdapter` extracts canonical material fields from
  SolidWorks custom properties, cut-list properties, and table rows.
- `SolidWorksDiffPreviewClient` sends the local document snapshot to
  `/api/v1/plugins/cad-material-sync/diff/preview` with
  `cad_system=solidworks`.
- `SolidWorksDiffConfirmationViewModel` converts the preview response into
  UI-ready rows and produces either confirmed `write_cad_fields` or an empty
  cancel/no-op write package.
- `SolidWorksMaterialPullWorkflow` orchestrates field extraction, diff preview,
  confirmation, and the final apply boundary without depending on SolidWorks
  COM or WPF.
- `SolidWorksWriteBackPlan` accepts only confirmed `write_cad_fields` keys and
  rejects AutoCAD primary labels.

## Future Windows Binding

The real Windows adapter should back `ISolidWorksMaterialDocumentGateway` with
SolidWorks Add-in/COM calls:

- Use `CustomPropertyManager.GetAll3` or equivalent bulk enumeration for the
  available property key set.
- Use `CustomPropertyManager.Get6` for resolved/evaluated property reads when
  the current document requires evaluated values.
- Read cut-list or table-backed values when part-level custom properties are
  absent.
- Write only the SolidWorks keys returned by `write_cad_fields`.
- Save, close, reopen, and verify persistence during Windows smoke.

## Current Guardrail

The parent TODO items for SolidWorks field reading and local confirmation UI
must remain unchecked until real Windows evidence is accepted. This skeleton is
only the implementation seam for the next Windows-capable slice.
