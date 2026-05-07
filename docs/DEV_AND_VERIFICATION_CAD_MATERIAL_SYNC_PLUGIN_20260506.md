# CAD Material Sync Plugin Development And Verification

## Goal

本轮实现 CAD 物料属性同步的端到端开发切片：Yuantus 插件负责规则、校验、匹配和字段包输出；Yuantus AutoCAD 客户端接入插件 API，负责读取/写入图纸明细栏或标题栏字段。

## Boundary

本 PR/开发窗口交付 Yuantus 服务端插件、服务端测试、Yuantus AutoCAD 客户端接入代码和交付文档。

不包含：

- Windows + AutoCAD 2018/2024 DLL 编译产物；
- 真实 DWG/DXF 写回 smoke；
- 生产级全量结构化 profile 表单编辑器，例如条件字段、版本灰度、CAD 别名矩阵的完整可视化编辑；
- 数据库 migration。
- SolidWorks 客户端适配。

## Implementation

新增插件：

- `plugins/yuantus-cad-material-sync/plugin.json`
- `plugins/yuantus-cad-material-sync/main.py`

新增测试：

- `src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py`

新增 TODO：

- `docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md`

新增 Yuantus AutoCAD 客户端源码：

- `clients/autocad-material-sync/`
- `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_YUANTUS_AUTOCAD_CLIENT_MIGRATION_20260506.md`
- `clients/autocad-material-sync/MANIFEST.md`
- `scripts/verify_cad_material_delivery_package.py`
- `scripts/print_cad_material_delivery_git_commands.sh`
- `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_DELIVERY_PACKAGE_20260506.md`

Yuantus AutoCAD 客户端接入：

- `clients/autocad-material-sync/CADDedupPlugin/MaterialSyncApiClient.cs`
- `clients/autocad-material-sync/CADDedupPlugin/ICadMaterialFieldAdapter.cs`
- `clients/autocad-material-sync/CADDedupPlugin/CadMaterialFieldMapper.cs`
- `clients/autocad-material-sync/CADDedupPlugin/CadMaterialFieldService.cs`
- `clients/autocad-material-sync/CADDedupPlugin/DedupPlugin.cs`
- `clients/autocad-material-sync/CADDedupPlugin/DedupConfig.cs`
- `clients/autocad-material-sync/CADDedupPlugin/ConfigForm.cs`
- `clients/autocad-material-sync/CADDedupPlugin/PackageContents.xml`
- `clients/autocad-material-sync/PLM_MATERIAL_SYNC_GUIDE.md`
- `clients/autocad-material-sync/verify_material_sync_static.py`
- `clients/autocad-material-sync/verify_material_sync_fixture.py`
- `clients/autocad-material-sync/verify_material_sync_e2e.py`
- `clients/autocad-material-sync/verify_material_sync_db_e2e.py`
- `clients/autocad-material-sync/fixtures/material_sync_mock_drawing.json`

新增 DB e2e 设计与验证文档：

- `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_SYNC_DB_E2E_20260506.md`

新增物料库匹配设计与验证文档：

- `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_MATCHING_20260506.md`

新增单位换算与显示格式设计验证文档：

- `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_UNIT_FORMAT_20260506.md`

新增条件字段设计验证文档：

- `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_CONDITIONAL_FIELDS_20260506.md`

新增多 CAD 字段别名设计验证文档：

- `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_CAD_ALIASES_20260506.md`

新增 profile 版本化与灰度设计验证文档：

- `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_PROFILE_VERSIONING_20260506.md`

新增字段治理设计验证文档：

- `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_FIELD_GOVERNANCE_20260506.md`

新增管理端配置预览 API 设计验证文档：

- `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_CONFIG_PREVIEW_API_20260506.md`

新增 CAD 字段差异预览 API 设计验证文档：

- `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_DIFF_PREVIEW_API_20260506.md`

新增管理端配置持久化 API 设计验证文档：

- `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_CONFIG_STORE_API_20260506.md`

新增管理端配置导入/导出包 API 设计验证文档：

- `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_CONFIG_BUNDLE_API_20260506.md`

新增目标 CAD 系统字段输出设计验证文档：

- `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_CAD_SYSTEM_OUTPUT_20260506.md`

新增 Workbench 管理端接入设计验证文档：

- `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_WORKBENCH_UI_20260506.md`

新增 Workbench 结构化配置生成器设计验证文档：

- `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_WORKBENCH_STRUCTURED_CONFIG_20260506.md`

新增 profile 默认 overwrite 策略设计验证文档：

- `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_SYNC_DEFAULT_OVERWRITE_20260506.md`

新增 CAD 差异确认写回包设计验证文档：

- `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_DIFF_CONFIRM_PACKAGE_20260506.md`

## Design Notes

- v1 使用现有插件运行时挂载到 `/api/v1/plugins/cad-material-sync/*`，不改 PLM core 路由注册方式。
- v1 使用 `PluginConfigService` 读取租户/组织级配置，不新增数据库迁移。
- profile 是通用适配层：字段、CAD 字段名、必填、类型、单位、规格模板、匹配选择器都在 profile 中声明。
- 默认 profile 包含板材、管材、棒材、锻件四类规则。
- `specification` 是派生字段。长、宽、厚、外径、壁厚、直径、毛坯尺寸等源字段仍保存在独立属性中。
- CAD 写回不在服务端直接修改 DWG/DXF。插件返回 `cad_fields` 字段包，由本地 CAD 适配器写回图纸。
- PLM 入站同步默认只填空字段；已有值冲突会返回 `conflict`。请求明确传 `overwrite=true`，或请求省略 `overwrite` 且 profile 配置 `sync_defaults.overwrite=true` 时才覆盖。
- AutoCAD 客户端新增 `PLMMATPROFILES`、`PLMMATCOMPOSE`、`PLMMATPUSH`、`PLMMATPULL` 命令，并在 Ribbon 中加入物料同步入口。
- AutoCAD 字段服务会扫描 ModelSpace 和全部 Layout/PaperSpace 的块表记录，读取/写回块属性和表格字段，避免只覆盖当前布局。
- AutoCAD 客户端内置字段别名用于兜底，长期仍应由服务端 profile 下发企业模板字段映射。
- CAD 字段适配已拆分为 `ICadMaterialFieldAdapter<TCadDocument>`、纯规则 `CadMaterialFieldMapper` 和 AutoCAD 实现 `CadMaterialFieldService`，macOS 可以通过 mock drawing fixture 验证字段映射规则。
- 新增 macOS 端到端验证：从 CAD mock fixture 抽取字段，调用 Yuantus `/sync/inbound` dry-run，拿到 `cad_fields` 后回填 fixture，再调用 `/sync/outbound` 校验字段包一致。
- 新增真实 SQLite DB 端到端验证：dry-run 不落库、真实创建 PLM Item、真实更新 Item、outbound 字段包回填 CAD fixture。
- 新增物料库匹配增强：按 `item_number`、`drawing_no`、`material_code` 和物料类别/材料/规格组合的优先级 strategy 匹配；单匹配进入更新/冲突路径，多匹配返回候选。
- 新增 profile 单位换算和显示格式：数值字段可声明标准单位、输入单位、显示单位、精度、format spec 和后缀；PLM 属性保留标准单位，规格模板按显示配置渲染。
- 新增 profile 条件字段：字段可通过 `when`/`condition`/`visible_when` 控制启用，通过 `required_when` 控制条件必填；校验前会合并 profile selector，使条件能依赖物料类别默认值。
- 新增 profile 多 CAD 字段别名：`cad_mapping` 和字段 `cad_key` 支持列表/字典别名；入站识别所有别名，出站仍只输出主 CAD 字段，避免同一属性重复写多个图框字段。
- 新增 profile 版本化与灰度：profile 可声明 `versions`、`active_version`、`default_version` 和 `rollout`；显式版本优先，其次灰度命中，再回退默认版本，便于按租户/组织逐步切换规格规则。
- 新增字段治理：profile 自动生成 `governance` 元数据，明确 `specification` 是派生/cache 字段，长宽厚等字段是 source of truth；当传入规格与源字段合成结果不一致时返回 `derived_field_mismatch` warning。
- 新增管理端配置预览 API：`POST /config/preview` 支持 profile 草稿诊断、当前生效版本解析、样例规格预览和 CAD 字段包预览，不写数据库，作为后续管理 UI 的实时预览后端。
- 新增 CAD 字段差异预览 API：`POST /diff/preview` 根据当前 CAD 字段和目标字段包返回 `added/changed/cleared/unchanged` 字段级差异，并返回只包含待写字段的 `write_cad_fields` 和 `requires_confirmation`，支撑 CAD 客户端确认写回 UI。
- 新增管理端配置持久化 API：`GET/PUT/DELETE /config` 复用 `PluginConfigService` 读写当前租户/组织作用域配置；保存前做配置诊断，写操作要求 admin/superuser。
- 新增管理端配置导入/导出包 API：`GET /config/export` 输出带 `plugin_id/schema_version/config_hash` 的配置包；`POST /config/import` 支持 dry-run、merge、hash 校验和 admin 写入。
- 新增目标 CAD 系统字段输出：`compose`、`validate`、`config/preview`、`diff/preview`、`sync/outbound`、`sync/inbound` 请求可传 `cad_system`，服务端按 SolidWorks/AutoCAD 等目标系统选择出站主 CAD 字段，未配置时回退默认字段。
- 新增 Workbench 管理端接入：`/api/v1/workbench` 增加 CAD Material 区块，复用现有 tenant/org/token、请求日志和 raw response 面板，接入 profile 列表、配置读取/保存/删除、草稿预览、合成、差异预览、出站字段包和导入/导出。
- 新增 Workbench 结构化配置生成器：管理员可在页面内生成字段定义、CAD 字段名、类型、必填、单位、规格模板、匹配键和 `sync_defaults.overwrite` 默认策略；生成器只更新配置草稿，保存仍走既有配置 API。
- 新增 profile 默认 overwrite 策略：`/sync/inbound` 在请求省略 `overwrite` 时读取 `sync_defaults.overwrite`；请求显式 `overwrite=false/true` 始终优先；旧 `ui_defaults.overwrite` 不参与服务端写库。
- 新增 Workbench CAD 写回确认面板：`Preview diff` 成功后展示待写字段、当前值、目标值，并把 `write_cad_fields` 写入确认包 JSON；确认按钮只确认包已准备好，不直接改 DWG/DXF。
- 新增 CAD 差异确认 contract fixture：`docs/samples/cad_material_diff_confirm_fixture.json` 固定新增/变更、清空、无变化 3 个客户端消费场景，`scripts/verify_cad_material_diff_confirm_contract.py` 可在无 CAD 环境下验证 `/diff/preview` 合同。
- 新增 AutoCAD 2018 最低兼容基线：Yuantus AutoCAD 客户端工程默认 `AutoCADVersion=2018`、`TargetFrameworkVersion=v4.6`、`PackageContents` 使用 `R22.0`，并保留 `AutoCADVersion=2024` 显式构建路径。详见 `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_AUTOCAD2018_COMPATIBILITY_20260506.md`。
- 新增 Windows + AutoCAD 2018 验收包：Yuantus AutoCAD 客户端新增 `WINDOWS_AUTOCAD2018_VALIDATION_GUIDE.md` 和 `verify_autocad2018_preflight.ps1`，覆盖预检、构建、加载、命令 smoke、真实 DWG 写回、证据留存和失败排查。详见 `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_AUTOCAD2018_WINDOWS_VALIDATION_PACKAGE_20260506.md`。
- 新增 AutoCAD 本地差异确认 UI：`PLMMATPULL` 调用 `/diff/preview`，展示 `MaterialSyncDiffPreviewWindow`，用户确认后只写回 `write_cad_fields`。详见 `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_AUTOCAD_DIFF_PREVIEW_UI_20260506.md`。
- 新增 Yuantus 仓库级交付包验证：`scripts/verify_cad_material_delivery_package.py` 聚合客户端静态检查、mock drawing fixture、插件 e2e、SQLite DB e2e、diff confirm contract、XML/XAML 解析、旧路径残留扫描和构建产物排除；`scripts/print_cad_material_delivery_git_commands.sh` 输出精确 staging 指令。详见 `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_DELIVERY_PACKAGE_20260506.md`。

## API Surface

- `GET /api/v1/plugins/cad-material-sync/profiles`
  - 返回当前租户/组织可用物料 profile。
- `GET /api/v1/plugins/cad-material-sync/profiles/{profile_id}`
  - 返回单个 profile。
- `GET /api/v1/plugins/cad-material-sync/config`
  - 返回当前作用域已保存配置和生效 profile。
- `PUT /api/v1/plugins/cad-material-sync/config`
  - 保存当前作用域 profile 配置，保存前校验，写操作要求 admin。
- `DELETE /api/v1/plugins/cad-material-sync/config`
  - 删除当前作用域 profile 配置，恢复默认规则，写操作要求 admin。
- `GET /api/v1/plugins/cad-material-sync/config/export`
  - 导出当前作用域配置 bundle。
- `POST /api/v1/plugins/cad-material-sync/config/import`
  - 导入配置 bundle，支持 dry-run 和 hash 校验，写操作要求 admin。
- `POST /api/v1/plugins/cad-material-sync/compose`
  - 输入 profile 和属性，输出规范化属性、合成规格、CAD 字段包；可传 `cad_system` 选择目标 CAD 字段名。
- `POST /api/v1/plugins/cad-material-sync/validate`
  - 输入 profile 和属性，校验类型/必填，并可查找已有物料；可传 `cad_system` 预览目标字段包。
- `POST /api/v1/plugins/cad-material-sync/config/preview`
  - 输入 profile 草稿配置和样例属性，输出合并后 profile、配置诊断、规格预览和 CAD 字段包；可传 `cad_system`。
- `POST /api/v1/plugins/cad-material-sync/diff/preview`
  - 输入当前 CAD 字段和目标属性/字段包，输出字段级差异摘要；可传 `cad_system`。
- `POST /api/v1/plugins/cad-material-sync/sync/outbound`
  - PLM 属性或 item -> CAD 字段包；可传 `cad_system`。
- `POST /api/v1/plugins/cad-material-sync/sync/inbound`
  - CAD 字段 -> PLM 属性，支持 dry run、匹配、冲突检查、可选新建；可传 `cad_system` 生成回写字段包。

## Verification

已执行：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py -q
```

结果：

```text
41 passed, 1 warning in 2.45s
```

插件运行时加载 smoke：

```bash
PYTHONPATH=src YUANTUS_PLUGINS_ENABLED=yuantus-cad-material-sync python3 -c "from fastapi import FastAPI; from yuantus.plugin_manager.runtime import load_plugins; app=FastAPI(); manager=load_plugins(app); print(manager.get_plugin_stats() if manager else None); print(sorted(getattr(route, 'path', '') for route in app.routes if 'cad-material-sync' in getattr(route, 'path', '')))"
```

结果：

```text
{'total': 4, 'by_status': {'discovered': 3, 'active': 1}, 'by_type': {'extension': 4}, 'by_category': {'demo': 1, 'cad': 1, 'files': 1, 'bom': 1}, 'errors': 0}
['/api/v1/plugins/cad-material-sync/compose', '/api/v1/plugins/cad-material-sync/config', '/api/v1/plugins/cad-material-sync/config', '/api/v1/plugins/cad-material-sync/config', '/api/v1/plugins/cad-material-sync/config/export', '/api/v1/plugins/cad-material-sync/config/import', '/api/v1/plugins/cad-material-sync/config/preview', '/api/v1/plugins/cad-material-sync/diff/preview', '/api/v1/plugins/cad-material-sync/profiles', '/api/v1/plugins/cad-material-sync/profiles/{profile_id}', '/api/v1/plugins/cad-material-sync/sync/inbound', '/api/v1/plugins/cad-material-sync/sync/outbound', '/api/v1/plugins/cad-material-sync/validate']
```

既有插件和 CAD 相关测试回归：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/api/tests/test_workbench_router.py src/yuantus/api/tests/test_plugin_runtime_security.py src/yuantus/meta_engine/tests/test_plugin_bom_compare.py src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py src/yuantus/meta_engine/tests/test_cad_properties_router.py src/yuantus/meta_engine/tests/test_cad_sync_template_router.py src/yuantus/meta_engine/tests/test_cad_import_service.py src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py -q
```

结果：

```text
117 passed, 1 skipped, 1 warning in 5.57s
```

CAD 差异确认 contract fixture：

```bash
PYTHONPATH=src python3 scripts/verify_cad_material_diff_confirm_contract.py
```

结果：

```text
OK: CAD material diff confirm contract fixture passed (3 cases)
```

Workbench 结构化配置生成器验证：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/api/tests/test_workbench_router.py -q
```

结果：

```text
5 passed, 1 warning in 3.02s
```

Workbench JS 语法验证：

```bash
node -e "const fs=require('fs'); const html=fs.readFileSync('src/yuantus/web/workbench.html','utf8'); const m=html.match(/<script>([\s\S]*)<\/script>/); new Function(m[1]); console.log('workbench script syntax ok');"
```

结果：

```text
workbench script syntax ok
```

Workbench 浏览器 smoke：

```bash
npx playwright test playwright/tests/cad_material_workbench_ui.spec.js
```

结果：

```text
1 passed
```

备注：首次运行时本机缺少 Playwright Chromium，已执行 `npx playwright install chromium` 后复跑通过。

最新组合回归：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/api/tests/test_workbench_router.py src/yuantus/api/tests/test_plugin_runtime_security.py src/yuantus/meta_engine/tests/test_plugin_bom_compare.py src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py src/yuantus/meta_engine/tests/test_cad_properties_router.py src/yuantus/meta_engine/tests/test_cad_sync_template_router.py src/yuantus/meta_engine/tests/test_cad_import_service.py src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py -q
```

结果：

```text
117 passed, 1 skipped, 1 warning in 5.57s
```

编译与 diff 检查：

```bash
PYTHONPYCACHEPREFIX=.pytest_cache/pycache python3 -m py_compile src/yuantus/api/routers/workbench.py src/yuantus/api/tests/test_workbench_router.py plugins/yuantus-cad-material-sync/main.py src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py
git diff --check
```

结果：无输出，表示通过。

备注：warning 为本机 Python/urllib3 的 LibreSSL 兼容提示，不是本插件回归失败。

AutoCAD 客户端静态验证：

```bash
python3 clients/autocad-material-sync/verify_material_sync_static.py
python3 clients/autocad-material-sync/verify_material_sync_fixture.py
python3 clients/autocad-material-sync/verify_material_sync_e2e.py
python3 clients/autocad-material-sync/verify_material_sync_db_e2e.py
xmllint --noout clients/autocad-material-sync/CADDedupPlugin/CADDedupPlugin.csproj clients/autocad-material-sync/CADDedupPlugin/PackageContents.xml clients/autocad-material-sync/CADDedupPlugin/PackageContents.2018.xml clients/autocad-material-sync/CADDedupPlugin/PackageContents.2024.xml
git diff --check -- clients/autocad-material-sync/WINDOWS_AUTOCAD2018_VALIDATION_GUIDE.md clients/autocad-material-sync/verify_autocad2018_preflight.ps1 clients/autocad-material-sync/verify_material_sync_static.py
```

结果：

```text
OK: AutoCAD material sync static verification passed
OK: material sync mock drawing fixture passed
OK: material sync CAD fixture to Yuantus plugin e2e passed
OK: material sync SQLite DB create/update/outbound e2e passed
```

`xmllint` 和限定 `git diff --check` 无输出。`CADDedupPlugin.csproj`、默认 2018 package 和 2024 package XML 结构有效。静态验证同时覆盖 AutoCAD 2018 默认基线、`R22.0` package、`.NET Framework v4.6`、版本化输出路径、2024 显式构建分支、Windows 验收指南和 2018 预检脚本。fixture 验证覆盖块属性抽取、表格相邻单元格抽取、`字段=值` 抽取和回填更新计数；e2e 验证覆盖 CAD fixture -> Yuantus 插件 dry-run -> CAD fixture 回填；DB e2e 覆盖 CAD fixture -> Yuantus 插件 -> SQLite PLM Item 创建/更新 -> outbound CAD fixture 回填。

受限验证：

```bash
dotnet --info
command -v msbuild
command -v csc
command -v mcs
```

结果：当前 macOS 开发环境未安装 .NET/MSBuild/C# 编译器，也没有 Windows AutoCAD 2018/2024 DLL，因此本窗口不能真实编译 AutoCAD DLL 或打开 AutoCAD 做 DWG 写回 smoke。后续在 Windows + AutoCAD 2018 环境优先执行 DLL 编译、命令 smoke 和真实 DWG 回填验证，再用 2024 做高版本回归。

当前命令证据：

```text
dotnet --info -> zsh:1: command not found: dotnet
command -v msbuild -> not found
command -v csc -> not found
command -v mcs -> not found
```

## Follow-up Boundary

这个切片已完成服务端插件能力和 Yuantus AutoCAD 客户端接入。下一步真实环境验证为：

- 在 Windows + AutoCAD 2018 上运行 `build_simple.bat` 或 Visual Studio Release/x64 构建。
- 在 AutoCAD 2018 中确认 `ACADVER=R22.0`，加载 DLL 后执行 `PLMMATPROFILES`。
- 使用带标题栏块属性或表格的 DWG 执行 `PLMMATCOMPOSE`。
- 执行 `PLMMATPUSH` dry-run，再对测试物料执行真实写入。
- 执行 `PLMMATPULL` 验证 PLM -> CAD 差异预览、确认和回填。
- 使用 `AUTOCAD_VERSION=2024` 对 AutoCAD 2024 做回归构建和 smoke。
- 另起 SolidWorks 客户端适配切片，复用 `cad-material-sync` API 和字段 mapper 规则。
