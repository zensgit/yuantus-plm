# CAD Material Diff Confirm Package Design And Verification

## Goal

把已有 CAD 字段差异预览推进到可确认写回的协议闭环：服务端返回只包含待写回字段的 `write_cad_fields`，Workbench 显示差异确认面板并生成确认后的写回包 JSON。真实 DWG/DXF 修改仍由本地 CAD adapter 执行。

## Design

`POST /api/v1/plugins/cad-material-sync/diff/preview` 继续返回完整 `target_cad_fields` 和字段级 `diffs`，并新增：

- `write_cad_fields`：只包含 `added`、`changed`、`cleared` 字段。
- `requires_confirmation`：当 `write_cad_fields` 非空时为 `true`。

示例：

```json
{
  "summary": {
    "added": 1,
    "changed": 1,
    "cleared": 0,
    "unchanged": 4
  },
  "write_cad_fields": {
    "厚": 12,
    "规格": "1200*600*12"
  },
  "requires_confirmation": true
}
```

Workbench `CAD Write Confirmation` 面板会在 Preview diff 成功后：

- 显示待写回字段数量和确认状态。
- 展示 changed/added/cleared 的字段、当前值和目标值。
- 将 `write_cad_fields` 写入 `Confirmed write-back package JSON`。
- `Confirm write package` 只确认包已准备好，不直接修改 CAD 文件。

新增 contract fixture：

- `docs/samples/cad_material_diff_confirm_fixture.json`
- `scripts/verify_cad_material_diff_confirm_contract.py`

fixture 固定 3 个客户端接入场景：新增/变更、清空、无变化。Yuantus AutoCAD/SolidWorks 客户端可用它验证 `write_cad_fields`、`requires_confirmation` 和字段状态解析。

## Boundary

后续 AutoCAD 客户端切片已在 `clients/autocad-material-sync` 接入 `/diff/preview` 和本地 WPF 差异确认窗。真实 DLL 编译、窗口渲染、用户确认和 DWG 写回仍需要 Windows + AutoCAD 2018 环境完成。

## Files

- `plugins/yuantus-cad-material-sync/main.py`
- `src/yuantus/web/workbench.html`
- `src/yuantus/api/tests/test_workbench_router.py`
- `src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py`
- `playwright/tests/cad_material_workbench_ui.spec.js`
- `docs/samples/cad_material_diff_confirm_fixture.json`
- `scripts/verify_cad_material_diff_confirm_contract.py`
- `docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md`
- `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_DIFF_PREVIEW_API_20260506.md`
- `docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_PLUGIN_20260506.md`

## Verification

插件目标测试：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py -q
```

结果：

```text
41 passed, 1 warning in 2.45s
```

Contract fixture 验证：

```bash
PYTHONPATH=src python3 scripts/verify_cad_material_diff_confirm_contract.py
```

结果：

```text
OK: CAD material diff confirm contract fixture passed (3 cases)
```

Workbench 渲染测试：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/api/tests/test_workbench_router.py -q
```

结果：

```text
5 passed, 1 warning in 3.02s
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

- changed/added/cleared 字段进入 `write_cad_fields`。
- unchanged 字段不进入写回包。
- 全部 unchanged 时 `requires_confirmation=false`。
- contract fixture 固定 3 个客户端消费场景。
- Workbench 渲染确认面板和确认按钮。
- 浏览器中可确认手动写回包 JSON。

## Remaining Work

- AutoCAD 客户端已接入 `/diff/preview` 并新增本地差异确认窗；仍需 Windows + AutoCAD 2018 真实 smoke。
- SolidWorks 明细表/属性表字段读取与确认 UI。
- Windows + AutoCAD 2018 编译 DLL 并做真实 DWG 手工 smoke，AutoCAD 2024 做高版本回归；2018 兼容性计划见 `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_AUTOCAD2018_COMPATIBILITY_20260506.md`。
