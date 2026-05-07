# CAD Material Config Bundle API Design And Verification

## Goal

补齐 CAD 物料 profile 配置的导入/导出包能力。管理员可以把测试环境验证过的 profile 配置导出为 bundle，再 dry-run 导入目标环境，确认无误后正式导入。

这个切片服务三类场景：

- 测试环境到生产环境的配置迁移。
- 不同租户/组织之间复制同一套 CAD 物料规则。
- 保存配置前后保留可校验的回滚包。

## API

新增：

```text
GET /api/v1/plugins/cad-material-sync/config/export
POST /api/v1/plugins/cad-material-sync/config/import
```

### Export

返回当前作用域已保存配置、合并后 profile，以及可导入的 bundle：

```json
{
  "ok": true,
  "scope": {"tenant_id": "default", "org_id": "default"},
  "bundle": {
    "schema_version": 1,
    "plugin_id": "yuantus-cad-material-sync",
    "exported_at": "2026-05-06T00:00:00Z",
    "scope": {"tenant_id": "default", "org_id": "default"},
    "config_hash": "sha256...",
    "config": {}
  }
}
```

### Import

请求体：

```json
{
  "bundle": {
    "schema_version": 1,
    "plugin_id": "yuantus-cad-material-sync",
    "config_hash": "sha256...",
    "config": {}
  },
  "merge": false,
  "dry_run": true
}
```

行为：

- `dry_run=true`：只校验，不写入 `meta_plugin_configs`。
- `merge=true`：导入配置和当前已保存配置做深合并后再校验。
- `dry_run=false` 且无错误：保存到当前租户/组织作用域。

## Validation

导入时校验：

- `plugin_id` 必须匹配 `yuantus-cad-material-sync`。
- `schema_version` 目前只支持 `1`。
- `config` 必须是对象。
- `config_hash` 若存在，必须等于 `config` 的稳定 SHA-256。
- 导入配置仍会进入 `preview_profile_config()` 做 profile 诊断。
- 有任一错误时不落库。

## Authorization

- `GET /config/export`：需要已登录用户。
- `POST /config/import`：需要 admin/superuser。

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
32 passed, 1 warning in 1.90s
```

新增覆盖用例：

- `test_config_export_import_bundle_round_trip_and_dry_run`
  - 导出 bundle 包含正确 `plugin_id`、`schema_version` 和 `config_hash`。
  - `dry_run=true` 不落库。
  - 正式导入会写入 `meta_plugin_configs`。
- `test_config_import_rejects_tampered_bundle_and_requires_admin`
  - 篡改 `config_hash` 时返回 `config_hash_mismatch` 且不落库。
  - 非 admin 导入返回 403。

补充编译检查：

```bash
PYTHONPYCACHEPREFIX=.pytest_cache/pycache python3 -m py_compile plugins/yuantus-cad-material-sync/main.py src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py
```

结果：无输出，表示语法编译通过。

插件运行时 smoke：

```bash
PYTHONPATH=src YUANTUS_PLUGINS_ENABLED=yuantus-cad-material-sync python3 -c "from fastapi import FastAPI; from yuantus.plugin_manager.runtime import load_plugins; app=FastAPI(); manager=load_plugins(app); print(manager.get_plugin_stats() if manager else None); print(sorted(getattr(route, 'path', '') for route in app.routes if 'cad-material-sync' in getattr(route, 'path', '')))"
```

结果：`yuantus-cad-material-sync` active，13 条 `/api/v1/plugins/cad-material-sync/*` 路由正常挂载，包含 `/config/export` 和 `/config/import`。

相关 CAD/插件回归：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/api/tests/test_plugin_runtime_security.py src/yuantus/meta_engine/tests/test_plugin_bom_compare.py src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py src/yuantus/meta_engine/tests/test_cad_properties_router.py src/yuantus/meta_engine/tests/test_cad_sync_template_router.py src/yuantus/meta_engine/tests/test_cad_import_service.py src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py -q
```

结果：

```text
103 passed, 1 skipped, 1 warning in 2.35s
```

## Remaining Boundary

导入/导出 API 已完成。后续前端管理页需要提供导出下载、导入上传、dry-run 结果展示和正式导入确认流程。
