# CAD Material Config Store API Design And Verification

## Goal

补齐 CAD 物料 profile 管理端的配置持久化后端能力。前一轮已经有草稿预览和诊断，本轮新增当前作用域配置的读取、保存和删除接口，让管理端 UI 后续可以真正发布 profile 配置。

## API

新增：

```text
GET /api/v1/plugins/cad-material-sync/config
PUT /api/v1/plugins/cad-material-sync/config
DELETE /api/v1/plugins/cad-material-sync/config
```

### GET /config

返回当前租户/组织作用域已保存配置，以及配置生效后的 profile 列表。

```json
{
  "ok": true,
  "scope": {"tenant_id": "default", "org_id": "default"},
  "config": {},
  "profiles": []
}
```

### PUT /config

保存当前作用域配置。保存前复用 `preview_profile_config()` 做诊断；如果存在错误，返回 `ok=false` 且不落库。

```json
{
  "config": {
    "profiles": {
      "sheet": {
        "compose": {"template": "T{thickness}-{length}x{width}"},
        "cad_mapping": {"specification": "物料规格"}
      }
    }
  },
  "merge": false
}
```

成功响应：

```json
{
  "ok": true,
  "saved": true,
  "scope": {"tenant_id": "default", "org_id": "default"},
  "config": {},
  "profiles": [],
  "warnings": []
}
```

失败响应：

```json
{
  "ok": false,
  "saved": false,
  "errors": [
    {
      "profile_id": "sheet",
      "code": "unknown_template_field",
      "message": "compose template references unknown field 'missing_length'"
    }
  ]
}
```

### DELETE /config

删除当前作用域配置，恢复默认 profile。

## Authorization

- `GET /config`：需要已登录用户。
- `PUT /config`、`DELETE /config`：需要 `admin` / `superuser` role 或 `is_superuser=true`。
- 权限判断在插件内完成，避免普通 CAD 用户改全局物料规则。

## Design Notes

- 复用已有 `PluginConfigService` 和 `meta_plugin_configs`，不新增数据库迁移。
- 作用域来自 `get_request_context()` 的 `tenant_id` / `org_id`；缺省时落到 `default/default`。
- `merge=true` 时先把已保存配置和请求配置做深合并，再整体校验和保存。
- 保存接口返回生效后的 profile 列表，方便 UI 保存后立即刷新。
- 无效配置不落库，避免后续 CAD 客户端读取到坏 profile。

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
30 passed, 1 warning in 1.67s
```

新增覆盖用例：

- `test_config_routes_persist_validate_and_delete_profile_config`
  - 无效模板字段返回 `ok=false`，不写 `meta_plugin_configs`。
  - 有效配置可保存。
  - `GET /config` 返回保存后生效 profile。
  - `DELETE /config` 删除配置并恢复默认。
- `test_config_write_routes_require_admin`
  - 非 admin 用户 `PUT /config` 返回 403。
  - 非 admin 用户 `DELETE /config` 返回 403。
  - 权限失败不落库。

补充编译检查：

```bash
PYTHONPYCACHEPREFIX=.pytest_cache/pycache python3 -m py_compile plugins/yuantus-cad-material-sync/main.py src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py
```

结果：无输出，表示语法编译通过。

插件运行时 smoke：

```bash
PYTHONPATH=src YUANTUS_PLUGINS_ENABLED=yuantus-cad-material-sync python3 -c "from fastapi import FastAPI; from yuantus.plugin_manager.runtime import load_plugins; app=FastAPI(); manager=load_plugins(app); print(manager.get_plugin_stats() if manager else None); print(sorted(getattr(route, 'path', '') for route in app.routes if 'cad-material-sync' in getattr(route, 'path', '')))"
```

结果：`yuantus-cad-material-sync` active，11 条 `/api/v1/plugins/cad-material-sync/*` 路由正常挂载，包含 `GET/PUT/DELETE /api/v1/plugins/cad-material-sync/config`。

相关 CAD/插件回归：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/api/tests/test_plugin_runtime_security.py src/yuantus/meta_engine/tests/test_plugin_bom_compare.py src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py src/yuantus/meta_engine/tests/test_cad_properties_router.py src/yuantus/meta_engine/tests/test_cad_sync_template_router.py src/yuantus/meta_engine/tests/test_cad_import_service.py src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py -q
```

结果：

```text
101 passed, 1 skipped, 1 warning in 2.43s
```

## Remaining Boundary

本轮完成管理端配置持久化 API。后续仍需要前端页面来调用这些接口，包含 profile 列表、字段编辑、CAD key 别名编辑、模板预览、版本灰度配置和发布确认。
