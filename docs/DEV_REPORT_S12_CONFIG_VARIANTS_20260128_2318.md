# S12 Configuration/Variant BOM 开发报告（2026-01-28 23:18）

## 目标

在 BOM 关系上支持配置条件过滤（Config Variants），并提供配置选项集管理能力。

## 关键实现

### 1) 配置选项集模型与 API

- 新增模型：`meta_config_option_sets`、`meta_config_options`
- 新增服务：`ConfigService`
- 新增路由：`/api/v1/config/option-sets` 与子资源 `/options`
- 权限：写操作仅 `superuser` 允许（保持与 Meta Schema 管理一致）

### 2) BOM 关系支持配置条件

- BOM 关系新增 `config_condition` 字段
- `GET /bom/{id}/tree` / `effective` / `mbom` 支持 `config` 参数
- 支持简单表达式与 JSON 规则
  - 示例（JSON）：`{"all":[{"option":"Color","value":"Red"},{"option":"Voltage","value":"220"}]}`
  - 示例（简化字符串）：`Color=Red;Voltage=220`

### 3) 迁移

- 迁移文件：`migrations/versions/o1b2c3d4e6a3_add_config_options.py`
- 新增表：`meta_config_option_sets`、`meta_config_options`
- 默认值使用 `server_default` 以兼容 Postgres

## 主要文件

- `src/yuantus/meta_engine/models/configuration.py`
- `src/yuantus/meta_engine/services/config_service.py`
- `src/yuantus/meta_engine/web/config_router.py`
- `src/yuantus/meta_engine/services/bom_service.py`
- `src/yuantus/meta_engine/web/bom_router.py`
- `src/yuantus/api/app.py`
- `scripts/verify_config_variants.sh`
- `docs/DESIGN_CONFIG_VARIANTS_20260128.md`

## 变更摘要

- 新增配置选项集 CRUD API（option set / option）
- BOM 添加 `config_condition` 并在树/生效接口中根据配置选择过滤
- 验证脚本与文档补齐

## 风险与回退

- 配置判断逻辑为纯读取路径，默认不传 `config` 不影响现有行为
- 若需回退：可停止使用 `config_condition`，并保留数据表不影响旧功能
