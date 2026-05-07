# CAD Material Workbench UI Design And Verification

## Goal

把 `cad-material-sync` 的管理端能力接入现有 `/api/v1/workbench`，让管理员不再只能通过 curl 调 profile 配置 API。

这个切片聚焦最小可用管理面：

- 查看物料 profile 列表。
- 读取当前租户/组织配置。
- 编辑 JSON 草稿并实时预览配置诊断、规格合成和 CAD 字段包。
- 保存/删除配置。
- 预览当前 CAD 字段与目标字段包差异。
- 导出/导入配置 bundle。

## Design

Workbench 不新增前端框架，也不新增新路由。它复用现有静态 HTML 管理台：

- 页面入口：`GET /api/v1/workbench`
- 页面文件：`src/yuantus/web/workbench.html`
- 请求封装：现有 `sendRequest()`，自动携带 API base、tenant header、org header 和 bearer token。

新增 Workbench 分区：

- 左侧导航新增 `CAD Material`。
- 主区新增 `CAD Material Profiles`。
- 表单包含 `profile_id`、`cad_system`、sample values、config JSON、current/target CAD fields 和 import bundle。
- 操作按钮统一走 `data-action` 与 `handleAction()` 分发。

接入的插件 API：

- `GET /plugins/cad-material-sync/profiles`
- `GET /plugins/cad-material-sync/config`
- `POST /plugins/cad-material-sync/compose`
- `POST /plugins/cad-material-sync/config/preview`
- `PUT /plugins/cad-material-sync/config`
- `DELETE /plugins/cad-material-sync/config`
- `POST /plugins/cad-material-sync/diff/preview`
- `POST /plugins/cad-material-sync/sync/outbound`
- `GET /plugins/cad-material-sync/config/export`
- `POST /plugins/cad-material-sync/config/import`

交互行为：

- `Get config` 成功后把 `payload.config` 回填到 Config JSON。
- `Preview draft` 成功后把 `preview.cad_fields` 回填到 Target CAD fields。
- `Compose CAD fields` 和 `Outbound fields` 成功后把 `cad_fields` 回填到 Target CAD fields。
- `Export bundle` 成功后把 `bundle` 回填到 Import bundle JSON。
- 所有请求仍会进入统一 request log、raw response、response summary 和 handoff 面板。

## Files

- `src/yuantus/web/workbench.html`
- `src/yuantus/api/tests/test_workbench_router.py`
- `docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md`
- `docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_PLUGIN_20260506.md`

## Verification

Workbench 入口与 action wiring：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/api/tests/test_workbench_router.py -q
```

结果：

```text
5 passed, 1 warning in 3.04s
```

新增覆盖：

- 页面渲染包含 `CAD Material Profiles`。
- 关键按钮存在：profile list、config preview、diff preview、bundle export。
- 所有 `cad-material-*` 按钮都有对应 `handleAction()` case，防止出现“按钮存在但没接线”。

插件目标测试：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py -q
```

结果：

```text
34 passed, 1 warning in 2.10s
```

Workbench JS 静态语法检查：

```bash
node -e "const fs=require('fs'); const html=fs.readFileSync('src/yuantus/web/workbench.html','utf8'); const m=html.match(/<script>([\s\S]*)<\/script>/); new Function(m[1]); console.log('workbench script syntax ok');"
```

结果：

```text
workbench script syntax ok
```

插件运行时 smoke：

```bash
PYTHONPATH=src YUANTUS_PLUGINS_ENABLED=yuantus-cad-material-sync python3 -c "from fastapi import FastAPI; from yuantus.plugin_manager.runtime import load_plugins; app=FastAPI(); manager=load_plugins(app); print(manager.get_plugin_stats() if manager else None); print(sorted(getattr(route, 'path', '') for route in app.routes if 'cad-material-sync' in getattr(route, 'path', '')))"
```

结果：

```text
{'total': 4, 'by_status': {'discovered': 3, 'active': 1}, 'by_type': {'extension': 4}, 'by_category': {'demo': 1, 'cad': 1, 'files': 1, 'bom': 1}, 'errors': 0}
['/api/v1/plugins/cad-material-sync/compose', '/api/v1/plugins/cad-material-sync/config', '/api/v1/plugins/cad-material-sync/config', '/api/v1/plugins/cad-material-sync/config', '/api/v1/plugins/cad-material-sync/config/export', '/api/v1/plugins/cad-material-sync/config/import', '/api/v1/plugins/cad-material-sync/config/preview', '/api/v1/plugins/cad-material-sync/diff/preview', '/api/v1/plugins/cad-material-sync/profiles', '/api/v1/plugins/cad-material-sync/profiles/{profile_id}', '/api/v1/plugins/cad-material-sync/sync/inbound', '/api/v1/plugins/cad-material-sync/sync/outbound', '/api/v1/plugins/cad-material-sync/validate']
```

相关 CAD/插件/Workbench 回归：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/api/tests/test_workbench_router.py src/yuantus/api/tests/test_plugin_runtime_security.py src/yuantus/meta_engine/tests/test_plugin_bom_compare.py src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py src/yuantus/meta_engine/tests/test_cad_properties_router.py src/yuantus/meta_engine/tests/test_cad_sync_template_router.py src/yuantus/meta_engine/tests/test_cad_import_service.py src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py -q
```

结果：

```text
110 passed, 1 skipped, 1 warning in 4.51s
```

语法编译：

```bash
PYTHONPYCACHEPREFIX=.pytest_cache/pycache python3 -m py_compile src/yuantus/api/routers/workbench.py src/yuantus/api/tests/test_workbench_router.py plugins/yuantus-cad-material-sync/main.py src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py
```

结果：无输出，表示语法编译通过。

## Remaining Boundary

这个切片不是完整结构化表单编辑器。字段定义、CAD 字段名、必填、类型、单位、规格模板和匹配策略目前通过 JSON 配置编辑，后续还需要把这些 JSON 能力拆成更细的表格/表单控件。
