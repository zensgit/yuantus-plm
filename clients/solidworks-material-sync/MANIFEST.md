# SolidWorks CAD Material Sync Client Manifest

Status: SDK-free R1.1 skeleton. This package is not Windows SolidWorks runtime
acceptance evidence.

## Source Files

- `SolidWorksMaterialSync/SolidWorksMaterialSync.csproj` - SDK-free C# project
  definition for the client seam.
- `SolidWorksMaterialSync/ICadMaterialFieldAdapter.cs` - CAD field adapter
  interface mirrored from the AutoCAD client boundary.
- `SolidWorksMaterialSync/ISolidWorksMaterialDocumentGateway.cs` - gateway that
  a future Windows Add-in/COM adapter must back with SolidWorks API calls.
- `SolidWorksMaterialSync/SolidWorksMaterialFieldMapper.cs` - SolidWorks key to
  canonical material field mapping.
- `SolidWorksMaterialSync/SolidWorksMaterialFieldAdapter.cs` - field
  extraction/write-back adapter over the gateway seam.
- `SolidWorksMaterialSync/SolidWorksDiffPreviewClient.cs` - diff-preview
  request seam pinned to `cad_system=solidworks`.
- `SolidWorksMaterialSync/SolidWorksWriteBackPlan.cs` - confirmation write-back
  boundary that accepts only SolidWorks `write_cad_fields`.

## Explicit Non-Deliverables

- No compiled DLLs.
- No SolidWorks interop assemblies.
- No Windows registry files.
- No screenshots, logs, or CAD sample files.
- No filled Windows evidence.

