# CAD Material Unit And Format Design And Verification

## Goal

补齐 CAD 物料 profile 的单位换算和显示格式能力：CAD 或用户输入可以带单位，PLM 属性保留标准单位数值，规格模板按 profile 声明的显示单位和格式输出。

这个切片解决跨 CAD 模板常见问题：有的图纸按 `mm` 填写，有的按 `cm`、`m` 或英寸填写，但 PLM 物料属性需要统一标准单位，规格栏又要按企业习惯显示。

## Design

数值字段支持以下 profile 配置：

- `unit`：PLM 标准单位，例如 `mm`。
- `input_unit`：无单位数字的默认输入单位。
- `cad_unit`：CAD 字段默认输入单位，优先级低于输入值自带单位。
- `display_unit`：规格模板渲染时的显示单位。
- `display_precision`：规格模板渲染精度。
- `display_format`：Python format spec，例如 `.2f`。
- `display_suffix`：渲染后缀，例如 `mm`。
- `trim_zeros`：使用 `display_precision` 时是否移除尾随零，默认 true。

输入支持：

- 普通数字：`1200`
- 带单位字符串：`60cm`、`1.2m`、`0.5in`
- 字典：`{"value": 1.2, "unit": "m"}`

当前内置长度换算：

- `mm`、`millimeter`、`毫米`
- `cm`、`centimeter`、`厘米`
- `m`、`meter`、`米`
- `in`、`inch`、`"`

行为边界：

- PLM properties 存标准单位数值。
- `specification` 等模板输出使用显示单位和格式。
- 不支持的单位组合返回 `invalid_unit`，不静默猜测。

## Example

profile 片段：

```json
{
  "fields": [
    {
      "name": "length",
      "type": "number",
      "unit": "mm",
      "display_unit": "cm",
      "display_precision": 1
    },
    {
      "name": "thickness",
      "type": "number",
      "unit": "mm",
      "display_precision": 1,
      "display_suffix": "mm"
    }
  ],
  "compose": {
    "template": "{length}cm*{thickness}"
  }
}
```

输入：

```json
{
  "length": {"value": 1.2, "unit": "m"},
  "thickness": "0.5in"
}
```

标准属性：

```json
{
  "length": 1200,
  "thickness": 12.7
}
```

规格输出：

```text
120cm*12.7mm
```

## Verification

目标插件测试：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py -q
```

结果：

```text
16 passed, 1 warning in 1.06s
```

覆盖用例：

- `m`、`cm`、`in` 输入转换为标准 `mm` 属性。
- 规格模板按 `display_unit`、`display_precision` 和 `display_suffix` 渲染。
- 不支持的单位组合返回 `invalid_unit`。

## Remaining Boundary

当前实现覆盖长度单位。重量、面积、体积或企业自定义单位可在后续扩展单位表或 profile 配置单位族，不应在 CAD 客户端硬编码。
