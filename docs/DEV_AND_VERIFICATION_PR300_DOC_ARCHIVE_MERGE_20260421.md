# DEV_AND_VERIFICATION_PR300_DOC_ARCHIVE_MERGE_20260421

## 1. 目标

闭环上一轮「PR #288 审阅归档 + Line A 任务书 + 本会话工作记录」6 份 MD 的主仓库落盘流程——把用户在另一终端（Codex）已经推送到远端的 doc-only PR #300 走完 review、merge、local sync、contract test 回绿。

## 2. 输入状态（本轮开始时）

- local `main`：`2d24c0d`（`feat(ops): gate shared-dev 142 readonly refreeze (#299)`）
- origin/`main`：已前进到 `5160c52`（`feat(ops): preview shared-dev 142 stable readonly candidate (#301)`）
- PR #300：已由用户（Codex）创建，OPEN 状态，分支 `docs/pr288-review-archive-20260420`
- 我手头本会话尚未 push 的 MD：已经全部在 Codex 的 PR #300 提交面上，不再需要我单独再开 PR

## 3. 执行步骤

### 3.1 先退出多余分支

发现我在上一轮尾段创建的 `docs/post-pr288-sync-20260420` 分支，与 Codex 的 `docs/pr288-review-archive-20260420` 指向相同 commit `91ab0e5`，内容完全重复。

动作：

```bash
git checkout main
git branch -D docs/post-pr288-sync-20260420
```

Deleted branch `docs/post-pr288-sync-20260420` (was `91ab0e5`)，两条 commit（`aa5e2dd`、`91ab0e5`）仍留在 Codex 的分支里，并已进 PR #300。无信息丢失。

### 3.2 同步 origin/main

```bash
git pull --ff-only
```

Fast-forward 1 commit（PR #301 `5160c52`），无冲突，no untracked override。

### 3.3 PR #300 审阅

通过 `gh pr view 300 --json ...` 核对：

| 项 | 值 |
|---|---|
| state | OPEN |
| base / head | `main` / `docs/pr288-review-archive-20260420` |
| mergeStateStatus | CLEAN |
| mergeable | MERGEABLE |
| isDraft | false |
| commits | 2（`aa5e2dd`、`91ab0e5`） |
| files | 8（全部在 `docs/` 下） |
| additions | 1392 |
| deletions | 0 |
| check summary | 3 SUCCESS + 5 SKIPPED，0 failure |

独立核查：

- `gh pr diff 300 --name-only | grep -vE "^docs/|^\.github/"` 结果为空 → 确认纯文档
- 本地 pre-merge 跑一次 3 份 contract test 预演 → `3 passed in 0.02s`

### 3.4 Merge

采用 squash merge 把 2 份 commit 压成一条主干 doc commit，并同时清理远端分支：

```bash
gh pr merge 300 --squash --delete-branch
```

### 3.5 Post-merge 同步 + 验证

```bash
git pull --ff-only
```

local main 前进到 `bda1c47`（`docs: archive PR288 review and planning notes (#300)`）。

最终 contract test（已 ff 到最新 main 且 6 份归档 MD 已入 docs/）：

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

结果：`3 passed in 0.02s`

## 4. 最终产物

| 项 | 值 |
|---|---|
| PR #300 状态 | MERGED |
| PR #300 merge commit | `bda1c470dcfa0fdd76f563c9a4fec5114d57f169` |
| merged at | 2026-04-21T00:09:39Z |
| PR URL | https://github.com/zensgit/yuantus-plm/pull/300 |
| local main HEAD | `bda1c47` |
| origin/main HEAD | `bda1c47` |
| 合并进 main 的文档数量 | 7 份 MD + 1 处索引修改 |

### 4.1 合并进 main 的 7 份 MD

1. `docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260420.md`
2. `docs/DEVELOPMENT_CLAUDE_TASK_AUTO_NUMBERING_LATEST_RELEASE_GUARD_20260420.md`
3. `docs/DEV_AND_VERIFICATION_CLAUDE_TASK_AUTO_NUMBERING_LATEST_RELEASE_GUARD_20260420.md`
4. `docs/DEV_AND_VERIFICATION_PR288_TARGETED_CODE_REVIEW_20260420.md`
5. `docs/DEV_AND_VERIFICATION_PR294_PR288_REMEDIATION_REREVIEW_20260420.md`
6. `docs/DEV_AND_VERIFICATION_MAIN_REPO_POST_PR288_SYNC_20260420.md`
7. `docs/DEV_AND_VERIFICATION_PR288_REVIEW_ARCHIVE_PUSH_AND_PR_20260420.md`

## 5. 本轮未做的事

- ❌ **未** 触碰 PR #294（仍 OPEN）的分支或 merge 时机
- ❌ **未** 修改任何 `docs/` 以外的代码
- ❌ **未** 启动 Claude Code CLI 执行下一条真实代码线（见 §7）
- ❌ **未** 把本 MD 自己提交/ push——由用户决定挂在下一条 bounded increment 的 PR 里，或单独再开一个极小的 doc cleanup PR

## 6. 本 MD 自身的索引状态

本 MD（`DEV_AND_VERIFICATION_PR300_DOC_ARCHIVE_MERGE_20260421.md`）在写盘时尚未进 `DELIVERY_DOC_INDEX.md`。contract test 会在包含本 MD 的下一条 PR 里要求补进索引。

## 7. 悬而未决：下一条真实代码线的歧义

用户指令末尾是：

> 让 Claude 按 `docs/DEVELOPMENT_CLAUDE_TASK_AUTO_NUMBERING_LATEST_RELEASE_GUARD_20260420.md` 开始下一条真实代码线

本 MD 记录当前的观察和建议以备决策，但**不**自动启动 Claude CLI。

### 7.1 现状观察

- 上述任务书 **已经对应一个实现 PR**：**PR #294**（分支 `feature/auto-numbering-latest-released-guard-20260420`，状态 OPEN，9 checks 7 SUCCESS + 2 SKIPPED，我在上一轮已做过复审并判定「可合」）
- PR #294 的提交文件：
  - `docs/DEV_AND_VERIFICATION_AUTO_NUMBERING_LATEST_RELEASED_GUARD_20260420.md`
  - `docs/DEV_AND_VERIFICATION_AUTO_NUMBERING_LATEST_RELEASED_GUARD_REVIEW_REMEDIATION_20260420.md`
  - `docs/DELIVERY_DOC_INDEX.md`（+2 项）
  - 以及 `src/yuantus/meta_engine/operations/add_op.py` / `update_op.py`、`services/numbering_service.py`、`latest_released_guard.py`、`web/router.py`、相关 test 文件
- 若现在再跑 Claude CLI 依照**同一份**任务书执行，会产生**重复实现**，且大概率与 PR #294 在文件层面冲突

### 7.2 三个合理解读

| 解读 | 含义 | 风险 | 建议 |
|---|---|---|---|
| A：合并 PR #294 | 用户把「下一条真实代码线」理解为「让已有实现落地」 | 低。已独立复审过 | ✅ 推荐优先执行 |
| B：启动 Claude CLI 重新实现 | 用户可能未意识到 PR #294 已经做完了 | 高：重复工作 + 潜在冲突 | ⚠️ 执行前先澄清 |
| C：按任务书的 bounded-increment 纪律启动**下一个**增量 | 例如「Suspended 生命周期态」或「require_admin 去重」 | 中：需要先识别 next scope | 🟡 需要 bounded-increment 选题 |

### 7.3 建议

1. **先合 PR #294**——实现一条代码线闭环（gap 分析 → 任务书 → 实现 → 复审 → 合并）
2. 合完 PR #294 后，再决定「下一条真实代码线」是什么。现成的 bounded increment 候选（全部来自我之前的 gap 分析与复审）：
   - **a.** F4 empty-string tenant_id 输入卫生 hardening（Codex 提出，3 行代码 + 参数化测试）
   - **b.** numbering floor 的 O(N) 扫表下推到 DB（优先级低）
   - **c.** `require_admin` 4 份拷贝去重（纯重构，低风险）
   - **d.** gap 分析 §一.3：Suspended 生命周期态（对标 Odoo `plm_suspended`）——需要新的任务书
3. **启动任何新 Claude CLI 代码实现任务前**，用本 MD §7.2 的框架先做一次澄清

## 8. 下一步（等用户决定）

- 若选 A：`gh pr merge 294 --squash --delete-branch`（同样的 merge 语义、带 follow-up 清理）
- 若选 B：先说明为何要重做（可能的理由：worktree → main 清洁重建）
- 若选 C：指定 a/b/c/d 或另一个候选，我再写 bounded-increment 任务书

## 9. Reviewer / 执行者

本轮执行由本会话的 Claude 助手完成：

- 审阅 + 合并 PR #300（doc-only，已授权）
- 同步 local main
- 跑 contract test
- 写本 MD 作为执行记录
- **未** 启动 Claude Code CLI 任何代码实现任务，保留给用户决策
