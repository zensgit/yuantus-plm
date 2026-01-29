# Release Notes - v0.1.3

日期：2026-01-29

## 亮点

- 配置变体条件表达增强（支持 op 运算、exists/missing、范围/正则/包含）
- 产品详情 `files[]` 增加 UI 别名字段（name/type/role/mime/size/version/created_on/updated_on）
- 产品详情摘要扩展：`document_summary.items`、`eco_summary.items`
- BOM UI 输出别名：where-used / bom_compare / substitutes 增强
- UI 端联调清单与验证文档补齐

## 变更明细

### Config Variants
- 扩展 `config_condition` 语义，兼容旧规则且支持复杂条件表达

### Product Detail
- `files[]` 新增别名字段，保持向后兼容
- 文档/ECO 摘要新增 `items` 便于 UI 列表渲染

### BOM UI
- where-used/bom_compare/substitutes 输出新增 UI 友好别名字段

## 验证

- 全量回归（UI + Config）：`docs/VERIFICATION_RUN_ALL_UI_CONFIG_20260129_1322.md`
- UI 联调验证：`docs/VERIFICATION_UI_INTEGRATION_20260129_1329.md`

## 兼容性

- 所有新增字段均为“增量扩展”，不破坏现有调用。
