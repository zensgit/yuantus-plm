# CAD Material Sync GitHub Handoff

## Current GitHub Branch

- Repository: `https://github.com/zensgit/yuantus-plm`
- Branch: `feat/cad-material-sync-plugin-20260506`
- Delivery commit before this handoff note: `f103bd5 feat: add CAD material sync delivery package`
- PR create URL: `https://github.com/zensgit/yuantus-plm/pull/new/feat/cad-material-sync-plugin-20260506`

## Continue From A New Computer

Clone and switch to the feature branch:

```bash
git clone https://github.com/zensgit/yuantus-plm.git
cd yuantus-plm
git switch feat/cad-material-sync-plugin-20260506
```

Run the repository-level delivery verification:

```bash
python3 scripts/verify_cad_material_delivery_package.py
```

Expected final line:

```text
OK: CAD material delivery package verification passed
```

## AutoCAD Client Source

The Yuantus-owned AutoCAD client package is in:

```text
clients/autocad-material-sync/
```

Important entrypoints:

- `clients/autocad-material-sync/MANIFEST.md`
- `clients/autocad-material-sync/PLM_MATERIAL_SYNC_GUIDE.md`
- `clients/autocad-material-sync/WINDOWS_AUTOCAD2018_VALIDATION_GUIDE.md`
- `clients/autocad-material-sync/CADDedupPlugin/CADDedupPlugin.csproj`
- `clients/autocad-material-sync/verify_autocad2018_preflight.ps1`

## Local Verification Commands

From the Yuantus repository root:

```bash
python3 scripts/verify_cad_material_delivery_package.py
PYTHONPATH=src python3 -m pytest src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py src/yuantus/api/tests/test_workbench_router.py -q
python3 scripts/verify_cad_material_diff_confirm_contract.py
```

## Windows AutoCAD 2018 Validation

On a Windows machine with AutoCAD 2018 installed:

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

This Windows smoke is still required because macOS cannot compile/load the AutoCAD .NET DLL or verify real DWG write-back.

## Commit Boundary

If more CAD Material Sync changes are added before merge, print the precise staging command:

```bash
bash scripts/print_cad_material_delivery_git_commands.sh --git-add-cmd
```

Do not include:

- `.claude/`
- `local-dev-env/`
- `docs/DELIVERY_DOC_INDEX.md` unless deliberately closing the delivery index separately
- AutoCAD build outputs under `clients/autocad-material-sync/CADDedupPlugin/bin/` or `obj/`

## Current Residual Local Files

After the delivery commit, the local worktree intentionally still had these uncommitted local-only or undecided paths:

- `docs/DELIVERY_DOC_INDEX.md`
- `.claude/`
- `local-dev-env/`

They are not required for continuing CAD Material Sync from GitHub.
