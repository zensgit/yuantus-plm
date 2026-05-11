# CAD Material AutoCAD Diff Preview UI Design And Verification

## Goal

把服务端 `/diff/preview` 和 `write_cad_fields` 合同接入现有 Windows AutoCAD 客户端。`PLMMATPULL` 在真实写回 DWG 前先展示本地 WPF 差异确认窗口，用户确认后只写回服务端返回的待写字段包。

## Boundary

本轮修改 Yuantus AutoCAD 客户端仓库，不改变 Yuantus 服务端 API。真实窗口渲染、DLL 编译、`NETLOAD` 和 DWG 写回仍需 Windows + AutoCAD 2018 环境最终验收。

## Implementation

Yuantus AutoCAD 客户端新增/修改：

- `clients/autocad-material-sync/CADDedupPlugin/MaterialSyncApiClient.cs`
  - 新增 `DiffPreviewAsync(...)`。
  - 新增 `MaterialDiffPreviewResponse` 和 `MaterialCadFieldDiff`。
  - 所有 material sync 请求显式传 `cad_system="autocad"`，确保 connector-specific CAD 字段名不回退默认映射。
- `clients/autocad-material-sync/CADDedupPlugin/MaterialSyncDiffPreviewWindow.xaml`
  - 展示 CAD 字段、当前值、目标值、状态和确认/取消按钮。
- `clients/autocad-material-sync/CADDedupPlugin/MaterialSyncDiffPreviewWindow.xaml.cs`
  - 输出 `ConfirmedWriteFields`，只在用户确认后返回。
- `clients/autocad-material-sync/CADDedupPlugin/DedupPlugin.cs`
  - `PLMMATPULL` 先抽取当前 CAD 字段。
  - 调用 `/diff/preview`。
  - 无差异时不写回。
  - 有差异时弹出 `MaterialSyncDiffPreviewWindow`。
  - 用户取消时不写回。
  - 用户确认时只应用 `write_cad_fields`。
- `clients/autocad-material-sync/CADDedupPlugin/CADDedupPlugin.csproj`
  - 纳入新 XAML 和 code-behind。
- `clients/autocad-material-sync/CADDedupPlugin/PackageContents.xml`
- `clients/autocad-material-sync/CADDedupPlugin/PackageContents.2018.xml`
- `clients/autocad-material-sync/CADDedupPlugin/PackageContents.2024.xml`
  - 发布元数据描述补充 PLM Material Sync。
  - `PLMMATPULL` 命令描述改为差异预览确认后回填。
- `clients/autocad-material-sync/verify_material_sync_static.py`
  - 增加 `/diff/preview`、`cad_system=autocad`、窗口文件、确认写回包、package 描述和 `PLMMATPULL` 行为静态检查。
- `clients/autocad-material-sync/README.md`
- `clients/autocad-material-sync/PLM_MATERIAL_SYNC_GUIDE.md`
- `clients/autocad-material-sync/WINDOWS_AUTOCAD2018_VALIDATION_GUIDE.md`

## Verification

AutoCAD 客户端静态验证：

```bash
python3 clients/autocad-material-sync/verify_material_sync_static.py
```

结果：

```text
OK: AutoCAD material sync static verification passed
```

XAML/XML 结构验证：

```bash
xmllint --noout clients/autocad-material-sync/CADDedupPlugin/CADDedupPlugin.csproj clients/autocad-material-sync/CADDedupPlugin/MaterialSyncDiffPreviewWindow.xaml
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

限定 diff check：

```bash
git diff --check -- clients/autocad-material-sync/CADDedupPlugin/MaterialSyncApiClient.cs clients/autocad-material-sync/CADDedupPlugin/DedupPlugin.cs clients/autocad-material-sync/CADDedupPlugin/MaterialSyncDiffPreviewWindow.xaml clients/autocad-material-sync/CADDedupPlugin/MaterialSyncDiffPreviewWindow.xaml.cs clients/autocad-material-sync/CADDedupPlugin/CADDedupPlugin.csproj clients/autocad-material-sync/verify_material_sync_static.py clients/autocad-material-sync/README.md clients/autocad-material-sync/PLM_MATERIAL_SYNC_GUIDE.md clients/autocad-material-sync/WINDOWS_AUTOCAD2018_VALIDATION_GUIDE.md
```

结果：无输出，表示本轮 AutoCAD diff preview UI 相关改动没有空白错误。

## Windows Acceptance

Windows + AutoCAD 2018 实机仍需验证：

- DLL 编译通过。
- `PLMMATPULL` 调用后弹出差异预览窗口。
- 取消按钮不修改当前 DWG。
- 确认按钮只写回 `write_cad_fields`。
- 使用包含 `cad_system=autocad` 别名配置的 profile 验证 AutoCAD 主字段名被选中。
- 保存并重新打开 DWG 后字段仍存在。
