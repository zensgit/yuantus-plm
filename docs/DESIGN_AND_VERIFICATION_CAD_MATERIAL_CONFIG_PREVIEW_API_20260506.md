# CAD Material Config Preview API Design And Verification

## Goal

补齐 CAD 物料 profile 管理端 UI 所需的后端基础能力：管理端可以提交草稿配置，服务端返回合并后的 profile、配置诊断、当前生效版本和样例规格预览。

这个切片先做 API，不做前端页面，目的是让后续 UI 在保存前能实时回答：

- 这个 profile 草稿最终会合并成什么规则。
- 当前 `active_version` / `rollout` 选择了哪个版本。
- 规格模板能否正确合成。
- CAD 字段包最终会写回哪些字段。
- 配置是否有模板字段缺失、版本名错误或 CAD key 冲突。

## API

新增：

```text
POST /api/v1/plugins/cad-material-sync/config/preview
```

请求体：

```json
{
  "profile_id": "sheet",
  "include_profiles": true,
  "config": {
    "profiles": {
      "sheet": {
        "active_version": "v2",
        "versions": {
          "v2": {
            "compose": {"template": "PL{thickness}-{length}x{width}"},
            "cad_mapping": {"specification": "物料规格"}
          }
        }
      }
    }
  },
  "values": {
    "material": "Q235B",
    "length": 1200,
    "width": 600,
    "thickness": 12
  }
}
```

响应体核心字段：

```json
{
  "ok": true,
  "profile_id": "sheet",
  "profiles": [],
  "profile": {
    "profile_id": "sheet",
    "profile_version": "v2",
    "available_versions": ["v2"]
  },
  "preview": {
    "properties": {"specification": "PL12-1200x600"},
    "composed": {"specification": "PL12-1200x600"},
    "cad_fields": {"物料规格": "PL12-1200x600"},
    "errors": [],
    "warnings": []
  },
  "errors": [],
  "warnings": []
}
```

## Diagnostics

当前诊断覆盖：

- `missing_profile_id`：profile 配置缺少 profile id。
- `unknown_active_version`：`active_version` 指向未定义版本。
- `unknown_template_field`：规格模板引用不存在字段。
- `compose_failed`：样例值无法完成规格合成。
- `missing_fields`：profile 没有字段。
- `missing_field_name`：字段定义缺少 name。
- CAD key 重复映射 warning。
- `default_version` 指向未定义版本 warning。
- 派生规格和输入规格不一致时的 `derived_field_mismatch` warning。

## Design Notes

- 预览接口不写 `PluginConfigService`，只对请求体草稿做解析和诊断。
- 预览复用 `load_profiles(config=...)`，因此单位、条件字段、多 CAD 别名、版本化/灰度、字段治理都会按真实运行规则解析。
- `include_profiles=false` 可让前端只取单个 profile 和预览结果，避免大配置反复传输。
- 预览响应中的 `profile.governance` 可直接驱动管理端把事实源字段和派生/cache 字段分开显示。
- 该接口目前复用插件现有登录用户依赖；真正保存配置的接口后续应要求 admin 权限。

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
26 passed, 1 warning in 1.17s
```

新增覆盖用例：

- `test_profile_config_preview_returns_preview_and_diagnostics`
  - 草稿 `active_version=v2` 生效。
  - 返回合成规格和 CAD 字段包。
  - 返回完整 profile 列表。
- `test_profile_config_preview_reports_unknown_template_field`
  - 模板引用不存在字段时返回 `unknown_template_field`。
  - 样例合成失败时返回 `compose_failed`。
- `test_config_preview_route_can_hide_full_profile_list`
  - 路由可用。
  - `include_profiles=false` 时隐藏完整 profile 列表。
  - 返回单 profile 预览结果。

补充编译检查：

```bash
PYTHONPYCACHEPREFIX=.pytest_cache/pycache python3 -m py_compile plugins/yuantus-cad-material-sync/main.py src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py
```

结果：无输出，表示语法编译通过。

插件运行时 smoke：

```bash
PYTHONPATH=src YUANTUS_PLUGINS_ENABLED=yuantus-cad-material-sync python3 -c "from fastapi import FastAPI; from yuantus.plugin_manager.runtime import load_plugins; app=FastAPI(); manager=load_plugins(app); print(manager.get_plugin_stats() if manager else None); print(sorted(getattr(route, 'path', '') for route in app.routes if 'cad-material-sync' in getattr(route, 'path', '')))"
```

结果：`yuantus-cad-material-sync` active，7 个 `/api/v1/plugins/cad-material-sync/*` 路由正常挂载，包含 `/api/v1/plugins/cad-material-sync/config/preview`。

相关 CAD/插件回归：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/api/tests/test_plugin_runtime_security.py src/yuantus/meta_engine/tests/test_plugin_bom_compare.py src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py src/yuantus/meta_engine/tests/test_cad_properties_router.py src/yuantus/meta_engine/tests/test_cad_sync_template_router.py src/yuantus/meta_engine/tests/test_cad_import_service.py src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py -q
```

结果：

```text
97 passed, 1 skipped, 1 warning in 1.82s
```

## Remaining Boundary

这个切片只完成管理端 UI 所需的预览/诊断后端接口。后续仍需要前端页面，包含 profile 列表、字段编辑、CAD key 别名编辑、模板实时预览、匹配策略编辑、版本灰度配置和保存发布流程。
