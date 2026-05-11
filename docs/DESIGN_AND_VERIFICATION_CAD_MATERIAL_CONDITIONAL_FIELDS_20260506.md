# CAD Material Conditional Fields Design And Verification

## Goal

补齐 CAD 物料 profile 的条件字段能力，让不同物料类别、材料牌号或用户输入状态可以触发不同属性要求。

这个切片直接服务以下场景：

- 板材仅在指定材料牌号下要求填写板材标准。
- 锻件仅在填写热处理时要求填写热处理标准。
- CAD 客户端打开插件后可从 profile 获取当前类别实际需要的字段规则。

## Design

字段配置新增条件表达：

- `when` / `condition` / `visible_when`：控制字段是否启用。
- `required_when`：控制字段是否在特定条件下必填。

支持的条件操作：

- `equals` / `not_equals`
- `in` / `not_in`
- `exists` / `missing` / `blank`
- `contains`
- `regex`
- `all` / `any` / `none` 组合条件
- `op` / `operator` + `value` 的兼容写法，例如 `{"field": "material", "op": "in", "value": ["Q235B"]}`

执行规则：

- `compose_profile()` 会先把 profile `selector` 合并进待校验值，再执行字段条件判断。因此字段条件可以依赖 `material_category` 等类别默认值。
- 条件不满足且字段为空时，该字段不会被要求、不会写入 normalized properties，也不会进入 CAD 字段包。
- 条件不满足但调用方显式传了值时，仍按字段类型做规范化，避免用户或 CAD 已有值被静默丢弃。
- `required_when` 不改变字段启用状态，只改变必填要求；适合“填了热处理，则热处理标准必填”这类上下文字段。
- 服务端只负责规则、校验和字段包输出；CAD 客户端仍按 profile/cad_fields 执行实际图纸回填。

## Examples

板材标准按材料牌号触发：

```json
{
  "name": "plate_standard",
  "label": "板材标准",
  "type": "string",
  "required": true,
  "cad_key": "板材标准",
  "when": {
    "all": [
      {"field": "material_category", "equals": "sheet"},
      {"field": "material", "in": ["Q235B", "Q355B"]}
    ]
  }
}
```

锻件热处理标准按用户输入触发：

```json
{
  "name": "heat_treatment_standard",
  "label": "热处理标准",
  "type": "string",
  "required_when": {"field": "heat_treatment", "exists": true},
  "cad_key": "热处理标准"
}
```

## Files

- `plugins/yuantus-cad-material-sync/main.py`
- `src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py`
- `docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md`
- `docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_PLUGIN_20260506.md`

## Verification

目标插件测试：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py -q
```

结果：

```text
18 passed, 1 warning in 0.94s
```

新增覆盖用例：

- `test_conditional_required_field_only_applies_when_condition_matches`
  - `material=Q235B` 且 `material_category=sheet` 时，`plate_standard` 必填。
  - `material=6061` 时，`plate_standard` 不触发必填，也不会进入 properties。
  - `plate_standard` 填写后进入 CAD 字段包。
- `test_required_when_can_make_forging_attribute_contextual`
  - 锻件未填写 `heat_treatment` 时，不要求 `heat_treatment_standard`。
  - 填写 `heat_treatment` 后，`heat_treatment_standard` 必填。
  - 填写完整后，字段保留在 normalized properties 中。

补充编译检查：

```bash
PYTHONPYCACHEPREFIX=.pytest_cache/pycache python3 -m py_compile plugins/yuantus-cad-material-sync/main.py src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py
```

结果：无输出，表示语法编译通过。

相关 CAD/插件回归：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/api/tests/test_plugin_runtime_security.py src/yuantus/meta_engine/tests/test_plugin_bom_compare.py src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py src/yuantus/meta_engine/tests/test_cad_properties_router.py src/yuantus/meta_engine/tests/test_cad_sync_template_router.py src/yuantus/meta_engine/tests/test_cad_import_service.py src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py -q
```

结果：

```text
89 passed, 1 skipped, 1 warning in 1.33s
```

## Remaining Boundary

当前条件表达已满足物料 profile 的字段动态化。后续管理端 UI 需要把这些条件作为可编辑配置暴露出来，并在表单端按同一规则做前端显隐和实时必填提示，避免用户只能在提交后看到服务端错误。
