# 设计文档：并行支线 P1-1 BOM Delta Markdown 导出扩展

- 日期：2026-03-01
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 范围：为 BOM delta 导出新增 markdown 格式，并保持字段过滤与摘要一致性。

## 1. 目标

1. `compare/delta/export` 支持 `md` 导出，方便评审直接阅读。
2. markdown 导出包含摘要（总量、风险分布、compare summary）与操作表。
3. 保持与 `json/csv` 共用同一字段过滤规则。

## 2. 方案

## 2.1 服务层

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/bom_service.py`

新增方法：
- `export_delta_markdown(delta_preview, fields)`

行为：
1. 若输入未过滤，内部复用 `filter_delta_preview_fields(...)`。
2. 输出结构：
- `# BOM Delta Preview`
- `## Summary`（`summary`、`change_summary`、`compare_summary`）
- `## Operations`（按 `selected_fields` 渲染 markdown 表格）
3. 空操作时输出 `_No operations_`。

## 2.2 路由层

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/bom_router.py`

增强：
- `GET /api/v1/bom/compare/delta/export`
  - `export_format` 从 `json|csv` 扩展为 `json|csv|md`
  - `md` 返回 `text/markdown`，下载名 `bom-delta-preview.md`
  - 非法格式错误更新为：`export_format must be json, csv or md`

## 3. 兼容性

1. 现有 `json/csv` 路径保持不变。
2. 不涉及数据库迁移。
3. 仅新增导出格式，向后兼容。

## 4. 风险与回滚

1. 风险
- markdown 表格对复杂字段（dict/list）可读性受限。

2. 缓解
- 复杂字段统一 JSON 字符串化输出，避免歧义。

3. 回滚
- 回滚 `export_delta_markdown` 与路由 `md` 分支即可。

## 5. 验收标准

1. `compare/delta/export?export_format=md` 返回 markdown 下载流。
2. markdown 导出支持 `fields` 过滤。
3. 非法格式返回 `400` 且错误文案符合约定。
4. 服务与路由测试通过。
