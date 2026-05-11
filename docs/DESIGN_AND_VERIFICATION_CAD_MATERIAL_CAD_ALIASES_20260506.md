# CAD Material Multi-CAD Field Aliases Design And Verification

## Goal

补齐 CAD 物料 profile 的多 CAD 字段别名能力，让同一个 PLM 属性可以适配不同 CAD 软件、不同企业图框模板和不同明细表字段名。

这个切片解决两类问题：

- 不同图纸模板中，同一含义可能叫 `材料`、`材质`、`Material` 或 `SW-Material@Part`。
- 出站写回需要一个稳定主字段名，入站读取需要能识别多个历史字段名和多 CAD 字段名。

## Design

映射规则保持向后兼容：

- 旧写法 `cad_key: "材料"` 继续有效。
- 旧写法 `cad_mapping: {"material": "材料"}` 继续有效。
- 新写法支持列表和字典：
  - 列表第一项是出站主写回字段，全部列表项都可用于入站识别。
  - 字典中的 `default` / `primary` / `cad_key` / `write` 是主字段候选。
  - 字典中的 `aliases` / `cad_aliases` / `cad_keys` / `read` / `autocad` / `solidworks` 等都作为入站别名。
  - 字典中的 `by_connector` / `by_cad` / `by_cad_system` / `cad_systems` / `connectors` 支持按 CAD 软件组织字段名。

出站行为：

- `cad_field_package()` 每个 PLM 属性只输出一个主 CAD 字段名，避免同一值重复写入多个图框字段造成覆盖歧义。
- 默认主字段优先来自 `cad_mapping`，字段定义中的 `cad_key` / `cad_keys` 作为补充；当请求传入 `cad_system` 且字段级配置有对应系统字段时，可覆盖 `cad_mapping` 中的普通默认字段。

入站行为：

- `cad_fields_to_properties()` 会把所有别名加入反向映射。
- CAD 传入任意别名字段时，都可还原到同一个 PLM 属性。
- 字段名仍经过 `normalize_cad_key()` 标准化，因此中英文模板和大小写差异可继续复用现有规范化逻辑。

## Examples

profile 片段：

```json
{
  "cad_mapping": {
    "material": {
      "default": "材料",
      "aliases": ["材质", "Material"],
      "solidworks": "SW-Material@Part"
    },
    "specification": ["规格", "物料规格", "SW-Specification@Part"]
  },
  "fields": [
    {
      "name": "length",
      "label": "长",
      "type": "number",
      "cad_key": "长",
      "cad_aliases": ["长度", "LENGTH"]
    }
  ]
}
```

入站可识别：

```json
{
  "SW-Material@Part": "Q235B",
  "LENGTH": "1200",
  "SW-Specification@Part": "legacy"
}
```

出站仍写主字段：

```json
{
  "材料": "Q235B",
  "长": 1200,
  "规格": "1200*600*12"
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
19 passed, 1 warning in 1.08s
```

新增覆盖用例：

- `test_cad_field_aliases_support_multiple_cad_templates`
  - `cad_mapping` 字典别名识别 `SW-Material@Part`。
  - `cad_mapping` 列表别名识别 `SW-Specification@Part`。
  - 字段级 `cad_aliases`、`cad_keys`、`cad_key_by_connector` 分别识别 `LENGTH`、`WIDTH`、`THICKNESS`。
  - 出站字段包仍只输出主字段 `材料`、`规格`、`长`、`宽`、`厚`。

补充编译检查：

```bash
PYTHONPYCACHEPREFIX=.pytest_cache/pycache python3 -m py_compile plugins/yuantus-cad-material-sync/main.py src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py
```

结果：无输出，表示语法编译通过。

插件运行时 smoke：

```bash
PYTHONPATH=src YUANTUS_PLUGINS_ENABLED=yuantus-cad-material-sync python3 -c "from fastapi import FastAPI; from yuantus.plugin_manager.runtime import load_plugins; app=FastAPI(); manager=load_plugins(app); print(manager.get_plugin_stats() if manager else None); print(sorted(getattr(route, 'path', '') for route in app.routes if 'cad-material-sync' in getattr(route, 'path', '')))"
```

结果：`yuantus-cad-material-sync` active，6 个 `/api/v1/plugins/cad-material-sync/*` 路由正常挂载。

相关 CAD/插件回归：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/api/tests/test_plugin_runtime_security.py src/yuantus/meta_engine/tests/test_plugin_bom_compare.py src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py src/yuantus/meta_engine/tests/test_cad_properties_router.py src/yuantus/meta_engine/tests/test_cad_sync_template_router.py src/yuantus/meta_engine/tests/test_cad_import_service.py src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py -q
```

结果：

```text
90 passed, 1 skipped, 1 warning in 1.80s
```

## Follow-Up

后续切片已增加显式 `cad_system` 参数，出站可按 AutoCAD/SolidWorks 等目标系统选择主字段。详见 `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_CAD_SYSTEM_OUTPUT_20260506.md`。
