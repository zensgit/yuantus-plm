# CAD Material Yuantus AutoCAD Client Migration Design And Verification

## Goal

把 PLM 仓库里已经完成的 AutoCAD 物料同步客户端能力迁入 Yuantus 仓库，让后续开发、提交、换机 clone 和 Windows 验收都以 `yuantus-plm` 为主仓库，不再依赖旧 PLM 仓库的本机客户端路径。

## Scope

本轮迁移的是可编译、可验证、和 CAD Material Sync 直接相关的客户端源码与验证资产：

- AutoCAD 2018/2024 兼容 C# 工程。
- CAD 字段读取、字段映射、明细表/标题栏写回实现。
- Yuantus `cad-material-sync` API 客户端。
- `PLMMATPROFILES`、`PLMMATCOMPOSE`、`PLMMATPUSH`、`PLMMATPULL` 命令入口。
- `/diff/preview` 本地 WPF 差异确认窗口。
- AutoCAD bundle `PackageContents`。
- Windows 构建/预检脚本。
- macOS 可运行的静态、fixture、插件 e2e、SQLite DB e2e 验证脚本。

本轮没有迁移 PLM 仓库里的无关前端、数据库、alembic、日志、历史备份和旧实验文件；也没有把 AutoCAD DLL 编译结果纳入仓库。

## Destination

Yuantus 内新增客户端目录：

```text
clients/autocad-material-sync/
```

主要内容：

- `clients/autocad-material-sync/CADDedupPlugin/CADDedupPlugin.csproj`
- `clients/autocad-material-sync/CADDedupPlugin/MaterialSyncApiClient.cs`
- `clients/autocad-material-sync/CADDedupPlugin/CadMaterialFieldMapper.cs`
- `clients/autocad-material-sync/CADDedupPlugin/CadMaterialFieldService.cs`
- `clients/autocad-material-sync/CADDedupPlugin/ICadMaterialFieldAdapter.cs`
- `clients/autocad-material-sync/CADDedupPlugin/DedupPlugin.cs`
- `clients/autocad-material-sync/CADDedupPlugin/MaterialSyncDiffPreviewWindow.xaml`
- `clients/autocad-material-sync/CADDedupPlugin/MaterialSyncDiffPreviewWindow.xaml.cs`
- `clients/autocad-material-sync/CADDedupPlugin/PackageContents.xml`
- `clients/autocad-material-sync/CADDedupPlugin/PackageContents.2018.xml`
- `clients/autocad-material-sync/CADDedupPlugin/PackageContents.2024.xml`
- `clients/autocad-material-sync/PLM_MATERIAL_SYNC_GUIDE.md`
- `clients/autocad-material-sync/WINDOWS_AUTOCAD2018_VALIDATION_GUIDE.md`
- `clients/autocad-material-sync/verify_autocad2018_preflight.ps1`
- `clients/autocad-material-sync/verify_material_sync_static.py`
- `clients/autocad-material-sync/verify_material_sync_fixture.py`
- `clients/autocad-material-sync/verify_material_sync_e2e.py`
- `clients/autocad-material-sync/verify_material_sync_db_e2e.py`
- `clients/autocad-material-sync/fixtures/material_sync_mock_drawing.json`

## Adjustments

- `verify_material_sync_e2e.py` 现在优先从 `clients/autocad-material-sync` 向上定位当前 Yuantus 仓库根目录，避免换电脑或 clone 到不同目录名后仍依赖旧 PLM 同级路径。
- 客户端 README 和物料同步指南的命令路径已改为 `clients/autocad-material-sync`。
- Windows AutoCAD 2018 验收指南已改为从 `clients\autocad-material-sync` 执行。
- Yuantus 侧既有开发、TODO、AutoCAD 2018 兼容、Windows 验收、diff preview 文档已切到 Yuantus 内部客户端路径。

## Verification

AutoCAD 客户端静态验证：

```bash
python3 clients/autocad-material-sync/verify_material_sync_static.py
```

结果：

```text
OK: AutoCAD material sync static verification passed
```

CAD mock drawing fixture：

```bash
python3 clients/autocad-material-sync/verify_material_sync_fixture.py
```

结果：

```text
OK: material sync mock drawing fixture passed
```

XML/XAML 结构验证：

```bash
xmllint --noout clients/autocad-material-sync/CADDedupPlugin/CADDedupPlugin.csproj clients/autocad-material-sync/CADDedupPlugin/MaterialSyncDiffPreviewWindow.xaml clients/autocad-material-sync/CADDedupPlugin/PackageContents.xml clients/autocad-material-sync/CADDedupPlugin/PackageContents.2018.xml clients/autocad-material-sync/CADDedupPlugin/PackageContents.2024.xml
```

结果：无输出，表示 XML/XAML 解析通过。

Python 验证脚本编译：

```bash
python3 -m py_compile clients/autocad-material-sync/verify_material_sync_static.py clients/autocad-material-sync/verify_material_sync_fixture.py clients/autocad-material-sync/verify_material_sync_e2e.py clients/autocad-material-sync/verify_material_sync_db_e2e.py
```

结果：无输出，表示脚本语法通过。

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

旧路径残留扫描已覆盖客户端目录、CAD Material TODO、开发验证文档和既有设计验证文档。

结果：无输出，表示迁移相关文档和客户端目录不再引用旧 PLM AutoCAD 客户端路径。

## Remaining Boundary

macOS 仍不能编译和加载 AutoCAD .NET 插件 DLL。最终验收仍需在 Windows + AutoCAD 2018 环境运行：

```powershell
cd clients\autocad-material-sync
powershell -ExecutionPolicy Bypass -File .\verify_autocad2018_preflight.ps1 -RunBuild
```

然后在 AutoCAD 2018 中执行 `NETLOAD`、`DEDUPHELP`、`PLMMATPROFILES`、`PLMMATCOMPOSE`、`PLMMATPUSH`、`PLMMATPULL`，使用真实 DWG 验证标题栏块属性和明细表回填。
