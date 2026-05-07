# CAD Material Workbench Structured Config Design And Verification

## Goal

在 `/api/v1/workbench` 的 CAD Material 管理区补齐结构化配置生成能力，让管理员不必手写完整 JSON，也可以把字段定义、CAD 字段名、必填、类型、单位、规格模板、匹配键配置写入 profile 草稿。

## Scope

本轮交付的是 Workbench 侧结构化生成器和浏览器 smoke：

- 生成并更新 `config.profiles[profile_id].fields[]`。
- 生成并更新 `config.profiles[profile_id].compose`。
- 生成并更新 `config.profiles[profile_id].matching.strategies`。
- 在 `config.profiles[profile_id].sync_defaults.overwrite` 保存服务端入站同步默认 overwrite 策略。
- 根据 Sample values JSON 对 compose template 做本地实时预览。

服务端入站同步的优先级是：请求显式 `overwrite` 优先；请求省略 `overwrite` 时才读取 profile 的 `sync_defaults.overwrite`；未配置时保持默认非破坏性行为。旧 `ui_defaults.overwrite` 不参与服务端写库。

## Design

### Workbench UI

新增 `Structured Rule Builder` 子面板：

- `Field name`：PLM 属性字段名，例如 `length`。
- `Field label`：字段显示名，例如 `长`。
- `Field type`：`string`、`number`、`integer`、`boolean`。
- `CAD field`：CAD 明细栏/标题栏字段，例如 `长`。
- `Unit` / `Display unit` / `Display precision`：对应 profile 字段单位、显示单位和精度。
- `Required`：生成字段级 `required`。
- `Compose target` / `Compose template`：生成规格字段和模板，例如 `specification = {length}*{width}*{thickness}`。
- `Match fields`：逗号分隔匹配键，例如 `material_category,material,specification`。
- `Sync overwrite default`：保存到 `sync_defaults.overwrite`。

### Config Mutation

Workbench 不直接写数据库。结构化生成器只修改 `cad-material-config` textarea 中的草稿 JSON，后续仍复用既有按钮：

- `Preview draft` 调用 `/plugins/cad-material-sync/config/preview`。
- `Save config` 调用 `/plugins/cad-material-sync/config`。
- `Export bundle` / `Import config` 复用配置包 API。

字段 upsert 以 `field.name` 为主键，避免同一个字段重复追加：

```json
{
  "profiles": {
    "sheet": {
      "profile_id": "sheet",
      "fields": [
        {
          "name": "length",
          "label": "长",
          "type": "number",
          "required": true,
          "cad_key": "长",
          "unit": "mm",
          "display_precision": 0
        }
      ],
      "compose": {
        "target": "specification",
        "template": "{length}*{width}*{thickness}"
      },
      "matching": {
        "strategies": [
          {
            "fields": ["material_category", "material", "specification"]
          }
        ]
      },
      "sync_defaults": {
        "overwrite": true
      }
    }
  }
}
```

### Compatibility

- 配置 shape 使用插件已经支持的 `fields`、`cad_key`、`unit`、`display_unit`、`display_precision`、`compose`、`matching.strategies`。
- 新增 `sync_defaults.overwrite` 参与服务端入站同步默认策略；请求显式 `overwrite` 仍然优先。
- 旧 `ui_defaults.overwrite` 不参与服务端写库，避免 UI 元数据误触发覆盖。
- 不增加数据库 migration。

## Files

- `src/yuantus/web/workbench.html`
- `src/yuantus/api/tests/test_workbench_router.py`
- `playwright/tests/cad_material_workbench_ui.spec.js`
- `docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md`

## Verification

Workbench 渲染和 action wiring：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/api/tests/test_workbench_router.py -q
```

结果：

```text
5 passed, 1 warning in 3.00s
```

Workbench 脚本语法：

```bash
node -e "const fs=require('fs'); const html=fs.readFileSync('src/yuantus/web/workbench.html','utf8'); const m=html.match(/<script>([\s\S]*)<\/script>/); new Function(m[1]); console.log('workbench script syntax ok');"
```

结果：

```text
workbench script syntax ok
```

浏览器 smoke：

```bash
npx playwright test playwright/tests/cad_material_workbench_ui.spec.js
```

结果：

```text
1 passed
```

备注：本机首次运行时缺少 Playwright Chromium，已执行 `npx playwright install chromium` 后复跑通过。

插件与 CAD 相关回归：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/api/tests/test_workbench_router.py src/yuantus/api/tests/test_plugin_runtime_security.py src/yuantus/meta_engine/tests/test_plugin_bom_compare.py src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py src/yuantus/meta_engine/tests/test_cad_properties_router.py src/yuantus/meta_engine/tests/test_cad_sync_template_router.py src/yuantus/meta_engine/tests/test_cad_import_service.py src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py -q
```

结果：

```text
116 passed, 1 skipped, 1 warning in 5.92s
```

编译和 diff 检查：

```bash
PYTHONPYCACHEPREFIX=.pytest_cache/pycache python3 -m py_compile src/yuantus/api/routers/workbench.py src/yuantus/api/tests/test_workbench_router.py plugins/yuantus-cad-material-sync/main.py src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py
git diff --check
```

结果：无输出，表示通过。

## Remaining Work

- SolidWorks 等 CAD 客户端还需要在可视化确认 UI 中暴露最终生效的 overwrite 策略。
- 生产级 profile 表单还可继续扩展条件字段、版本灰度、CAD 别名矩阵的可视化编辑。
