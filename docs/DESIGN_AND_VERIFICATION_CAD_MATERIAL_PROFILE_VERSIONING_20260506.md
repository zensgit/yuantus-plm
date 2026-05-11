# CAD Material Profile Versioning And Rollout Design And Verification

## Goal

补齐 CAD 物料 profile 的版本化和灰度发布能力，让同一物料类别可以同时保留旧规则和新规则，并按显式版本、租户/组织/用户灰度或默认版本选择当前生效规则。

这个切片解决以下问题：

- 规格模板、字段、单位或 CAD 字段名变更不能一次性影响所有用户。
- 需要先让指定租户/组织试用新版 profile，再逐步扩大。
- 回滚应只改插件配置，不需要改代码、不需要数据库迁移。

## Design

profile 配置新增版本控制字段：

- `versions`：同一 profile 下的版本候选，支持对象或列表。
- `active_version`：当前 profile 显式生效版本。
- `active_versions`：全局按 profile 指定生效版本，例如 `{"sheet": "v2"}`。
- `default_version`：没有命中灰度时的默认版本。
- `default_versions`：全局默认版本表。
- `rollout` / `gray_release`：版本候选的灰度选择规则。

选择优先级：

1. 显式 `active_version` / `active_versions`。
2. 命中 `rollout` / `gray_release` 的版本。
3. `default_version` / `default_versions`。
4. 不应用版本覆盖，保留基础 profile。

版本启用规则：

- `enabled: false`、`disabled: true`、`status: disabled|retired|archived` 的版本不会被选中。
- 被选中版本会合并到基础 profile 上，旧字段、默认映射和 selector 仍可继承。
- 返回 profile 会包含：
  - `available_versions`
  - `profile_version`

灰度支持：

- `tenant_id` / `tenant_ids`
- `org_id` / `org_ids`
- `user_id` / `user_ids`
- `percent` / `percentage` / `traffic_percent`

百分比灰度使用 `profile_id + version + tenant_id + org_id + user_id` 的稳定 hash 桶，不需要额外存储。

## Examples

显式启用新版：

```json
{
  "profiles": {
    "sheet": {
      "active_version": "v2",
      "versions": {
        "v1": {
          "compose": {"template": "{length}*{width}*{thickness}"}
        },
        "v2": {
          "compose": {"template": "PL{thickness}-{length}x{width}"},
          "cad_mapping": {"specification": "物料规格"}
        }
      }
    }
  }
}
```

租户灰度：

```json
{
  "profiles": {
    "sheet": {
      "default_version": "v1",
      "versions": {
        "v1": {
          "compose": {"template": "STD-{length}*{width}*{thickness}"}
        },
        "v2": {
          "compose": {"template": "PILOT-{thickness}-{length}x{width}"},
          "rollout": {"tenant_ids": ["tenant-pilot"]}
        }
      }
    }
  }
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
21 passed, 1 warning in 1.06s
```

新增覆盖用例：

- `test_profile_version_selects_explicit_active_version`
  - `active_version=v2` 时选择新版模板。
  - 返回 `profile_version=v2` 和 `available_versions=["v1", "v2"]`。
  - 新版 `cad_mapping` 覆盖规格写回字段。
- `test_profile_version_rollout_uses_context_and_default_fallback`
  - 未命中租户灰度时选择 `default_version=v1`。
  - `tenant_id=tenant-pilot` 时选择 rollout 版本 `v2`。
  - 两个版本合成不同规格，验证实际生效规则不同。

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
92 passed, 1 skipped, 1 warning in 1.50s
```

## Remaining Boundary

当前版本选择发生在服务端 profile 加载阶段，适合租户/组织级插件配置灰度。后续如果 CAD 客户端需要在同一请求中预览指定版本，可在 `/compose`、`/validate`、`/sync/*` 请求体增加 `profile_version` 参数，并在 `_get_profile()` 后做请求级版本选择。
