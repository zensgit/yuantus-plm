# Dev Report - UI Integration Checklist

- 时间：2026-01-29 13:29 +0800
- 目的：为前端联调提供字段清单与契约概览

## 产品详情（/products/{id}）

### item
- 核心字段：`id/type/item_type_id/item_type/item_number/number/name/item_name/title/state/status/current_state`
- 时间别名：`created_at/created_on`、`updated_at/modified_on`
- 其他：`current_version_id/description/properties`

### files[]
- 原字段：`filename/file_role/file_type/mime_type/file_size/document_version`
- 别名：`name/role/type/mime/size/version`
- CAD 摘要：`is_cad/is_native_cad/cad_format/cad_connector_id/cad_document_schema_version/cad_review_state/cad_review_note/cad_review_by_id/cad_reviewed_at/conversion_status`
- URL：`preview_url/geometry_url/cad_manifest_url/cad_document_url/cad_metadata_url/cad_bom_url/download_url`
- 时间别名：`created_at/created_on`、`updated_at/updated_on`

### document_summary / eco_summary
- document_summary：`count/state_counts/sample/items/documents`
- eco_summary：`count/state_counts/pending_approvals/last_applied/items`

## BOM UI

### where-used
- 入口：`/bom/{id}/where-used`
- 列表项：`parent/child/relationship/line/line_normalized/level`
- 别名：`parent_number/parent_name/child_number/child_name`

### bom_compare
- 入口：`/bom/compare?include_child_fields=true`
- added/removed/changed 均包含：`parent/child` + `parent_number/parent_name/child_number/child_name`

### substitutes
- 入口：`/bom/{bom_line_id}/substitutes`
- 列表项：`substitute_part/part/relationship/rank`
- 别名：`substitute_number/substitute_name`

## 验证脚本

- `scripts/verify_product_detail.sh`
- `scripts/verify_product_ui.sh`
- `scripts/verify_where_used_ui.sh`
- `scripts/verify_bom_ui.sh`
- `scripts/verify_docs_approval.sh`
- `scripts/verify_docs_eco_ui.sh`
