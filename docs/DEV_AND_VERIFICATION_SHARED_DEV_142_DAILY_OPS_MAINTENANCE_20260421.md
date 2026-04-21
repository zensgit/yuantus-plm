# DEV_AND_VERIFICATION_SHARED_DEV_142_DAILY_OPS_MAINTENANCE_20260421

日期：2026-04-21

## 背景

`shared-dev 142` 的 baseline / drift / refreeze 工具链已经收口到维护态。

当前需求不再是继续扩脚本能力，而是补一个最小、稳定、可发现的日常操作入口，避免值班时从：

- first-run
- rerun
- drift-audit
- drift-investigation
- refreeze-readiness / candidate / proposal

这些低层脚本里重新拼决策树。

## 本轮目标

补一层薄的维护态入口，只固定：

1. 先跑 `readonly-rerun`
2. 失败再跑 `drift-audit`
3. 仍需解释再跑 `drift-investigation`

同时把这层入口接到：

- `README.md`
- `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DELIVERY_DOC_INDEX.md`
- discoverability / shell syntax contracts

## 实现

新增：

- `docs/P2_SHARED_DEV_142_DAILY_OPS_CHECKLIST.md`
- `scripts/print_p2_shared_dev_142_daily_ops_commands.sh`

更新：

- `scripts/run_p2_shared_dev_142_entrypoint.sh`
  - 新增 `--mode print-daily-commands`
- `README.md`
- `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DELIVERY_DOC_INDEX.md`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py`

## 设计约束

- 不新增新的“执行型”日常 wrapper，只新增命令打印入口
- 不改变现有 readonly / drift / refreeze 语义
- 不重新设计 `142` selector，只在 selector 上补一个 maintenance-state print mode
- 不把 daily ops 混成 baseline switch / refreeze 入口

## 验证

### Shell syntax

```bash
bash -n scripts/print_p2_shared_dev_142_daily_ops_commands.sh
bash -n scripts/run_p2_shared_dev_142_entrypoint.sh
```

### 定向 contracts

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py \
  src/yuantus/meta_engine/tests/test_readme_runbook_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

### 手工 smoke

```bash
bash scripts/print_p2_shared_dev_142_daily_ops_commands.sh | sed -n '1,120p'
bash scripts/run_p2_shared_dev_142_entrypoint.sh --help
```

## 预期结果

- `README` 和 handoff 能直接把人带到 daily ops 入口
- `entrypoint --help` 能直接暴露 `print-daily-commands`
- scripts/doc indices 与 runbook 排序 contracts 保持绿色

## 结论

本轮后，`shared-dev 142` 维护态的最小操作面已经固定为：

1. `readonly-rerun`
2. `drift-audit`
3. `drift-investigation`

日常值班不再需要从 refreeze / proposal / bootstrap 文档里回忆命令。  
这条线进入维护态后，新增入口已经足够，不应继续扩更多同类脚本。
