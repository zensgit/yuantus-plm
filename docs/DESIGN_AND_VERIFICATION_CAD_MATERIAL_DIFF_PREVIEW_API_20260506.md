# CAD Material Diff Preview API Design And Verification

## Goal

补齐 CAD 写回前的差异预览后端能力。CAD 客户端在真正写回标题栏、明细栏或属性表前，可以先把当前 CAD 字段和目标字段提交给服务端，得到字段级新增、变更、清空、未变列表，用于确认写回 UI。

这个切片最初只做服务端 API 和可供 Workbench/CAD 客户端确认的写回包，不直接修改 DWG/DXF，也不实现真实 CAD 客户端弹窗。后续 AutoCAD 客户端切片已接入该 API，并新增本地 WPF 差异确认窗；SolidWorks 客户端仍待接入。

## API

新增：

```text
POST /api/v1/plugins/cad-material-sync/diff/preview
```

请求体支持两种模式。

模式 A：由 PLM/源字段生成目标 CAD 字段包：

```json
{
  "profile_id": "sheet",
  "current_cad_fields": {
    "物料类别": "sheet",
    "材料": "Q235B",
    "长": "1200",
    "宽": "600",
    "厚": "",
    "规格": "旧规格"
  },
  "values": {
    "material": "Q235B",
    "length": 1200,
    "width": 600,
    "thickness": 12
  }
}
```

模式 B：调用方直接给目标 CAD 字段包：

```json
{
  "profile_id": "sheet",
  "current_cad_fields": {"备注": "旧备注"},
  "target_cad_fields": {"备注": ""}
}
```

响应体核心字段：

```json
{
  "ok": true,
  "profile_id": "sheet",
  "target_cad_fields": {
    "物料类别": "sheet",
    "材料": "Q235B",
    "长": 1200,
    "宽": 600,
    "厚": 12,
    "规格": "1200*600*12"
  },
  "write_cad_fields": {
    "厚": 12,
    "规格": "1200*600*12"
  },
  "requires_confirmation": true,
  "summary": {
    "added": 1,
    "changed": 1,
    "cleared": 0,
    "unchanged": 4
  },
  "diffs": [
    {
      "cad_key": "规格",
      "property": "specification",
      "current": "旧规格",
      "target": "1200*600*12",
      "status": "changed"
    }
  ]
}
```

## Design Notes

- 目标字段生成复用 `compose_profile()` 和 `cad_field_package()`，因此单位换算、条件字段、字段治理和多 CAD 别名逻辑保持一致。
- 当前 CAD 字段先通过 `cad_fields_to_properties()` 归一，再用当前 profile 重新打包为主 CAD key，避免模板里 `材质`、`Material`、`SW-Material@Part` 等别名导致误判。
- 若只传 `target_cad_fields` 且没有 `values` / `target_properties` / `item_id`，接口把它视为最终目标字段包，不强制要求长宽厚等源字段齐全。
- 字段状态：
  - `added`：当前为空，目标非空。
  - `changed`：当前和目标均非空但不同。
  - `cleared`：当前非空，目标为空。
  - `unchanged`：当前和目标等价。
- 数字和字符串数字按数值等价比较，例如 CAD 里的 `"1200"` 与目标 `1200` 视为未变。
- 响应新增 `write_cad_fields`，只包含 `added`、`changed`、`cleared` 字段，供本地 CAD adapter 在用户确认后写回。
- `requires_confirmation=true` 表示存在待写回字段；若全部 `unchanged`，写回包为空且不需要确认。

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
41 passed, 1 warning in 2.45s
```

新增覆盖用例：

- `test_cad_diff_preview_reports_field_level_changes`
  - 从 profile 和 values 生成目标字段包。
  - 识别 `厚` 为 `added`。
  - 识别 `规格` 从旧规格变为合成规格，状态为 `changed`。
  - 识别 `"1200"` 与 `1200` 数值等价，状态为 `unchanged`。
- `test_cad_diff_preview_can_compare_explicit_target_cad_fields`
  - 只传显式目标 CAD 字段包时，不要求 profile 源字段齐全。
  - 识别目标空值为 `cleared`。
- `test_cad_diff_preview_without_changes_requires_no_confirmation`
  - 全部字段未变时返回空 `write_cad_fields`。
  - `requires_confirmation=false`。

补充编译检查：

```bash
PYTHONPYCACHEPREFIX=.pytest_cache/pycache python3 -m py_compile plugins/yuantus-cad-material-sync/main.py src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py
```

结果：无输出，表示语法编译通过。

插件运行时 smoke：

```bash
PYTHONPATH=src YUANTUS_PLUGINS_ENABLED=yuantus-cad-material-sync python3 -c "from fastapi import FastAPI; from yuantus.plugin_manager.runtime import load_plugins; app=FastAPI(); manager=load_plugins(app); print(manager.get_plugin_stats() if manager else None); print(sorted(getattr(route, 'path', '') for route in app.routes if 'cad-material-sync' in getattr(route, 'path', '')))"
```

结果：`yuantus-cad-material-sync` active，13 个 `/api/v1/plugins/cad-material-sync/*` 路由正常挂载，包含 `/api/v1/plugins/cad-material-sync/diff/preview`。

相关 CAD/插件回归：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/api/tests/test_plugin_runtime_security.py src/yuantus/meta_engine/tests/test_plugin_bom_compare.py src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py src/yuantus/meta_engine/tests/test_cad_properties_router.py src/yuantus/meta_engine/tests/test_cad_sync_template_router.py src/yuantus/meta_engine/tests/test_cad_import_service.py src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py -q
```

结果：

```text
117 passed, 1 skipped, 1 warning in 5.57s
```

## Remaining Boundary

服务端差异预览、Workbench 确认写回包和 AutoCAD 客户端本地差异确认 UI 已完成。仍需要在 Windows + AutoCAD 2018 环境验证 DLL 编译、窗口渲染、确认后 DWG 写回；SolidWorks 客户端仍需另起切片接入该 API。实际 DWG/DXF 写回仍由本地 CAD adapter 执行。
