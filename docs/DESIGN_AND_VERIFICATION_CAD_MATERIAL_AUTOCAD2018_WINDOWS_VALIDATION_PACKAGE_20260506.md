# CAD Material AutoCAD 2018 Windows Validation Package Design And Verification

## Goal

补齐 Windows + AutoCAD 2018 实机验收包，让现场验证不再只依赖口头步骤。验收包覆盖预检、构建、加载、命令 smoke、真实 DWG 字段写回、证据留存和失败排查。

## Boundary

本轮只新增 Windows 验收文档和预检脚本，并同步现有 Yuantus 交付文档。不修改 Yuantus 服务端 API，不修改 CAD 字段读写逻辑，也不替代后续真实 AutoCAD 2018 手工 smoke。

## Package Contents

Yuantus AutoCAD 客户端新增：

- `clients/autocad-material-sync/WINDOWS_AUTOCAD2018_VALIDATION_GUIDE.md`
- `clients/autocad-material-sync/verify_autocad2018_preflight.ps1`

预检脚本覆盖：

- AutoCAD 2018 安装路径。
- `acad.exe`。
- `accoremgd.dll`、`acdbmgd.dll`、`acmgd.dll`、`AcWindows.dll`、`AdWindows.dll`。
- `.NET Framework 4.6` targeting pack。
- `PackageContents.2018.xml`。
- `CADDedupPlugin.csproj` 中的 2018 默认构建基线。
- MSBuild 查找。
- 可选 `-RunBuild` 编译验证。

验收指南覆盖：

- `ACADVER=R22.0`。
- `build_simple.bat` 默认 2018 构建。
- `NETLOAD` 和 bundle 加载路径。
- `DEDUPHELP`、`DEDUPCONFIG`、`PLMMATPROFILES` 命令 smoke。
- `PLMMATCOMPOSE` 写回规格。
- `PLMMATPUSH` dry-run 和真实写入。
- `PLMMATPULL` 回填图纸。
- 证据留存和失败排查表。

## Windows Usage

在 Windows 机器的 `clients\autocad-material-sync` 下执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\verify_autocad2018_preflight.ps1
```

带编译预检：

```powershell
powershell -ExecutionPolicy Bypass -File .\verify_autocad2018_preflight.ps1 -RunBuild
```

自定义 AutoCAD 2018 路径：

```powershell
powershell -ExecutionPolicy Bypass -File .\verify_autocad2018_preflight.ps1 -AutoCADInstallDir "D:\Autodesk\AutoCAD 2018"
```

## Verification

Yuantus AutoCAD 客户端静态验证：

```bash
python3 clients/autocad-material-sync/verify_material_sync_static.py
```

结果：

```text
OK: AutoCAD material sync static verification passed
```

XML 结构验证：

```bash
xmllint --noout clients/autocad-material-sync/CADDedupPlugin/CADDedupPlugin.csproj clients/autocad-material-sync/CADDedupPlugin/PackageContents.xml clients/autocad-material-sync/CADDedupPlugin/PackageContents.2018.xml clients/autocad-material-sync/CADDedupPlugin/PackageContents.2024.xml
```

结果：无输出，表示 XML 解析通过。

CAD fixture：

```bash
python3 clients/autocad-material-sync/verify_material_sync_fixture.py
```

结果：

```text
OK: material sync mock drawing fixture passed
```

CAD fixture 到 Yuantus 插件 e2e：

```bash
python3 clients/autocad-material-sync/verify_material_sync_e2e.py
```

结果：

```text
OK: material sync CAD fixture to Yuantus plugin e2e passed
```

SQLite DB e2e：

```bash
python3 clients/autocad-material-sync/verify_material_sync_db_e2e.py
```

结果：

```text
OK: material sync SQLite DB create/update/outbound e2e passed
```

Diff check：

```bash
git diff --check -- clients/autocad-material-sync/WINDOWS_AUTOCAD2018_VALIDATION_GUIDE.md clients/autocad-material-sync/verify_autocad2018_preflight.ps1 clients/autocad-material-sync/verify_material_sync_static.py
```

结果：无输出，表示本轮验收包相关改动没有空白错误。

## Remaining Boundary

仍需 Windows 实机完成：

- 运行 `verify_autocad2018_preflight.ps1 -RunBuild`。
- 在 AutoCAD 2018 中确认 `ACADVER=R22.0`。
- 加载 bundle 或 `NETLOAD` DLL。
- 执行物料同步命令 smoke。
- 用真实 DWG 验证标题栏块属性和明细表字段写回。
