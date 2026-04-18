# P2 PR219 Mainline Replay Audit

日期：2026-04-18
目标 PR：`#219 feat(plm): P1 main chain + P2 approval chain + P2-3.1 dashboard`

## 目标

确认当前 `main` 是否还应该继续沿用 `PR #219` 这条历史混合分支推进，以及如果不应该，下一步该如何从当前主线继续拆分真实开发工作。

## 当前基线

- 本地主仓库：`main@b42991d`
- GitHub 上 `PR #219` head：`origin/feature/claude-c43-cutted-parts-throughput@df5ab0f`
- 本地同名分支：`feature/claude-c43-cutted-parts-throughput@ee0076b`

说明：

- `PR #219` 指向的是远端历史 head `df5ab0f`
- 本地同名分支已经不是同一个 head，不能再把它当成 `PR #219` 的真实来源

## 实际审计

### 1. `PR #219` 仍然是脏混合分支

对比：

```bash
git fetch origin feature/claude-c43-cutted-parts-throughput
git rev-list --left-right --count main...origin/feature/claude-c43-cutted-parts-throughput
git diff --name-only main...origin/feature/claude-c43-cutted-parts-throughput
```

观察结果：

- `main...origin/feature/claude-c43-cutted-parts-throughput = 200 / 7`
- 当前 `main` 比这条历史分支多 `200` 个提交
- 这条历史分支相对当前 `main` 仍残留 `7` 个独有提交
- 残余 diff 仍覆盖 `52` 个文件

这说明：

- `PR #219` 已明显陈旧
- 它不是“只差一点就能合”的分支
- 继续直接审/合这条 PR 会把多个域重新缠在一起

### 2. 残余 diff 仍是多域混合

按文件域拆分，当前残余 `52` 文件大致分布为：

- repo docs：`24`
- AML docs：`4`
- meta-engine tests：`9`
- meta-engine services：`3`
- meta-engine web runtime：`3`
- version runtime：`3`
- Playwright：`2`
- 其它：`api_tests=1`、`tasks=1`、`cli=1`、`web_ui=1`

关键残余文件簇包括：

### P2 / ECO approval chain

- `src/yuantus/meta_engine/services/eco_service.py`
- `src/yuantus/meta_engine/web/eco_router.py`
- `src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py`
- `src/yuantus/meta_engine/tests/test_eco_approval_escalation.py`
- `src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py`
- `src/yuantus/meta_engine/tests/test_eco_approval_dashboard_export.py`
- `src/yuantus/meta_engine/tests/test_eco_approval_audit.py`
- `docs/DEV_AND_VERIFICATION_P2_*`
- `docs/P2_2_APPROVAL_AUTO_ASSIGN_ESCALATION.md`
- `docs/P2_OPS_RUNBOOK.md`

### P1 / CAD / version / queue

- `src/yuantus/meta_engine/services/checkin_service.py`
- `src/yuantus/meta_engine/services/job_worker.py`
- `src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py`
- `src/yuantus/meta_engine/version/file_service.py`
- `src/yuantus/meta_engine/version/models.py`
- `src/yuantus/meta_engine/version/service.py`
- `src/yuantus/meta_engine/tests/test_cad_checkin_transaction.py`
- `src/yuantus/meta_engine/tests/test_file_conversion_router_job_queue.py`
- `src/yuantus/meta_engine/tests/test_version_file_checkout_service.py`

### AML docs

- `docs/development/aml-metadata-doc-index-20260411.md`
- `docs/development/aml-metadata-federation-design-verification-20260411.md`
- `docs/development/aml-metadata-pact-design-and-verification-20260411.md`
- `docs/development/aml-metadata-session-handoff-20260411.md`

### `plm_workspace` / UI / Playwright

- `playwright/tests/plm_workspace_document_handoff.spec.js`
- `playwright/tests/README_plm_workspace.md`
- `src/yuantus/api/tests/test_plm_workspace_router.py`
- `src/yuantus/meta_engine/web/file_router.py`
- `src/yuantus/meta_engine/web/version_router.py`
- `src/yuantus/web/plm_workspace.html`
- `src/yuantus/cli.py`

## 已被更干净链路替代的范围

`PR #219` 里最关键的 `P2 / ECO` 主链，其实已经被更窄、更可审的链路替代：

- `PR #220`
  - `feat(eco): replay p2 approval chain on clean main`
  - merge commit: `0b0b3f1`
- `PR #222`
  - `fix(eco): restore parallel flow hook and diagnostics contracts`
  - merge commit: `20151a4`
- `PR #230`
  - `docs: capture P2 observation workflow and remote regression runbook`
  - merge commit: `8ea2e03`
- `PR #232`
  - `docs: record PR #222 remote observation rerun`
  - merge commit: `96e141b`
- `PR #233`
  - `docs: record eco parallel flow hook closeout`
  - merge commit: `b42991d`

这条替代链意味着：

- `P2 approval chain` 主体不应再通过 `PR #219` 回灌
- `#219` 现在更像一条历史混合分支引用，而不是可直接合并的主线候选

## 结论

当前不建议继续直接推进 `PR #219`。

推荐动作是：

1. 关闭 `PR #219`
2. 把其余仍有价值但尚未 clean replay 的残余内容，按域从当前 `main` 单独重放

最小拆分建议：

- `P1 main chain / CAD / version / queue`
- `plm_workspace` UI / Playwright / router
- AML metadata docs

不要再从 `origin/feature/claude-c43-cutted-parts-throughput` 直接开工，也不要继续试图把 `#219` 修成一个可合 PR。

## 关联文档

- `docs/DEV_AND_VERIFICATION_P2_APPROVAL_CHAIN_CLEAN_REPLAY_20260416.md`
- `docs/DEV_AND_VERIFICATION_P2_APPROVAL_CHAIN_PR220_CONTRACTS_REMEDIATION_20260416.md`
- `docs/DEV_AND_VERIFICATION_ECO_PARALLEL_FLOW_HOOK_REVIEW_REMEDIATION_20260418.md`
- `docs/DEV_AND_VERIFICATION_P2_REMOTE_OBSERVATION_VALIDATION_20260418.md`
- `docs/DEV_AND_VERIFICATION_ECO_PARALLEL_FLOW_HOOK_CLOSEOUT_20260418.md`
- `docs/DEV_AND_VERIFICATION_MAINLINE_BASELINE_SWITCH_EXECUTION_20260414.md`

## 验证命令

```bash
git -C /Users/chouhua/Downloads/Github/Yuantus fetch origin feature/claude-c43-cutted-parts-throughput
git -C /Users/chouhua/Downloads/Github/Yuantus rev-list --left-right --count main...origin/feature/claude-c43-cutted-parts-throughput
git -C /Users/chouhua/Downloads/Github/Yuantus diff --name-only main...origin/feature/claude-c43-cutted-parts-throughput
git -C /Users/chouhua/Downloads/Github/Yuantus rev-parse --short origin/feature/claude-c43-cutted-parts-throughput
git -C /Users/chouhua/Downloads/Github/Yuantus rev-parse --short feature/claude-c43-cutted-parts-throughput
```
