# Where-Used Line Schema Design (2026-01-24 21:20 +0800)

目标：为前端提供稳定的 BOM where-used 行字段元数据（字段名、规范化、严重度），用于展示/过滤配置。

## 范围

- 新增端点：`GET /api/v1/bom/where-used/schema`
- 输出字段：`line_fields[]`，包含 `field / severity / normalized / description`
- 权限：`Part BOM` 的 `get` 权限

## 行为

- 字段顺序与 `BOMService.LINE_FIELD_KEYS` 保持一致
- 规范化/严重度规则与 BOM compare 保持一致
- 不引入新的过滤开关，仅提供 schema 元数据

## 非目标

- 不改变 where-used 返回内容
- 不新增 compare 模式或 line_key 计算

## 关联实现

- `BOMService.line_schema()` 复用 compare 字段元信息
- `BOMService.compare_schema()` 复用 `line_schema` 返回
