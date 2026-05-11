# Yuantus AutoCAD Material Sync Client Manifest

## Purpose

This directory is the Yuantus-owned AutoCAD client package for CAD Material Sync. It contains the AutoCAD .NET plugin source, Windows build and validation scripts, macOS contract verification scripts, and user-facing guides needed to continue development from a fresh Git clone.

## Source Layout

- `CADDedupPlugin/` - AutoCAD .NET Framework plugin project.
- `CADDedupPlugin/MaterialSyncApiClient.cs` - client for `/api/v1/plugins/cad-material-sync`.
- `CADDedupPlugin/CadMaterialFieldMapper.cs` - SDK-free CAD field mapping rules used by fixture tests.
- `CADDedupPlugin/CadMaterialFieldService.cs` - AutoCAD DWG title block/table read-write adapter.
- `CADDedupPlugin/MaterialSyncDiffPreviewWindow.xaml` - local diff confirmation UI for `PLMMATPULL`.
- `CADDedupPlugin/PackageContents.2018.xml` - AutoCAD 2018/R22.0 package metadata.
- `CADDedupPlugin/PackageContents.2024.xml` - AutoCAD 2024/R24.3 regression package metadata.
- `fixtures/material_sync_mock_drawing.json` - CAD drawing fixture for macOS verification.

## Local Verification

From the Yuantus repository root:

```bash
python3 scripts/verify_cad_material_delivery_package.py
```

Precise staging command:

```bash
bash scripts/print_cad_material_delivery_git_commands.sh --git-add-cmd
```

Focused client checks:

```bash
python3 clients/autocad-material-sync/verify_material_sync_static.py
python3 clients/autocad-material-sync/verify_material_sync_fixture.py
python3 clients/autocad-material-sync/verify_material_sync_e2e.py
python3 clients/autocad-material-sync/verify_material_sync_db_e2e.py
```

## Windows AutoCAD 2018 Validation

From a Windows checkout of Yuantus:

```powershell
cd clients\autocad-material-sync
powershell -ExecutionPolicy Bypass -File .\verify_autocad2018_preflight.ps1 -RunBuild
```

Then load the compiled DLL in AutoCAD 2018 and smoke:

- `DEDUPHELP`
- `DEDUPCONFIG`
- `PLMMATPROFILES`
- `PLMMATCOMPOSE`
- `PLMMATPUSH`
- `PLMMATPULL`

## Delivery Boundary

Commit source, scripts, docs, and fixtures. Do not commit AutoCAD build outputs:

- `bin/`
- `obj/`
- `*.dll`
- `*.pdb`
- `*.exe`

The macOS verification scripts do not replace real Windows + AutoCAD 2018 DLL loading and DWG write-back smoke.
