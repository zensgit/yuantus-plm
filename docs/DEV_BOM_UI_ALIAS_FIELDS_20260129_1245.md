# Dev Report - BOM UI Alias Fields

- 时间：2026-01-29 12:45 +0800
- 范围：Where-Used / BOM Compare / Substitutes UI 负载增强

## 变更摘要

- Where-Used 输出增加别名字段：`parent_number/parent_name/child_number/child_name`
- BOM Compare 输出增加别名字段：`parent_number/parent_name/child_number/child_name`
- Substitute 列表增加别名字段：`substitute_number/substitute_name`
- UI 验证脚本新增别名字段校验

## 影响范围

- `GET /api/v1/bom/{item_id}/where-used`
- `GET /api/v1/bom/compare`
- `GET /api/v1/bom/{bom_line_id}/substitutes`

## 相关文件

- `src/yuantus/meta_engine/services/bom_service.py`
- `src/yuantus/meta_engine/services/substitute_service.py`
- `src/yuantus/meta_engine/web/bom_router.py`
- `scripts/verify_bom_ui.sh`
- `docs/VERIFICATION.md`
