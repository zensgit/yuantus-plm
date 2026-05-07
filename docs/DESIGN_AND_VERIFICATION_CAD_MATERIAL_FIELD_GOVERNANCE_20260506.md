# CAD Material Field Governance Design And Verification

## Goal

补齐 CAD 物料 profile 的字段治理能力，明确哪些字段是事实源，哪些字段只是派生/cache，并给 CAD 客户端和后续管理端 UI 提供统一元数据。

这个切片解决三个风险：

- `specification` 不应成为唯一事实源。
- 长、宽、厚、外径、壁厚、直径、毛坯尺寸等源字段必须独立保存。
- CAD 或用户传入旧规格时，系统应明确提示已按源字段重新合成。

## Design

`load_profiles()` 现在会为每个 profile 注入 `governance`：

```json
{
  "derived_fields": {
    "specification": {
      "role": "derived_cache",
      "cache": true,
      "source_of_truth": false,
      "sources": ["length", "width", "thickness"],
      "template": "{length}*{width}*{thickness}",
      "recompute_policy": "recompute_from_source_fields",
      "mismatch_warning": "derived_field_mismatch"
    }
  },
  "source_fields": [
    {
      "name": "length",
      "label": "长",
      "type": "number",
      "unit": "mm",
      "cad_keys": ["长"],
      "role": "source_of_truth"
    }
  ],
  "dynamic_property_templates": {
    "property_name": "{profile_id}_{field_name}",
    "cad_key": "{field_label}",
    "custom_field_prefix": "material_",
    "naming_style": "snake_case"
  }
}
```

运行时行为：

- `specification` 仍由 `compose.template` 生成。
- 若 CAD 入站或用户输入中已带 `specification`，且它与源字段合成结果不同，`compose_profile()` 返回 `derived_field_mismatch` warning。
- `sync/inbound` 响应新增 `warnings`，CAD 客户端可以把“旧规格已被源字段重算”展示给用户。
- 字段治理元数据可被 `GET /profiles` 和 `GET /profiles/{profile_id}` 直接读取，不需要新增 API。

兼容性：

- 旧 profile 不需要配置 `governance`，服务端自动生成默认治理元数据。
- 若企业已有特殊治理规则，可以通过 profile `governance` 覆盖默认值。
- 不改变现有规格合成策略：源字段仍覆盖传入的规格 cache。

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
23 passed, 1 warning in 1.16s
```

新增覆盖用例：

- `test_profile_governance_marks_specification_as_derived_cache`
  - `specification` 标记为 `derived_cache`。
  - `source_of_truth=false`，`cache=true`。
  - 板材规格源字段是 `length`、`width`、`thickness`。
  - 源字段保留单位和 CAD key。
  - 暴露动态属性命名模板。
- `test_compose_warns_when_incoming_derived_specification_is_recomputed`
  - 输入旧规格时，系统仍按源字段合成新规格。
  - 返回 `derived_field_mismatch` warning。
- `test_sync_inbound_can_create_update_and_outbound_from_real_sqlite_db`
  - CAD 入站带旧规格时，`sync/inbound` dry-run 返回 warning。

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
94 passed, 1 skipped, 1 warning in 1.60s
```

## Remaining Boundary

当前字段治理已在服务端 profile 元数据和同步响应中生效。后续管理端 UI 需要读取 `governance.source_fields`、`governance.derived_fields` 和 `dynamic_property_templates`，把“事实源字段”和“派生字段”在配置界面分开显示。
