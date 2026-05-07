# CAD Material Matching Design And Verification

## Goal

补齐 CAD 物料同步中的物料库匹配增强：CAD 字段入站时先按高置信标识匹配已有 PLM Item，再回退到物料类别、材料、规格组合匹配；多匹配时返回候选，不自动创建或覆盖；单匹配但字段冲突时返回冲突，等待用户确认 overwrite。

## Design

服务端插件新增可配置匹配策略：

```python
DEFAULT_MATCH_STRATEGIES = [
    ["item_number"],
    ["drawing_no"],
    ["material_code"],
    ["material_category", "material", "specification"],
    ["material", "specification"],
]
```

匹配规则：

- 每个 strategy 内字段按 AND 查询。
- strategy 之间按优先级顺序执行，命中任一 strategy 后立即返回。
- 单个高置信字段不会被其他字段差异拖累，例如 `item_number` 命中时不再额外要求材料或规格也一致。
- profile 可通过 `matching.strategies` 或 `match_strategies` 覆盖默认策略。
- `load_profiles()` 会在返回 profile 时补默认 `matching`，便于客户端或管理端读取当前策略。

入站同步行为：

- 0 个匹配：按 `create_if_missing` 决定返回 `not_found` 或创建。
- 1 个匹配：进入更新路径；已有值不同且 `overwrite=false` 时返回 `conflict`。
- 多个匹配：返回 `ambiguous_match` 和 `matched_items` 候选列表，不创建、不覆盖。

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
14 passed, 1 warning in 1.01s
```

覆盖用例：

- `item_number` 精确命中已有 Item，即使材料不同也进入冲突路径。
- `material_code` 优先匹配已有 Item，并在 validate 中返回候选。
- 物料类别 + 材料 + 规格组合命中多个 Item 时返回 `ambiguous_match` 候选列表。

## Remaining Boundary

后续管理端可把 `matching.strategies` 暴露为 profile 配置 UI，并支持按企业模板调整优先级，例如把 `material_code` 放在 `item_number` 前，或增加自定义字段组合。
