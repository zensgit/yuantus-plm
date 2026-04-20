# DEV / Verification - Shared-dev 142 Real Execution Validation

日期：2026-04-20
仓库基线：`9ee2b69`（`docs: expose P2 first-run checklist from README runbooks (#281)`）

## 目标

对已经收口完成的 shared-dev `142` operator 入口做一次真实执行验证，不再只停留在 dry-run 或文档层。

本轮实际执行了两条链：

1. `workflow-readonly-check`
2. `readonly-rerun`

## 执行结果

### 1. workflow-readonly-check：失败，但根因已被本地 wrapper 明确 surfaced

执行命令：

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode workflow-readonly-check
```

真实 run：

- GitHub Actions run id: `24644935616`
- 输出目录：
  - `./tmp/p2-shared-dev-142-workflow-readonly-check-20260420-095938`

workflow 真实 blocker：

- `p2-observation-regression` 在 workflow auth precheck 阶段失败
- artifact 里的 `workflow_precheck.json` 明确给出：
  - `reason: missing authentication secret`
  - `required: P2_OBSERVATION_TOKEN, P2_OBSERVATION_PASSWORD`

本轮修复后，本地 wrapper 已经能直接给出明确失败原因，而不是只报 generic `conclusion=failure`。

实际产物：

- `./tmp/p2-shared-dev-142-workflow-readonly-check-20260420-095938/workflow-probe/WORKFLOW_DISPATCH_RESULT.md`
- `./tmp/p2-shared-dev-142-workflow-readonly-check-20260420-095938/workflow-probe/workflow_dispatch.json`
- `./tmp/p2-shared-dev-142-workflow-readonly-check-20260420-095938/workflow-probe/artifact/WORKFLOW_PRECHECK.md`
- `./tmp/p2-shared-dev-142-workflow-readonly-check-20260420-095938/workflow-probe/artifact/workflow_precheck.json`
- `./tmp/p2-shared-dev-142-workflow-readonly-check-20260420-095938/WORKFLOW_READONLY_CHECK.md`

当前结论：

- workflow 路径没有业务面失败证据
- 当前 blocker 是仓库侧缺少 `P2_OBSERVATION_TOKEN` 或 `P2_OBSERVATION_PASSWORD` secret

### 2. readonly-rerun：通过

执行命令：

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode readonly-rerun
```

输出目录：

- precheck:
  - `./tmp/p2-shared-dev-observation-142-readonly-rerun-20260420-095641-precheck`
- main:
  - `./tmp/p2-shared-dev-observation-142-readonly-rerun-20260420-095641`
- archive:
  - `./tmp/p2-shared-dev-observation-142-readonly-rerun-20260420-095641.tar.gz`

关键结果：

- precheck:
  - `login_http_status=200`
  - `summary_http_status=200`
- summary:
  - `pending_count=2`
  - `overdue_count=3`
  - `escalated_count=1`
- counts:
  - `items_count=5`
  - `export_json_count=5`
  - `export_csv_rows=5`
- anomalies:
  - `total_anomalies=2`
  - `no_candidates=0`
  - `escalated_unresolved=1`
  - `overdue_not_escalated=1`
- diff:
  - baseline vs current 全部 `Δ=0`
  - `items/export-json/export-csv` 一致
- eval:
  - `verdict: PASS`
  - `checks: 20/20 passed`

当前结论：

- shared-dev `142` 的 direct local readonly rerun 真实通过
- official frozen baseline 与当前 rerun 保持一致

## 本轮脚本修复

### 1. `scripts/run_p2_observation_regression_workflow.sh`

新增对 artifact 中 `workflow_precheck.json` 的读取：

- 当 workflow run 失败且 artifact 已下载时
- 如果存在 `workflow_precheck.json`
- 本地 failure reason 会直接展开成：
  - `missing authentication secret`
  - `required: P2_OBSERVATION_TOKEN, P2_OBSERVATION_PASSWORD`

### 2. `scripts/run_p2_shared_dev_142_workflow_readonly_check.sh`

新增 failure summary 收口：

- 当 workflow probe 失败时
- 或 probe 成功但后续 `compare/evaluate` 失败时
- 都会写出顶层 `WORKFLOW_READONLY_CHECK.md`
- 明确记录：
  - `status: failure`
  - 失败原因
  - `workflow_dispatch_result` 路径
  - `diff/eval` 是否已生成
  - `diff_log/eval_log` 路径
  - 下一步是补 `P2_OBSERVATION_TOKEN` 或 `P2_OBSERVATION_PASSWORD`，或直接检查 compare/eval log

### 3. `.github/workflows/ci.yml`

本轮 PR 在远端 `contracts` gate 暴露出一个现存仓库级 drift：

- `test_ci_contracts_mainline_baseline_switch_helper.py` 已存在
- 但 `contracts` job 的 pytest 清单漏列该文件

因此本轮顺手补齐了 `ci.yml` 的 contracts 测试列表，避免 PR 因无关 gate 缺口卡住。

## 验证

自动化：

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_wrapper.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

结果：

- `28 passed`

真实执行：

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode workflow-readonly-check
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode readonly-rerun
```

结果：

- workflow 路径：失败，但 blocker 已明确定位到 repo secret 缺失
- readonly 路径：通过，`PASS 20/20`

## 结论

这轮真实执行验证给出的是一个分叉结论：

- shared-dev `142` 本身的 readonly 观察面是可用的，local rerun 真实通过
- workflow 路径当前不可用，但 blocker 不是观察面指标回归，而是 GitHub Actions 缺少 `P2_OBSERVATION_TOKEN` / `P2_OBSERVATION_PASSWORD`

因此当前最合理的下一步是：

1. 给 `p2-observation-regression` 配上所需 secret
2. 重新执行：
   - `bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode workflow-readonly-check`
3. 预期届时应能生成：
   - `WORKFLOW_READONLY_DIFF.md`
   - `WORKFLOW_READONLY_EVAL.md`
   - `WORKFLOW_READONLY_CHECK.md`
