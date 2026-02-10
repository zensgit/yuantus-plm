# Runbook: CI/Regression Change Scope (Skip Rules + Force Full Runs)

目的：解释 GitHub Actions 中 `CI` / `regression` 两条流水线的 **变更范围判定**（哪些改动会触发哪些 job），以及在需要时如何 **强制跑全量**。

## 0) 从哪里看“为什么被跳过”

两条 workflow 都会把判定结果写到 `GITHUB_STEP_SUMMARY`：

- `CI` workflow：`detect_changes (CI)` job 的 Summary 会输出：
  - `run_plugin_tests`
  - `run_playwright`
  - `run_contracts`
- `regression` workflow：`detect_changes (regression)` job 的 Summary 会输出：
  - `cadgf_changed`
  - `regression_needed`

注意：如果 job 是被 `if:` 条件跳过（skipped），在 PR 页面点 “Re-run jobs” 通常不会让它变成执行，必须触发一次新的 workflow run（见下文“强制跑”）。

## 1) CI workflow（`.github/workflows/ci.yml`）

默认行为：

- `push` 到 `main`：始终跑全量（plugin-tests + playwright + contracts）
- `pull_request`：根据文件路径变化决定是否跑重任务（节省 CI 分钟数）
- `workflow_dispatch`（手动触发）：始终跑全量（用于强制跑）

### 1.1 PR 下的触发规则（概览）

- `contracts`（轻量）会在 PR 中被触发当你改动：
  - `.github/workflows/*.yml|*.yaml`
  - `configs/perf_gate.json`
  - `scripts/perf_*.py|scripts/perf_*.sh`
  - `docs/DELIVERY_DOC_INDEX.md`
- `plugin-tests`（含 migrations smoke）会在 PR 中被触发当你改动：
  - `src/**`（非 `tests/` 且非 `test_*.py`）
  - `migrations/**`
  - 或关键依赖/工作流文件：`.github/workflows/ci.yml`, `pyproject.toml`, `requirements.lock`, `alembic.ini`
- `playwright-esign` 会在 PR 中被触发当你改动：
  - `src/**`（非 `tests/` 且非 `test_*.py`）
  - `playwright/**`
  - `package.json` / `package-lock.json`
  - 或关键依赖/工作流文件：`.github/workflows/ci.yml`, `pyproject.toml`, `requirements.lock`, `alembic.ini`

精确逻辑以 `detect_changes (CI)` job 脚本为准。

### 1.2 如何强制跑全量 CI

方式 A（推荐）：手动触发 `CI` workflow（workflow_dispatch）

1. GitHub → Actions → 选择 `CI`
2. 点击 “Run workflow”
3. 选择你的分支（PR branch）
4. Run

因为 `workflow_dispatch` 事件会走 “非 PR 事件 → 全量开启” 分支，所以会跑全量 job。

方式 A2（可选）：用 `gh` 触发 workflow_dispatch（不需要点网页）

```bash
# 触发 CI workflow（选择 PR 分支）
gh workflow run CI --ref <branch>
```

方式 B：让 PR 的变更命中“全量触发”路径

例如触碰任一文件（即使是无害改动）：

- `pyproject.toml` 或 `requirements.lock`
- `.github/workflows/ci.yml`
- `alembic.ini`

不推荐作为常规手段（会污染 diff），但在紧急情况下可用。

### 1.3 PR Label Overrides（在 PR Checks 内强制跑）

如果你有权限给 PR 加 label，可以用 label 覆盖 change-scope 检测，让重任务在 PR checks 内执行：

- `ci:full`
  - 强制 `plugin-tests` + `playwright-esign` + `contracts` 全部执行
  - 在 `detect_changes (CI)` 的 job summary 中会显示 `force_full=true`

示例（CLI）：

```bash
gh pr edit <pr_number> --add-label "ci:full"
```

## 2) Regression workflow（`.github/workflows/regression.yml`）

默认行为：

- `schedule`（定时）/ `workflow_dispatch`（手动）：始终跑全量 docker-compose regression
- `push` / `pull_request`：仅当变更集可能影响运行时/集成时才跑（否则跳过）

### 2.1 PR/push 下的触发规则（概览）

`regression_needed=true`（会跑 docker compose 集成回归）当你改动：

- 依赖/迁移/运行关键文件：`pyproject.toml`, `requirements.lock`, `alembic.ini`, `migrations/**`
- 运行容器/compose：`docker-compose*.yml`, `Dockerfile*`
- 回归脚本：`scripts/verify_all.sh`, `scripts/verify_*.sh`
- 样例数据：`docs/samples/**`
- `src/**`（非 `tests/` 且非 `test_*.py`）

`cadgf_changed=true`（会跑 CADGF preview 子任务）当你改动匹配 CADGF 相关路径（见 `detect_changes (regression)` job 脚本里的正则）。

### 2.2 如何强制跑全量 regression

推荐：手动触发 `regression` workflow（workflow_dispatch）

1. GitHub → Actions → 选择 `regression`
2. 点击 “Run workflow”
3. 选择你的分支
4. （可选）设置 `run_cad_ml=true` 启动 cad-ml docker
5. Run

也可以用 `gh` 触发：

```bash
gh workflow run regression --ref <branch> -f run_cad_ml=false
```

### 2.3 PR Label Overrides（在 PR Checks 内强制跑）

在 PR 上添加以下 label 可覆盖 `detect_changes (regression)` 的判定：

- `ci:full`：强制 `regression_needed=true` 且 `cadgf_changed=true`
- `regression:force`：强制 `regression_needed=true`
- `cadgf:force`：强制 `cadgf_changed=true`

示例：

```bash
gh pr edit <pr_number> --add-label "regression:force"
```

## 3) 并发取消（避免浪费）

以下 workflow 已启用 `concurrency`（同一 ref 新跑会 cancel 旧跑）：

- `CI`
- `regression`
- `strict-gate`
- `perf-p5-reports`
- `perf-roadmap-9-3`

含义：你在 PR 上连续 push 多次时，旧的 in-progress runs 会被自动取消，减少排队与 CI minutes 消耗。
