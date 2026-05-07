# CAD Material AutoCAD 2018 Compatibility Design And Verification

## Goal

把 Windows AutoCAD 客户端的最低兼容基线调整为 AutoCAD 2018。客户现场低版本较多，因此 2018/R22.0 作为主交付验证环境；AutoCAD 2024 作为高版本回归路径保留。

## Boundary

本轮改造 Yuantus AutoCAD 客户端工程和 Yuantus 侧交付文档，不改变 Yuantus `cad-material-sync` 服务端 API、数据库模型或 Workbench 行为。

真实 DLL 编译、`NETLOAD`、命令注册和 DWG 写回 smoke 仍必须在 Windows + AutoCAD 2018 实机完成；macOS 只能完成静态、fixture 和服务端契约验证。

## Design

AutoCAD 2018 基线：

- AutoCAD release：`R22.0`
- .NET：`.NET Framework 4.6`
- 构建默认：`AutoCADVersion=2018`
- 默认安装路径：`C:\Program Files\Autodesk\AutoCAD 2018`
- 默认 bundle：`PackageContents.xml` 与 `PackageContents.2018.xml` 均声明 `SeriesMin="R22.0"`、`SeriesMax="R22.0"`

高版本回归：

- AutoCAD 2024 显式构建：`AutoCADVersion=2024`
- AutoCAD 2024 bundle：`PackageContents.2024.xml`
- 2024 package 声明 `SeriesMin="R24.3"`、`SeriesMax="R24.3"`
- 当前 .NET Framework 插件不声明 `R25.0`，避免把 AutoCAD 2025/.NET 8 路径混入同一 DLL 验收。

构建参数：

```batch
REM AutoCAD 2018 baseline
build_simple.bat

REM AutoCAD 2024 explicit regression
set AUTOCAD_VERSION=2024
set AUTOCAD_INSTALL_DIR=C:\Program Files\Autodesk\AutoCAD 2024
build_simple.bat
```

## Changed Files

Yuantus AutoCAD 客户端：

- `clients/autocad-material-sync/CADDedupPlugin/CADDedupPlugin.csproj`
- `clients/autocad-material-sync/CADDedupPlugin/PackageContents.xml`
- `clients/autocad-material-sync/CADDedupPlugin/PackageContents.2018.xml`
- `clients/autocad-material-sync/CADDedupPlugin/PackageContents.2024.xml`
- `clients/autocad-material-sync/build.bat`
- `clients/autocad-material-sync/build_simple.bat`
- `clients/autocad-material-sync/quick_build.bat`
- `clients/autocad-material-sync/build_with_devenv.ps1`
- `clients/autocad-material-sync/verify_material_sync_static.py`
- `clients/autocad-material-sync/verify_autocad2018_preflight.ps1`
- `clients/autocad-material-sync/WINDOWS_AUTOCAD2018_VALIDATION_GUIDE.md`
- `clients/autocad-material-sync/README.md`
- `clients/autocad-material-sync/PLM_MATERIAL_SYNC_GUIDE.md`

Yuantus 文档：

- `docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md`
- `docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_PLUGIN_20260506.md`
- `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_AUTOCAD2018_COMPATIBILITY_20260506.md`
- `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_AUTOCAD2018_WINDOWS_VALIDATION_PACKAGE_20260506.md`

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

CAD mock drawing fixture：

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

残留扫描：

```bash
rg -n -F -e "net48" -e "v4.8" -e "R25.0" -e "SeriesMin=\"R24.0\"" -e "C:\Program Files\Autodesk\AutoCAD 2024" clients/autocad-material-sync/CADDedupPlugin clients/autocad-material-sync/build.bat clients/autocad-material-sync/build_simple.bat clients/autocad-material-sync/quick_build.bat clients/autocad-material-sync/build_with_devenv.ps1 clients/autocad-material-sync/verify_material_sync_static.py
```

结果：只命中有意保留的 2024 显式构建分支、非 2018 fallback 和静态验证中的禁止项；未发现 `net48` 输出路径、`R25.0` package 声明或 AutoCAD 2024 固定 `HintPath`。

## Windows Acceptance Checklist

仍需在 Windows 实机完成：

- 安装 AutoCAD 2018，并确认命令行 `ACADVER` 返回 `R22.0`。
- 执行 `build_simple.bat`，确认输出 `CADDedupPlugin\bin\x64\Release\AutoCAD2018\CADDedupPlugin.dll`。
- 用 bundle 或 `NETLOAD` 加载 DLL。
- 执行 `DEDUPHELP`、`DEDUPCONFIG`、`PLMMATPROFILES`。
- 打开含标题栏块属性和明细表的 DWG。
- 执行 `PLMMATCOMPOSE`，确认 `规格` 字段写回。
- 执行 `PLMMATPUSH` dry-run 和真实写入。
- 执行 `PLMMATPULL`，确认 PLM 字段回填 DWG。
- 使用 `AUTOCAD_VERSION=2024` 做高版本回归 smoke。

## Risks

- AutoCAD 2018 真实 DLL 编译与加载必须用 2018 管理程序集验证，不能用 2024 DLL 代替。
- WPF、Ribbon、`Table` 字段读写都需要真实 AutoCAD 2018 smoke 才能最终确认。
- 如果后续支持 AutoCAD 2025+，需要单独评估 .NET 8 插件分支，不能直接扩大当前 .NET Framework package 的 `SeriesMax`。
