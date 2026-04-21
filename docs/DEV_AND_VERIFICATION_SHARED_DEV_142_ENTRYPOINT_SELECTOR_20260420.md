# DEV / Verification - Shared-dev 142 Entrypoint Selector

日期：2026-04-20
仓库基线：`a43219e`（`Merge pull request #276 from zensgit/scripts/shared-dev-142-workflow-readonly-check-wrapper-20260419`）

## 目标

把 shared-dev `142` 当前已经固定好的多条入口再收口成一个统一模式选择器，减少操作者记忆脚本名的成本。

本轮不新增运行时能力，只新增一个总入口：

- `scripts/run_p2_shared_dev_142_entrypoint.sh`

## 问题

上一轮之后，`142` 已经有多条固定入口：

1. `run_p2_shared_dev_142_readonly_rerun.sh`
2. `run_p2_shared_dev_142_drift_audit.sh`
3. `run_p2_shared_dev_142_workflow_probe.sh`
4. `run_p2_shared_dev_142_workflow_readonly_check.sh`
5. `print_p2_shared_dev_142_readonly_rerun_commands.sh`
6. `print_p2_shared_dev_142_drift_audit_commands.sh`

这些入口本身已经稳定，但操作者仍然要先记住：

- 哪条是本地 readonly
- 哪条是 workflow current-only
- 哪条是 workflow + readonly compare
- 哪条只是打印命令

这已经不是参数问题，而是模式选择问题。

## 实现

### 1. 新增统一模式选择器

新增：

- `scripts/run_p2_shared_dev_142_entrypoint.sh`

它强制要求：

- `--mode <mode>`

当前支持八个模式：

- `readonly-rerun`
- `drift-audit`
- `drift-investigation`
- `workflow-probe`
- `workflow-readonly-check`
- `print-readonly-commands`
- `print-drift-commands`
- `print-investigation-commands`

内部只做一件事：

- 把模式映射到已有固定脚本

即：

- `readonly-rerun` -> `scripts/run_p2_shared_dev_142_readonly_rerun.sh`
- `drift-audit` -> `scripts/run_p2_shared_dev_142_drift_audit.sh`
- `drift-investigation` -> `scripts/run_p2_shared_dev_142_drift_investigation.sh`
- `workflow-probe` -> `scripts/run_p2_shared_dev_142_workflow_probe.sh`
- `workflow-readonly-check` -> `scripts/run_p2_shared_dev_142_workflow_readonly_check.sh`
- `print-readonly-commands` -> `scripts/print_p2_shared_dev_142_readonly_rerun_commands.sh`
- `print-drift-commands` -> `scripts/print_p2_shared_dev_142_drift_audit_commands.sh`
- `print-investigation-commands` -> `scripts/print_p2_shared_dev_142_drift_investigation_commands.sh`

### 2. 加 `--dry-run`

选择器额外支持：

- `--dry-run`

它会打印：

- `MODE=...`
- `SUMMARY=...`
- `TARGET=...`
- `FORWARDED_ARGS=...`

然后退出，不实际执行目标脚本。

这有两个用途：

1. 操作者先确认自己即将跑哪条链路
2. 测试里可以稳定断言模式映射，而不必真的触发远端或 workflow

### 3. 文档入口改成先看选择器

同步更新：

- `scripts/print_p2_shared_dev_mode_selection.sh`
- `scripts/print_p2_shared_dev_observation_commands.sh`
- `docs/P2_ONE_PAGE_DEV_GUIDE.md`
- `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`
- `docs/P2_OBSERVATION_REGRESSION_WORKFLOW_DISPATCH.md`

现在 shared-dev `142` 的推荐顺序变成：

1. 先看：
   - `bash scripts/run_p2_shared_dev_142_entrypoint.sh --help`
2. 再按目标选模式：
   - `--mode readonly-rerun`
   - `--mode drift-audit`
   - `--mode workflow-probe`
   - `--mode workflow-readonly-check`

低层脚本仍保留，但变成“知道自己要什么时可以直接调用”的次级入口。

## 验证

执行：

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_wrapper.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

以及：

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --help
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode workflow-readonly-check --dry-run -- --eco-type ECR
```

验证点：

- 新 selector 脚本语法和 help 正常
- discoverability / 脚本索引能发现新 selector
- `--dry-run` 行为测试证明四个模式都正确映射到对应脚本，且会显式打印 `DRY_RUN=1`
- guide / handoff / workflow dispatch 文档现在都优先指向 selector，而不是要求操作者记低层脚本名

## 结果

本轮后，shared-dev `142` 的推荐入口已经从“四条脚本并列”收敛为：

1. 总入口：
   - `bash scripts/run_p2_shared_dev_142_entrypoint.sh --help`
2. 执行：
   - `bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode <mode>`

真正需要记忆的只有模式，不再需要先记忆具体脚本名。
