# CAD Material Target CAD System Output Design And Verification

## Goal

补齐服务端插件的目标 CAD 系统选择能力，让同一个物料 profile 在出站写回时可以按 AutoCAD、SolidWorks、ZWCAD 等目标系统选择不同主字段名。

这个切片解决的问题是：入站早已能识别多 CAD 字段别名，但出站默认只选择第一个主字段。SolidWorks 这类插件通常要写 `SW-Material@Part`、`SW-Specification@Part` 等属性名，如果仍输出 `材料`、`规格`，客户端还要做二次映射，通用适配层会分散到各 CAD 客户端。

## Design

请求模型新增可选字段：

- `cad_system`

支持接口：

- `POST /api/v1/plugins/cad-material-sync/compose`
- `POST /api/v1/plugins/cad-material-sync/validate`
- `POST /api/v1/plugins/cad-material-sync/config/preview`
- `POST /api/v1/plugins/cad-material-sync/diff/preview`
- `POST /api/v1/plugins/cad-material-sync/sync/outbound`
- `POST /api/v1/plugins/cad-material-sync/sync/inbound`

`cad_system` 支持别名归一化：

- `solidworks`、`solid_works`、`solid-works`、`sw` -> `solidworks`
- `autocad`、`auto_cad`、`auto-cad`、`dwg` -> `autocad`
- `zwcad`、`inventor`、`nx`、`creo` 保持同名

profile 可用两类写法声明目标系统字段：

```json
{
  "cad_mapping": {
    "material": {
      "default": "材料",
      "solidworks": "SW-Material@Part"
    },
    "specification": {
      "default": "规格",
      "solidworks": "SW-Specification@Part"
    }
  },
  "fields": [
    {
      "name": "length",
      "cad_key": "长",
      "cad_key_by_connector": {
        "solidworks": "SW-Length@Part"
      }
    }
  ]
}
```

兼容的配置容器：

- 字段级：`cad_key_by_connector`、`cad_keys_by_connector`、`cad_system_keys`、`connector_keys`
- 字典级：`by_connector`、`by_cad`、`by_cad_system`、`cad_systems`、`connectors`
- 直接键：`solidworks`、`autocad`、`zwcad`、`inventor`、`nx`、`creo`

出站选择顺序：

- 请求未传 `cad_system`：沿用默认主字段，保持旧行为。
- `cad_mapping` 声明了目标系统字段：优先使用该字段。
- `cad_mapping` 只有默认字段、字段定义声明了目标系统字段：字段级目标系统字段覆盖默认字段。
- 目标系统没有专属字段：回退 `default`、`primary`、`cad_key`、列表第一项等旧主字段。

入站行为不因 `cad_system` 变窄：反向映射继续识别所有别名，避免历史图纸或混合模板无法读取。

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
34 passed, 1 warning in 1.87s
```

新增覆盖用例：

- `test_cad_field_package_can_select_target_cad_system_keys`
  - 默认出站仍输出 `材料`、`规格`。
  - `cad_system=solidworks` 时输出 `SW-Material@Part`、`SW-Length@Part`、`SW-Width@Part`、`SW-Thickness@Part`、`SW-Specification@Part`。
- `test_config_preview_route_can_render_target_cad_system_fields`
  - `/config/preview` 在 profile 草稿场景下能按 `cad_system=solidworks` 生成 SolidWorks 字段包。
  - 字段级 `cad_key_by_connector.solidworks` 能覆盖继承来的默认 `cad_mapping.material=材料`。

插件运行时 smoke：

```bash
PYTHONPATH=src YUANTUS_PLUGINS_ENABLED=yuantus-cad-material-sync python3 -c "from fastapi import FastAPI; from yuantus.plugin_manager.runtime import load_plugins; app=FastAPI(); manager=load_plugins(app); print(manager.get_plugin_stats() if manager else None); print(sorted(getattr(route, 'path', '') for route in app.routes if 'cad-material-sync' in getattr(route, 'path', '')))"
```

结果：

```text
{'total': 4, 'by_status': {'discovered': 3, 'active': 1}, 'by_type': {'extension': 4}, 'by_category': {'demo': 1, 'cad': 1, 'files': 1, 'bom': 1}, 'errors': 0}
['/api/v1/plugins/cad-material-sync/compose', '/api/v1/plugins/cad-material-sync/config', '/api/v1/plugins/cad-material-sync/config', '/api/v1/plugins/cad-material-sync/config', '/api/v1/plugins/cad-material-sync/config/export', '/api/v1/plugins/cad-material-sync/config/import', '/api/v1/plugins/cad-material-sync/config/preview', '/api/v1/plugins/cad-material-sync/diff/preview', '/api/v1/plugins/cad-material-sync/profiles', '/api/v1/plugins/cad-material-sync/profiles/{profile_id}', '/api/v1/plugins/cad-material-sync/sync/inbound', '/api/v1/plugins/cad-material-sync/sync/outbound', '/api/v1/plugins/cad-material-sync/validate']
```

相关 CAD/插件回归：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/api/tests/test_plugin_runtime_security.py src/yuantus/meta_engine/tests/test_plugin_bom_compare.py src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py src/yuantus/meta_engine/tests/test_cad_properties_router.py src/yuantus/meta_engine/tests/test_cad_sync_template_router.py src/yuantus/meta_engine/tests/test_cad_import_service.py src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py -q
```

结果：

```text
105 passed, 1 skipped, 1 warning in 2.64s
```

语法编译：

```bash
PYTHONPYCACHEPREFIX=.pytest_cache/pycache python3 -m py_compile plugins/yuantus-cad-material-sync/main.py src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py
```

结果：无输出，表示语法编译通过。

## Remaining Boundary

这个切片完成的是服务端字段包选择，不等于完成真实 SolidWorks 客户端适配。SolidWorks 端仍需单独实现明细表/属性表读取、写回和真实客户端 smoke。
