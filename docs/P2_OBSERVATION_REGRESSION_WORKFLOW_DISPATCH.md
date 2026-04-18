# P2 Observation Regression Workflow Dispatch

**目的**：给 P2 observation tooling 一个固定的 GitHub Actions 入口，不再要求操作者只在本地 shell 手工拼接命令。

---

## 1. 入口

workflow 名称：

- `p2-observation-regression`

手工触发：

```bash
gh workflow run p2-observation-regression \
  --field base_url=http://<target-host> \
  --field tenant_id=tenant-1 \
  --field org_id=org-1 \
  --field environment=shared-dev
```

---

## 2. 凭证

workflow 支持两种认证来源，优先级与 shell wrapper 一致：

1. `P2_OBSERVATION_TOKEN`
2. `P2_OBSERVATION_PASSWORD` + dispatch input `username`

推荐 secrets：

- `P2_OBSERVATION_TOKEN`
- `P2_OBSERVATION_PASSWORD`

如果两者都没有，workflow 不会静默退出。它会生成：

- `WORKFLOW_PRECHECK.md`
- `workflow_precheck.json`

然后在最后的 failure gate 明确失败。

如果你有 `gh` 权限，也可以直接配置：

```bash
gh secret set P2_OBSERVATION_PASSWORD --repo zensgit/yuantus-plm
gh secret set P2_OBSERVATION_TOKEN --repo zensgit/yuantus-plm
```

---

## 3. 它会做什么

workflow 内部固定执行：

1. `bash scripts/run_p2_observation_regression.sh`
2. `EVAL_MODE=current-only`
3. 生成 `OBSERVATION_RESULT.md`
4. 生成 `OBSERVATION_EVAL.md`
5. 上传 artifact `p2-observation-regression`

这条入口当前只做 `current-only` 判定，目标是锁住：

- 当前结果目录内部口径自洽
- collect / render / evaluate 工具链在远端环境可重复执行

---

## 4. 可用输入

- `base_url`
- `tenant_id`
- `org_id`
- `username`
- `environment`
- `company_id`
- `eco_type`
- `eco_state`
- `deadline_from`
- `deadline_to`

---

## 5. 产物

artifact `p2-observation-regression` 内至少包含：

- `summary.json`
- `items.json`
- `export.json`
- `export.csv`
- `anomalies.json`
- `OBSERVATION_RESULT.md`
- `OBSERVATION_EVAL.md`

如果 precheck 失败，则至少包含：

- `WORKFLOW_PRECHECK.md`
- `workflow_precheck.json`

---

## 6. 适用边界

- 适合：shared-dev / frozen remote surface 的固定回归入口
- 不适合：本地 seed 演示、需要 baseline diff 的双轮状态迁移验证

如果要做显式 delta 验证，仍然用 shell 模式配合 `BASELINE_DIR` 和 `state-change`。
