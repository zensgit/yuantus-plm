# Dev Report - Docs/ECO UI Summary Items

- 时间：2026-01-29 12:29 +0800
- 范围：产品详情文档与 ECO 摘要扩展（items 列表）

## 变更摘要

- `document_summary` 增加 `items/documents` 列表（与 sample 一致，便于 UI 渲染）
- `eco_summary` 增加 `items` 列表（包含 stage/版本/更新时间）
- 验证脚本增强：校验 `document_summary.items` 与 `eco_summary.items`
- 文档更新：`docs/PRODUCT_DETAIL_FIELD_MAPPING.md` & `docs/VERIFICATION.md`

## 影响范围

- `GET /api/v1/products/{item_id}`
  - 仅新增字段（向后兼容）

## 相关文件

- `src/yuantus/meta_engine/services/product_service.py`
- `scripts/verify_docs_eco_ui.sh`
- `docs/PRODUCT_DETAIL_FIELD_MAPPING.md`
- `docs/VERIFICATION.md`
