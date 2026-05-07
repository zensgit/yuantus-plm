# CAD Material Sync Default Overwrite Design And Verification

## Goal

补齐 CAD Material profile 级默认 overwrite 策略，让管理员可以在 profile 配置中声明入站同步默认覆盖行为，同时保留请求级显式控制和非破坏性默认值。

## Design

新增 profile 配置：

```json
{
  "profiles": {
    "sheet": {
      "sync_defaults": {
        "overwrite": true
      }
    }
  }
}
```

入站同步优先级：

1. 请求显式传 `overwrite=true`：允许覆盖已有 PLM 字段。
2. 请求显式传 `overwrite=false`：禁止覆盖，即使 profile 配置了默认覆盖。
3. 请求省略 `overwrite`：读取 `profile.sync_defaults.overwrite`。
4. 未配置 `sync_defaults.overwrite`：保持默认非破坏性行为，只填空字段，冲突返回 `conflict`。

旧 `ui_defaults.overwrite` 不参与服务端写库。它只能作为 UI 元数据，不能触发服务端覆盖，避免历史配置或纯界面状态意外改变 PLM 数据。

当 profile 默认覆盖被应用时，响应 `warnings` 增加：

```text
profile_default_overwrite_applied:sync_defaults.overwrite
```

配置值支持布尔值和常见布尔字符串；无法解析时默认关闭，并返回 warning：

```text
profile:<profile_id>: sync_defaults.overwrite must be boolean
```

## Files

- `plugins/yuantus-cad-material-sync/main.py`
- `src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py`
- `src/yuantus/web/workbench.html`
- `playwright/tests/cad_material_workbench_ui.spec.js`
- `docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md`
- `docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_PLUGIN_20260506.md`
- `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_WORKBENCH_STRUCTURED_CONFIG_20260506.md`

## Verification

插件目标测试：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py -q
```

结果：

```text
39 passed, 1 warning in 2.46s
```

Workbench 渲染测试：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/api/tests/test_workbench_router.py -q
```

结果：

```text
5 passed, 1 warning in 2.99s
```

Workbench JS 语法：

```bash
node -e "const fs=require('fs'); const html=fs.readFileSync('src/yuantus/web/workbench.html','utf8'); const m=html.match(/<script>([\s\S]*)<\/script>/); new Function(m[1]); console.log('workbench script syntax ok');"
```

结果：

```text
workbench script syntax ok
```

Workbench 浏览器 smoke：

```bash
npx playwright test playwright/tests/cad_material_workbench_ui.spec.js
```

结果：

```text
1 passed
```

覆盖点：

- `sync_defaults.overwrite=true` 且请求省略 `overwrite` 时允许更新已有字段。
- 请求显式 `overwrite=false` 优先于 profile 默认，返回 `conflict`，DB 不变。
- 仅配置 `ui_defaults.overwrite=true` 不影响服务端写库，仍返回 `conflict`。
- 非 dry-run 冲突路径不会更新已有 Item。
- conflict payload 保留 `field/current/incoming` 明细。

## Remaining Work

- CAD 客户端确认 UI 需要展示最终生效 overwrite 策略，尤其是 profile 默认覆盖被应用时。
- 真实 Windows + AutoCAD 2018 手工 smoke 仍需在对应环境优先执行；AutoCAD 2024 作为高版本回归。
