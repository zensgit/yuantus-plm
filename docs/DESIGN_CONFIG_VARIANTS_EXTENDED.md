# Config/Variant BOM 条件表达增强设计

## 目标

扩展 BOM 行 `config_condition` 的表达能力，支持更丰富的条件运算（数值比较、包含、存在性、范围等），在不破坏既有 `key=value`/JSON 规则的前提下提升变型过滤能力。

## 现有模型

- BOM 行为 `meta_items`（Relationship Item），其 `properties.config_condition` 保存条件表达式。
- 查询时通过 `/api/v1/bom/{id}/tree?config=<JSON>` 传入配置选择。
- 服务器端在 BOM 过滤时调用 `BOMService._match_config_condition()`。

## 新增语义

### 1) 条件表达式结构

支持 JSON 对象：

```json
{"option":"Color","value":"Red"}
```

支持逻辑组合：

```json
{"all":[{"option":"Color","value":"Red"},{"option":"Voltage","op":"gte","value":200}]}
```

支持简写字符串：

```
Voltage>=200;Color=Red
```

### 2) 运算符

- `eq`（默认）/ `ne`
- `gt` / `gte` / `lt` / `lte`
- `in` / `not_in`
- `contains`（列表包含 / 字符串子串）
- `regex`（正则匹配）
- `exists` / `missing`
- `between` / `range`（或 `min`/`max`）

### 3) 选择值规范化

- `config` 选择 JSON 中的值允许是：字符串、数值、列表、对象。
- 对象选择值会优先读取 `value` / `key` / `id`。
- 多选列表按 **任一匹配** 通过条件。
- 数值比较会优先尝试 `Decimal` 转换，失败则回退为字符串比较。

## 兼容性

- 原 `{"option":"X","value":"Y"}` 与 `key=value` 表达式保持不变。
- 原逻辑中的 `all/any/not` 仍完全兼容。

## 关键实现点

- `BOMService._normalize_selection_value()`：统一选择值表示。
- `BOMService._has_value()`：判断存在性。
- `BOMService._coerce_number()`：数值比较的统一入口。
- `BOMService._parse_simple_condition()`：支持 `= != >= <= > < ~` 运算符。

## 示例

```json
{"option":"Voltage","op":"gte","value":200}
```

```json
{"option":"Features","op":"contains","value":"Cooling"}
```

```json
{"option":"Region","missing":true}
```

```json
{"option":"Color","op":"in","values":["Red","Blue"]}
```

```json
{"option":"Temp","op":"between","range":[-10, 60]}
```

## 验证

- 脚本：`scripts/verify_config_variants.sh`
- 覆盖：eq、gte、contains、ne、exists、missing、简写表达式
