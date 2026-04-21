# DEV_AND_VERIFICATION_MAIN_REPO_POST_PR288_SYNC_20260420

## 1. 目标

主仓库 `/Users/chouhua/Downloads/Github/Yuantus/` 在 PR #288 合并后（commit `f001b11`）一直未 `git pull`，导致：

- local HEAD 落后 `origin/main` **16 个 commit**
- 本地工作区存在大量与 `origin/main` 同名的 untracked / modified 文件（PR #288 提交面上的 artifact）
- `docs/DELIVERY_DOC_INDEX.md` 在本地与 `origin/main` 双向分叉

本轮目标：**把主仓库同步到 `origin/main` 最新状态，保留本会话产生的 5 份 local-only MD 与对应索引项**，并确保 3 份 contract test 回绿。**不** commit、**不** push，保留由用户或 Codex 决定何时开 doc-only PR。

## 2. 执行前工作区状态

### 2.1 git 对比

```
remote ahead: 16
local  ahead: 0
```

### 2.2 涉及 `origin/main` 与本地双向差异的文件（共 18 项）

#### Tracked 且本地 Modified 的（11 个）

对比本地 worktree 与 `origin/main`：

| 文件 | 本地 vs origin/main |
|---|---|
| `docs/CAD_CONNECTORS.md` | MATCH |
| `docs/DELIVERY_DOC_INDEX.md` | **DIFFER**（双向分叉，28 diff 行） |
| `docs/DELIVERY_SCRIPTS_INDEX_20260202.md` | DIFFER |
| `src/yuantus/config/__init__.py` | DIFFER |
| `src/yuantus/config/settings.py` | MATCH |
| `src/yuantus/meta_engine/services/plugin_config_service.py` | MATCH |
| `src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py` | DIFFER |
| `src/yuantus/meta_engine/tests/test_cad_capabilities_router.py` | DIFFER |
| `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py` | DIFFER |
| `src/yuantus/meta_engine/web/cad_router.py` | DIFFER |
| `src/yuantus/meta_engine/web/file_router.py` | MATCH |

#### Untracked 且 `origin/main` 上已有（13 个）

| 文件 | 本地 vs origin/main |
|---|---|
| `docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_INDEPENDENT_REVIEW_20260420.md` | MATCH |
| `docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_INDEPENDENT_REVIEW_REMEDIATION_20260420.md` | DIFFER |
| `docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SCOPE_OVERRIDES_20260420.md` | MATCH |
| `docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SCOPE_VERIFIER_20260420.md` | MATCH |
| `docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SCOPE_VERIFIER_LOCAL_SMOKE_20260420.md` | MATCH |
| `docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SELECTION_20260420.md` | MATCH |
| `scripts/verify_cad_backend_profile_scope.sh` | DIFFER |
| `src/yuantus/config/cad_backend_profile.py` | DIFFER |
| `src/yuantus/meta_engine/services/cad_backend_profile_service.py` | MATCH |
| `src/yuantus/meta_engine/tests/test_cad_backend_profile.py` | DIFFER |
| `src/yuantus/meta_engine/tests/test_cad_backend_profile_router.py` | MATCH |
| `src/yuantus/meta_engine/tests/test_cad_backend_profile_service.py` | MATCH |
| `src/yuantus/meta_engine/tests/test_ci_contracts_cad_backend_profile_scope_verifier.py` | DIFFER |

**注**：DIFFER 的几项里，origin/main 是权威版本（PR #288 的最终 hardened 版本 + Codex 后续 commit），本地是中间态。

### 2.3 保留不动的 untracked 项（非冲突）

- `.claude/` — 会话状态
- `local-dev-env/` — 本地 dev fixtures，`origin/main` 不含
- 5 份 local-only MD（本会话产出，origin/main 不含）：
  - `docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260420.md`
  - `docs/DEVELOPMENT_CLAUDE_TASK_AUTO_NUMBERING_LATEST_RELEASE_GUARD_20260420.md`
  - `docs/DEV_AND_VERIFICATION_CLAUDE_TASK_AUTO_NUMBERING_LATEST_RELEASE_GUARD_20260420.md`
  - `docs/DEV_AND_VERIFICATION_PR294_PR288_REMEDIATION_REREVIEW_20260420.md`
  - `docs/DEV_AND_VERIFICATION_PR288_TARGETED_CODE_REVIEW_20260420.md`

## 3. 执行步骤

### 3.1 安全备份

备份路径：`/tmp/yuantus-pre-pull-backup-20260420/`

- 顶层：5 份 local-only MD + `DELIVERY_DOC_INDEX.md`（共 6 份）
- `local-differ/` 子目录：12 份 DIFFER 文件的本地副本（扁平化命名，`/` → `__`）

### 3.2 Tracked Modified 文件回到本地 HEAD

```bash
git checkout HEAD -- docs/CAD_CONNECTORS.md docs/DELIVERY_DOC_INDEX.md \
  docs/DELIVERY_SCRIPTS_INDEX_20260202.md src/yuantus/config/__init__.py \
  src/yuantus/config/settings.py \
  src/yuantus/meta_engine/services/plugin_config_service.py \
  src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py \
  src/yuantus/meta_engine/tests/test_cad_capabilities_router.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/web/cad_router.py \
  src/yuantus/meta_engine/web/file_router.py
```

这一步把 11 个 Modified 文件 reset 到本地 HEAD（即 16 commit 前的状态），让后续 `git pull --ff-only` 可以干净 fast-forward。

### 3.3 删除与 `origin/main` 冲突的 untracked 文件

```bash
rm docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_INDEPENDENT_REVIEW_20260420.md \
   docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_INDEPENDENT_REVIEW_REMEDIATION_20260420.md \
   docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SCOPE_OVERRIDES_20260420.md \
   docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SCOPE_VERIFIER_20260420.md \
   docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SCOPE_VERIFIER_LOCAL_SMOKE_20260420.md \
   docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SELECTION_20260420.md \
   scripts/verify_cad_backend_profile_scope.sh \
   src/yuantus/config/cad_backend_profile.py \
   src/yuantus/meta_engine/services/cad_backend_profile_service.py \
   src/yuantus/meta_engine/tests/test_cad_backend_profile.py \
   src/yuantus/meta_engine/tests/test_cad_backend_profile_router.py \
   src/yuantus/meta_engine/tests/test_cad_backend_profile_service.py \
   src/yuantus/meta_engine/tests/test_ci_contracts_cad_backend_profile_scope_verifier.py
```

共 13 个，都已在 `/tmp/yuantus-pre-pull-backup-20260420/` 中有备份。

### 3.4 Fast-forward pull

```bash
git pull --ff-only origin main
```

结果：fast-forward 成功，`HEAD` 由之前的旧基点前进到 `2d24c0d`（= `origin/main`）。

### 3.5 补回 3 条索引项

PR #288 合并引入了新的 `DELIVERY_DOC_INDEX.md` 权威版本，本会话产生的 5 份 local-only MD 中有 3 份属于 `DEV_AND_VERIFICATION_*.md`，必须登记进索引以让 completeness contract 保持绿。

插入位置（按字母序）：

| 索引项 | 插入位置（上下文） |
|---|---|
| `DEV_AND_VERIFICATION_CLAUDE_TASK_AUTO_NUMBERING_LATEST_RELEASE_GUARD_20260420.md` | 在 `CI_STRICT_GATE_SCHEDULE_20260207` 和 `COMPOSE_IDENTITY_ONLY_...` 之间 |
| `DEV_AND_VERIFICATION_PR288_TARGETED_CODE_REVIEW_20260420.md` | 在 `PR223_DOC_INDEX_COMPLETENESS_REMEDIATION_20260416` 和 `PRODUCT_DETAIL_COCKPIT_FLAGS_20260207` 之间 |
| `DEV_AND_VERIFICATION_PR294_PR288_REMEDIATION_REREVIEW_20260420.md` | 紧接上一条 |

本 MD（`DEV_AND_VERIFICATION_MAIN_REPO_POST_PR288_SYNC_20260420.md`）也需要登记；落盘后会再次补索引。

### 3.6 Contract test 重跑

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

**结果（3.5 步补完索引后）**：`3 passed in 0.02s`

## 4. 执行后工作区状态

```
git status --short:
 M docs/DELIVERY_DOC_INDEX.md
?? .claude/
?? docs/DEVELOPMENT_CLAUDE_TASK_AUTO_NUMBERING_LATEST_RELEASE_GUARD_20260420.md
?? docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260420.md
?? docs/DEV_AND_VERIFICATION_CLAUDE_TASK_AUTO_NUMBERING_LATEST_RELEASE_GUARD_20260420.md
?? docs/DEV_AND_VERIFICATION_MAIN_REPO_POST_PR288_SYNC_20260420.md
?? docs/DEV_AND_VERIFICATION_PR288_TARGETED_CODE_REVIEW_20260420.md
?? docs/DEV_AND_VERIFICATION_PR294_PR288_REMEDIATION_REREVIEW_20260420.md
?? local-dev-env/
```

- HEAD = `origin/main` = `2d24c0d`
- Modified：仅 `docs/DELIVERY_DOC_INDEX.md`（+4 行，4 条新索引项含本 MD）
- Untracked 的 6 份 MD 里，5 份属于 bundle "本会话产出"；第 6 份是本 MD 自身
- `.claude/` 与 `local-dev-env/` 属于机器本地，按约定不提交

## 5. 本轮未做的事

- ❌ **未** `git commit`、未 `git push`——由用户或 Codex 决定是否开 doc-only PR
- ❌ **未** 修改任何 `docs/` 之外的代码
- ❌ **未** 更新 `DELIVERY_SCRIPTS_INDEX_20260202.md` 等非 DEV_AND_VERIFICATION 相关索引
- ❌ **未** 在 PR #294（仍 OPEN）的分支上补任何 commit
- ❌ **未** 删除 `/tmp/yuantus-pre-pull-backup-20260420/`——保留作为回退锚点，直到下一次 commit 完成

## 6. 剩余的 5（+1）份 uncommitted MD

本会话产物，尚未进入任何 PR：

| 文件 | 性质 | 归属建议 |
|---|---|---|
| `docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260420.md` | 主干 gap 分析 | 独立 doc PR 或并入 PR #294 |
| `docs/DEVELOPMENT_CLAUDE_TASK_AUTO_NUMBERING_LATEST_RELEASE_GUARD_20260420.md` | Line A 任务书 | 自然归属 PR #294 |
| `docs/DEV_AND_VERIFICATION_CLAUDE_TASK_AUTO_NUMBERING_LATEST_RELEASE_GUARD_20260420.md` | Line A 任务书收敛记录 | 自然归属 PR #294 |
| `docs/DEV_AND_VERIFICATION_PR288_TARGETED_CODE_REVIEW_20260420.md` | Codex 写的 PR #288 窄范围复审（merge 后归档） | 独立 doc PR |
| `docs/DEV_AND_VERIFICATION_PR294_PR288_REMEDIATION_REREVIEW_20260420.md` | 本会话的跨线复审 | 独立 doc PR |
| `docs/DEV_AND_VERIFICATION_MAIN_REPO_POST_PR288_SYNC_20260420.md` | 本 MD（执行记录） | 独立 doc PR |

**建议**：开一个 **doc-only PR**（例如 `docs/post-pr288-sync-20260420`），把上述 6 份 MD + `DELIVERY_DOC_INDEX.md` 的 4 条索引新增一并提交。理由：

- 6 份 MD 都是文档，无代码 side-effect
- 都属于同一轮工作闭环的文字记录
- 不会干扰 PR #294 的代码审阅 scope

## 7. Follow-up 登记（不阻塞）

### 7.1 F4 `empty-string tenant_id` 输入卫生 hardening

Codex 在 `DEV_AND_VERIFICATION_PR288_TARGETED_CODE_REVIEW_20260420.md` §剩余注意点指出：

> `F4` 当前测试覆盖的是 `tenant_id=None`。如果后续真的担心"空白字符串 tenant_id"这类脏 payload，可再补一条输入卫生 hardening，但这不构成当前 PR 的 blocker。

当前 `cad_pipeline_tasks.py::_cad_backend_profile_resolution` 的校验条件是 `if ctx.tenant_id is None`。如果 job payload 里 `tenant_id=""` 或 `tenant_id="   "`，`ctx.tenant_id` 会被设为空串但不是 None，guard 会穿透，继续走到 env-level profile fallback。

**建议**：独立 follow-up PR，将判定改为：

```python
tenant_id = (ctx.tenant_id or "").strip()
if not tenant_id:
    raise JobFatalError(...)
```

并补一条参数化测试覆盖 `""`、`"   "`、`None` 三种 payload。**不阻塞**任何当前 merge。

### 7.2 numbering floor 的 O(N) 全表扫（Line A）

`services/numbering_service.py::_floor_allocated_value` 每次分配都全表扫同 ItemType 下所有 Item。
大历史库（10⁴+ 条）会出现可观察延迟。
**建议**：下推到 DB 层，例如 `SELECT MAX(CAST(substring(item_number, length(prefix)+1) AS INTEGER))`。
**不阻塞** PR #294 的 merge。

### 7.3 `require_admin` 4 份拷贝去重

四处完全相同：`cad_router.py:77` / `search_router.py:14` / `schema_router.py:18` / `permission_router.py:17`。
**建议**：独立 follow-up PR，统一到 `src/yuantus/security/rbac/dependencies.py::require_admin`。

## 8. 验证

### 8.1 Fast-forward 判定

```
git rev-parse HEAD origin/main
2d24c0d5bbb51ea3cdef19c7bd60509909fa3de3
2d24c0d5bbb51ea3cdef19c7bd60509909fa3de3
```

### 8.2 3 份 contract test

```
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

**结果**：`3 passed in 0.02s`

### 8.3 PR 状态

- PR #288 (CAD backend profile 相关): **MERGED** at 2026-04-20T12:36Z, merge commit `f001b11`
- PR #294 (auto numbering + latest released guards): **OPEN**, 9 checks (7 SUCCESS + 2 SKIPPED)

## 9. 已知边界

- 本轮未在 PR #294 的分支上做任何动作。PR #294 的内容已由独立复审确认「可合」，merge 时机由用户决定
- 本轮未跑 shared-dev 142 远端 smoke。142 当前仍是旧版服务（见 `DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SHARED_DEV_142_SMOKE_20260420.md` 的结论），smoke blocked 不是代码缺陷
- `/tmp/yuantus-pre-pull-backup-20260420/` 作为本轮操作的回退锚点，**下一次 commit 成功并 push 后**再决定是否清理

## 10. 下一步建议

1. 用户决定：把本轮 6 份 MD + 1 条 modified 索引开 doc-only PR，或并入 PR #294
2. PR #294 merge（代码部分与文档部分无互相依赖）
3. 142 smoke 在远端升级到含 `/api/v1/cad/backend-profile` 后再重跑
4. §7 列出的 3 条 follow-up 按优先级独立推进，**不阻塞** 当前 merge 节奏

## 11. Reviewer / 执行者

本轮执行由本会话的 Claude 助手以「纯读 + 纯维护 + 不 push」的模式完成。
所有可能产生远端副作用的动作（commit、push、open PR）**都未**执行，由用户保留决定权。
