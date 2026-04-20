# DEV / Verification - Shared-dev 142 Workflow Success Validation

日期：2026-04-20
仓库基线：`1a199d5`（`Merge pull request #282 from zensgit/scripts/shared-dev-142-workflow-failure-diagnosis-20260420`）

## 目标

把上一轮已经定位清楚的 workflow blocker 真正消掉：

1. 给 GitHub Actions workflow `p2-observation-regression` 配上可用认证 secret
2. 重新执行 shared-dev `142` 的 `workflow-readonly-check`
3. 确认 workflow 路径和 frozen readonly baseline 的 compare/eval 全部真实通过

## 本轮执行

### 1. 配置 repo secret

使用本机已验证可用的 shared-dev `142` 凭证，把 password 写入仓库 secret：

```bash
set -a
source "$HOME/.config/yuantus/p2-shared-dev.env"
set +a
printf '%s' "$PASSWORD" | gh secret set P2_OBSERVATION_PASSWORD -R zensgit/yuantus-plm
gh secret list -R zensgit/yuantus-plm
```

结果：

- `P2_OBSERVATION_PASSWORD` 已存在于 repo secret list
- GitHub 返回时间戳：`2026-04-20T03:05:25Z`

### 2. 重新执行 workflow-readonly-check

执行命令：

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode workflow-readonly-check
```

真实 run：

- GitHub Actions run id: `24646485777`
- workflow 名称：`p2-observation-regression`
- 输出目录：
  - `./tmp/p2-shared-dev-142-workflow-readonly-check-20260420-110538`

## 执行结果

### 1. workflow dispatch：成功

workflow job `p2_observation_regression` 完整通过：

- `Validate auth configuration`
- `Run P2 observation regression`
- `Write observation summary to job summary`
- `Upload P2 observation regression evidence`

说明：

- 之前的 blocker 已确认解除
- workflow 路径不再停在 auth precheck failure

### 2. readonly compare / eval：成功

顶层产物全部生成：

- `./tmp/p2-shared-dev-142-workflow-readonly-check-20260420-110538/workflow-probe/WORKFLOW_DISPATCH_RESULT.md`
- `./tmp/p2-shared-dev-142-workflow-readonly-check-20260420-110538/workflow-probe/workflow_dispatch.json`
- `./tmp/p2-shared-dev-142-workflow-readonly-check-20260420-110538/workflow-probe/artifact`
- `./tmp/p2-shared-dev-142-workflow-readonly-check-20260420-110538/WORKFLOW_READONLY_DIFF.md`
- `./tmp/p2-shared-dev-142-workflow-readonly-check-20260420-110538/WORKFLOW_READONLY_EVAL.md`
- `./tmp/p2-shared-dev-142-workflow-readonly-check-20260420-110538/WORKFLOW_READONLY_CHECK.md`
- `./tmp/p2-shared-dev-142-workflow-readonly-check-20260420-110538.tar.gz`

关键结论：

- `WORKFLOW_READONLY_CHECK.md`
  - `verdict: PASS`
- `WORKFLOW_READONLY_EVAL.md`
  - `verdict: PASS`
  - `checks: 20/20 passed`

### 3. 指标对账：全部稳定

baseline `shared-dev-142-readonly-20260419` 与本次 workflow artifact `workflow-probe-current` 对比：

- summary
  - `pending_count`: `2 -> 2`，`Δ=0`
  - `overdue_count`: `3 -> 3`，`Δ=0`
  - `escalated_count`: `1 -> 1`，`Δ=0`
- counts
  - `items_count`: `5 -> 5`，`Δ=0`
  - `export_json_count`: `5 -> 5`，`Δ=0`
  - `export_csv_rows`: `5 -> 5`，`Δ=0`
- anomalies
  - `total_anomalies`: `2 -> 2`，`Δ=0`
  - `no_candidates`: `0 -> 0`，`Δ=0`
  - `escalated_unresolved`: `1 -> 1`，`Δ=0`
  - `overdue_not_escalated`: `1 -> 1`，`Δ=0`

这说明：

- workflow 采集链与本地 readonly baseline 没有产生口径漂移
- compare/eval 对 shared-dev `142` 当前 frozen 状态判断一致

### 4. 业务面快照

本次 workflow artifact 中的关键业务面与之前 readonly rerun 保持一致：

- `summary.json`
  - `pending_count=2`
  - `overdue_count=3`
  - `escalated_count=1`
- `anomalies.json`
  - `total_anomalies=2`
  - `no_candidates=0`
  - `escalated_unresolved=1`
  - `overdue_not_escalated=1`

## 附带观察

GitHub Actions 本轮出现一条非阻塞 annotation：

- `actions/upload-artifact@v4` 的 Node.js 20 deprecation 提示

当前影响：

- 不影响本轮结果
- 不是 P2 observation regression 的 blocker

## 验证

真实执行：

```bash
gh secret list -R zensgit/yuantus-plm
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode workflow-readonly-check
```

文档契约：

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

结果：

- `3 passed`

## 结论

shared-dev `142` 的 workflow 路径现在已经真实打通：

1. repo secret 已配置
2. GitHub Actions workflow `24646485777` 成功
3. readonly compare/eval 成功
4. frozen baseline 对比 `Δ=0`

到这一步，P2 observation 在 shared-dev `142` 上已经同时具备：

- direct local readonly rerun 路径
- GitHub workflow readonly check 路径

两条路径都已用真实环境跑通。
