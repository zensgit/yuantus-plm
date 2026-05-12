# Windows SolidWorks Validation Guide

## Purpose

This guide is the Windows-side execution package for the CAD Material Sync
SolidWorks client path.

It does not replace macOS-side service, fixture, or contract tests. It verifies
the remaining behavior that only a real Windows SolidWorks workstation can
prove: build, Add-in/COM load, custom-property read, cut-list/table read,
diff-preview confirmation, COM write-back, save/reopen persistence, and final
evidence acceptance.

## Status

Status: template/runbook only; not validation evidence.

Do not mark SolidWorks field reading, local confirmation UI, COM write-back, or
Windows runtime acceptance complete from this guide alone.

## Prerequisites

- Windows 10/11 x64.
- SolidWorks desktop installed.
- SolidWorks version and service pack recorded for evidence.
- Visual Studio or Build Tools with MSBuild and .NET desktop build tools.
- Network access from Windows to the Yuantus server.
- A sanitized test part document, not a production CAD file.
- Yuantus server with `yuantus-cad-material-sync` enabled.
- Python 3 available for evidence validation.

## Preflight

Run from `clients\solidworks-material-sync`:

```powershell
powershell -ExecutionPolicy Bypass -File .\verify_solidworks_windows_preflight.ps1
```

If SolidWorks is installed in a custom directory:

```powershell
powershell -ExecutionPolicy Bypass -File .\verify_solidworks_windows_preflight.ps1 `
  -SolidWorksInstallDir "D:\Dassault Systemes\SOLIDWORKS"
```

If the implementation project uses a custom path:

```powershell
powershell -ExecutionPolicy Bypass -File .\verify_solidworks_windows_preflight.ps1 `
  -ProjectPath ".\SolidWorksMaterialSync\SolidWorksMaterialSync.csproj"
```

Expected result:

```text
Preflight passed. The Windows machine is ready for SolidWorks material sync build/smoke.
```

## Build

The current repository contains the SDK-free source seam. A future Windows
implementation PR must add the real Add-in/COM project or extend the existing
project with the required SolidWorks interop references.

When that project exists, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\verify_solidworks_windows_preflight.ps1 -RunBuild
```

Pass criteria:

- MSBuild is found.
- Project restores and compiles.
- Output DLL path is recorded.
- No compiled DLL is committed back to the repository.

## SolidWorks Load Smoke

1. Close all SolidWorks instances.
2. Start SolidWorks.
3. Load the Add-in through the chosen Add-in/COM registration path.
4. Open the sanitized test part.
5. Verify the Add-in command/menu is visible.

Pass criteria:

- SolidWorks loads the Add-in without COM registration or managed assembly
  errors.
- The Add-in logs its active document path or sanitized document label.
- No production file path, token, or customer name is written to evidence.

## Field Read Smoke

Use a sanitized part document with:

- part-level custom properties:
  - `SW-Part Number@Part`
  - `SW-Description@Part`
  - `SW-Material@Part`
  - `SW-Thickness@Part`
- cut-list or table-backed fields:
  - `SW-Length@CutList` or `SW-Length@Part`
  - `SW-Width@CutList` or `SW-Width@Part`
- optional:
  - `SW-Specification@Part`
  - `SW-HeatTreatment@Part`

Pass criteria:

- Reads come from a real SolidWorks document.
- Part-level reads use the `CustomPropertyManager` path.
- Evaluated values use the resolved-value read path such as `Get6` when needed.
- Available key enumeration uses `GetAll3` or an equivalent bulk property
  enumeration.
- Cut-list or table-backed values are captured when part-level values are
  absent.

## Diff Preview And Confirmation Smoke

Run the SolidWorks pull workflow against a known test item.

Expected API path:

`POST /api/v1/plugins/cad-material-sync/diff/preview`

Expected request boundary:

- `cad_system=solidworks`
- current CAD fields from the active document snapshot.
- profile `sheet` for the first smoke unless another profile is explicitly
  documented.

Pass criteria:

- A local confirmation UI opens before any write.
- UI rows show field key, current value, target value, and status.
- The UI displays the final `write_cad_fields` package.
- Cancel returns no write package and does not save the SolidWorks document.
- Confirm writes only keys present in `write_cad_fields`.
- Explicit clear writes an empty string only when preview marks the field
  cleared.

## Save/Reopen Persistence Smoke

After confirm:

1. Save the test part.
2. Close the document.
3. Reopen the document.
4. Read the same custom properties again.

Pass criteria:

- `SW-Specification@Part` or the target field keeps the confirmed value.
- Unchanged fields remain unchanged.
- No AutoCAD primary labels such as `材料`, `规格`, `长`, `宽`, or `厚` are
  written as SolidWorks primary keys.

## Evidence Validation

Copy the repository evidence template and fill it with sanitized values:

`docs/CAD_MATERIAL_SYNC_SOLIDWORKS_WINDOWS_VALIDATION_EVIDENCE_TEMPLATE_20260511.md`

Then run from repository root:

```powershell
python scripts\validate_cad_material_solidworks_windows_evidence.py `
  evidence\solidworks-cad-material-sync-windows-evidence.md
```

Expected success:

```text
OK: CAD material SolidWorks Windows evidence shape is acceptable
```

## Evidence To Capture

- Preflight output.
- SolidWorks version and service pack.
- Build command and result.
- Add-in/COM load method and result.
- Sanitized test document description.
- Custom property read result.
- Cut-list or table read result.
- Diff preview UI result.
- Confirm write command result.
- Cancel path result.
- Before/after SolidWorks property values.
- Save/reopen result.
- Yuantus dry-run and real-write log paths.

Do not include secrets, bearer tokens, tenant tokens, workstation usernames,
production CAD file paths, or customer names.

## Failure Triage

| Symptom | Likely Cause | Check |
| --- | --- | --- |
| Preflight cannot find SolidWorks | Install path mismatch | Run with `-SolidWorksInstallDir` |
| MSBuild not found | Build Tools missing | Install Visual Studio Build Tools .NET desktop workload |
| Add-in fails to load | COM registration or interop mismatch | Check Add-in registration and SolidWorks version |
| Property read returns empty values | Wrong property scope | Compare part-level and cut-list property managers |
| Diff preview returns AutoCAD labels | Wrong `cad_system` | Verify request contains `cad_system=solidworks` |
| Confirm changes too many fields | UI bypassed `write_cad_fields` | Inspect final write package before COM write |
| Save/reopen loses value | Document not saved or property scope wrong | Repeat read after close/reopen |
| Evidence validator fails | Missing real smoke field | Fill required evidence field or rerun smoke |

## Exit Criteria

SolidWorks runtime support can be marked complete only when:

- Preflight passes on the Windows machine.
- Add-in/COM project builds.
- SolidWorks loads the client.
- Real custom properties and cut-list/table fields are read.
- Diff preview UI opens before write-back.
- Cancel is proven to be a no-op.
- Confirm writes only `write_cad_fields`.
- Save/reopen proves persistence.
- Filled evidence passes
  `scripts/validate_cad_material_solidworks_windows_evidence.py`.

