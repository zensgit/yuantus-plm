# CAD Material Sync Plugin TODO

## Scope

把 CAD 明细栏/标题栏字段和 PLM 物料属性做成可配置插件能力，优先支持板材、管材、棒材、锻件四类物料：

- CAD 端获取物料类型对应字段。
- 用户填写或从明细栏提取字段后，按类型规则合成规格。
- 插件校验字段完整性和类型，并查询 PLM 物料库是否已有匹配项。
- 输出 CAD 字段包，由 CAD 适配器写回图纸明细栏/标题栏。
- 支持从 CAD 字段回写 PLM Item 属性，默认只填空字段；请求显式 overwrite 或 profile `sync_defaults.overwrite=true` 才覆盖已有值。

## Completed

- [x] 新增服务端插件 `yuantus-cad-material-sync`。
- [x] 插件声明 `plugins/yuantus-cad-material-sync/plugin.json`，标记 CAD/material/sync/specification 能力。
- [x] 将 AutoCAD 物料同步客户端源码、构建脚本、验证脚本和 Windows 2018 验收文档迁入 Yuantus：`clients/autocad-material-sync/`。
- [x] 新增 Yuantus 内交付包 manifest、一键验证入口和精确 staging 指令打印器：`clients/autocad-material-sync/MANIFEST.md`、`scripts/verify_cad_material_delivery_package.py`、`scripts/print_cad_material_delivery_git_commands.sh`。
- [x] 默认物料 profile：
  - [x] `sheet` 板材：`length * width * thickness`
  - [x] `tube` 管材：`Φouter_diameter * wall_thickness * length`
  - [x] `bar` 棒材：`Φdiameter * length`
  - [x] `forging` 锻件：`blank_size`
- [x] API：
  - [x] `GET /api/v1/plugins/cad-material-sync/profiles`
  - [x] `GET /api/v1/plugins/cad-material-sync/profiles/{profile_id}`
  - [x] `POST /api/v1/plugins/cad-material-sync/compose`
  - [x] `POST /api/v1/plugins/cad-material-sync/validate`
  - [x] `POST /api/v1/plugins/cad-material-sync/sync/outbound`
  - [x] `POST /api/v1/plugins/cad-material-sync/sync/inbound`
- [x] 通过插件配置服务扩展/覆盖 profile，不新增 v1 数据库迁移。
- [x] 单测覆盖默认 profile、规格合成、CAD 字段反向映射、配置覆盖、同步默认冲突策略、API smoke。

## Next TODO

- [ ] CAD 客户端适配层：
  - [x] AutoCAD 客户端命令接入 `cad-material-sync` 插件 API。
  - [x] AutoCAD/DWG 标题栏块属性读取。
  - [x] AutoCAD 表格字段读取和相邻单元格写回。
  - [x] CAD 端字段包写回明细栏/标题栏。
  - [x] AutoCAD 命令注册：`PLMMATPROFILES`、`PLMMATCOMPOSE`、`PLMMATPUSH`、`PLMMATPULL`。
  - [x] AutoCAD 配置页增加租户、组织、profile、dry-run 默认值。
  - [x] 抽象 `ICadMaterialFieldAdapter<TCadDocument>`，将 CAD 字段读写接口和 AutoCAD 实现解耦。
  - [x] 抽出不依赖 AutoCAD SDK 的 `CadMaterialFieldMapper`，支持 macOS fixture 验证字段规则。
  - [x] 服务端提供 CAD 字段差异预览 API，支撑 CAD 端确认写回 UI。
  - [x] 服务端/Workbench 提供 CAD 差异确认写回包与确认面板。
  - [x] 提供 CAD 差异确认写回包 contract fixture 和独立验证脚本，供 CAD 客户端接入。
  - [x] AutoCAD 客户端 `PLMMATPULL` 接入 `/diff/preview`，提供本地 WPF 差异预览和确认写回 UI。
  - [ ] SolidWorks 明细表/属性表字段读取。
    - [x] SDK-free SolidWorks 属性表/明细表 fixture 与 contract，固定字段归一化和写回字段包边界。
    - [x] SolidWorks Windows evidence 模板与 validator，固定真实 Add-in/COM/确认 UI smoke 的验收字段。
    - [x] SDK-free SolidWorks client skeleton：定义 Add-in/COM gateway、`CustomPropertyManager` 字段读取 seam 和写回边界。
    - [ ] 真实 SolidWorks Add-in/COM 读取实现与 Windows smoke。
  - [ ] SolidWorks 本地客户端可视化差异预览和确认写回 UI。
    - [x] SDK-free SolidWorks `/diff/preview` 确认写回包 fixture 与 contract，固定 `SW-*@Part` 写回字段和确认边界。
    - [x] SDK-free SolidWorks diff-preview client skeleton：固定 `cad_system=solidworks`、`write_cad_fields` 和确认/取消边界。
    - [x] SDK-free SolidWorks confirmation view-model：固定确认、取消/no-op、显式清空和 `write_cad_fields` 过滤。
    - [ ] 真实 SolidWorks 本地确认 UI、COM 写回和 Windows smoke。
- [x] PLM 管理端配置 UI：
  - [x] 服务端提供 profile 配置草稿预览/诊断 API，支撑 UI 实时预览。
  - [x] 服务端提供 profile 配置读取/保存/删除 API，保存前校验且写操作要求 admin。
  - [x] 服务端提供 profile 配置导入/导出包 API，支持 dry-run 和 hash 校验。
  - [x] Workbench 管理端接入 profile 列表、配置读取、草稿预览、保存、删除、导入/导出和 CAD 字段差异预览。
  - [x] 物料类别 profile 列表。
  - [x] 字段定义、CAD 字段名、必填、类型、单位配置。
  - [x] 规格模板配置与实时预览。
  - [x] 匹配键配置和 Workbench overwrite 默认策略配置。
  - [x] 后端按 profile 默认 overwrite 策略执行入站同步。
- [x] 物料库匹配增强：
  - [x] 按 `material_code`、`item_number`、`drawing_no` 精确匹配。
  - [x] 按物料类别、材料、规格组合匹配。
  - [x] 多匹配时返回候选列表给 CAD 端选择。
  - [x] profile 支持 `matching.strategies` 覆盖默认匹配优先级。
- [x] 字段治理：
  - [x] 明确 `specification` 是派生/cache 字段。
  - [x] 长宽厚、外径、壁厚、直径、毛坯尺寸等源字段保留为独立属性。
  - [x] 给动态属性增加推荐命名和 CAD key 配置模板。
- [x] 更通用适配：
  - [x] profile 支持单位换算和显示格式。
  - [x] profile 支持条件字段，例如锻件热处理、板材牌号标准。
  - [x] profile 支持多 CAD 软件别名字段。
  - [x] 服务端出站字段包支持按 `cad_system` 选择目标 CAD 主字段，例如 SolidWorks 属性名。
  - [x] profile 支持版本化和灰度发布。
- [ ] 更完整验证：
  - [x] 接真实数据库验证 item 更新和新建路径。
  - [x] 接现有 AutoCAD 客户端代码完成字段读取/写回开发。
  - [x] AutoCAD 客户端命令/API/XML 静态验证。
  - [x] macOS mock drawing fixture 验证字段抽取和回填规则。
  - [x] macOS 端到端 fixture 验证：CAD 字段 -> Yuantus 插件 dry-run -> CAD 字段回填。
  - [x] macOS 真实 SQLite DB 端到端验证：CAD 字段 -> PLM Item 创建/更新 -> outbound CAD 字段回填。
  - [x] 将 AutoCAD 2018 设为 Windows 客户端最低兼容构建基线，提供 2018/2024 版本化 package 和构建参数。
  - [x] 提供 Windows + AutoCAD 2018 预检脚本和真实 DWG smoke 验收指南。
  - [x] 提供 Yuantus 仓库级交付包验证，覆盖客户端迁移完整性、旧路径残留、构建产物排除和 macOS 可运行契约验证。
  - [ ] 在 Windows + AutoCAD 2018 环境编译 DLL 并做真实 DWG 手工 smoke。
  - [ ] 在 Windows + AutoCAD 2024 环境做回归 smoke，确保高版本路径未退化。

## Risks To Track

- `specification` 不应成为唯一事实源，否则后续搜索、变更影响分析、单位换算会困难。
- CAD 字段名在不同企业模板中差异很大，必须通过 profile 配置解决，不能硬编码到 CAD 端。
- 默认回写只填空字段是必要保护；批量 overwrite 必须要求用户显式请求或管理员配置 `sync_defaults.overwrite=true`，并在回写前有确认/审计边界。
- 服务端插件只生成字段包，不直接改 DWG/DXF 文件；实际写回应由 CAD 本地适配器完成。
