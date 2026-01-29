# Dev Report - Product Detail File Aliases

- 时间：2026-01-29 12:24 +0800
- 范围：产品详情 `files[]` 字段别名与 UI 兼容补充

## 变更摘要

- 在 `ProductDetailService._get_files()` 中补充文件字段别名：
  - `name` = `filename`
  - `role` = `file_role`
  - `type` = `file_type`
  - `mime` = `mime_type`
  - `size` = `file_size`
  - `version` = `document_version`
  - `created_on` / `updated_on` = `created_at` / `updated_at`
- 更新产品详情字段映射文档：`docs/PRODUCT_DETAIL_FIELD_MAPPING.md`
- 扩展验证脚本校验文件别名字段：`scripts/verify_product_detail.sh`

## 影响范围

- `GET /api/v1/products/{item_id}`
  - 仅新增字段（向后兼容）

## 相关文件

- `src/yuantus/meta_engine/services/product_service.py`
- `scripts/verify_product_detail.sh`
- `docs/PRODUCT_DETAIL_FIELD_MAPPING.md`
