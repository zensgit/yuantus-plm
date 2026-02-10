# Strict Gate Runbook

目的：用一套可重复的脚本 + CI 定时任务，生成 **evidence-grade** 的回归验证报告（Markdown），并把关键日志作为 artifact 保存，方便排障与审计。

## Where It Is Used

- Script: `scripts/strict_gate_report.sh`
- CI workflow: `.github/workflows/strict-gate.yml`
- Evidence outputs:
  - Report: `docs/DAILY_REPORTS/STRICT_GATE_*.md`
  - Logs: `tmp/strict-gate/<run_id>/*.log`

## What It Runs

`scripts/strict_gate_report.sh` 会串行执行并汇总：

- `pytest (targeted)`：可选（由 `TARGETED_PYTEST_ARGS` 决定）
- `pytest (non-DB)`：默认全量 non-DB 测试
- `pytest (DB)`：默认全量 DB 测试（由 `YUANTUS_PYTEST_DB=1` 控制）
- `demo_plm_closed_loop`：可选（由 `DEMO_SCRIPT=1` 控制）
- `playwright`：默认执行 `npx playwright test`（主要是 API-only 断言）

脚本会生成单份 Markdown 报告，并在失败时追加 **失败日志 tail**（便于在 CI Summary 里直接定位问题）。

## Run Locally

基础用法（输出到默认路径）：

```bash
bash scripts/strict_gate_report.sh
```

查看帮助（包含环境变量/示例）：

```bash
scripts/strict_gate_report.sh --help
```

常用参数：

- 自定义输出目录/报告路径：

```bash
OUT_DIR=tmp/strict-gate/local \
REPORT_PATH=docs/DAILY_REPORTS/STRICT_GATE_local.md \
  bash scripts/strict_gate_report.sh
```

- 只跑一组 targeted tests（可用于快速验证某个修复）：

```bash
TARGETED_PYTEST_ARGS='src/yuantus/meta_engine/tests/test_perf_gate_config_file.py' \
  bash scripts/strict_gate_report.sh
```

- 包含闭环 demo（会额外生成 demo report 并在 strict gate 报告中记录其路径）：

```bash
DEMO_SCRIPT=1 bash scripts/strict_gate_report.sh
```

- 只跑某个 Playwright spec：

```bash
PLAYWRIGHT_CMD='npx playwright test playwright/tests/export_bundles_api.spec.js' \
  bash scripts/strict_gate_report.sh
```

## Run In CI

Workflow: `.github/workflows/strict-gate.yml`

- Triggers:
  - schedule: 每天 `03:00 UTC`
  - workflow_dispatch: 手动触发（可选 `run_demo=true`）

Outputs:

- Job summary：会直接展示 strict gate 报告内容（含失败 tail）
- Artifacts:
  - `strict-gate-report`：报告 Markdown
  - `strict-gate-logs`：`tmp/strict-gate/...` 的日志目录

### Trigger From CLI (Recommended)

用 `gh` 直接触发（避免点网页）：

```bash
# 不跑 demo（推荐，默认）
gh workflow run strict-gate --ref <branch> -f run_demo=false

# 跑 demo
gh workflow run strict-gate --ref <branch> -f run_demo=true
```

找到对应的 workflow run（run id 会被用于报告文件名）：

```bash
gh run list --workflow strict-gate --branch <branch> --limit 5
```

下载 artifacts（推荐下载到单独目录，避免污染当前工作区）：

```bash
RUN_ID=<run_id>
OUT_DIR=tmp/strict-gate-artifacts/$RUN_ID
mkdir -p "$OUT_DIR"

gh run download "$RUN_ID" -n strict-gate-report -D "$OUT_DIR"
gh run download "$RUN_ID" -n strict-gate-logs   -D "$OUT_DIR"
```

说明：
- strict gate 报告与日志是在 Actions runner 的工作区生成，并通过 artifact 上传；默认不会提交回 repo。
- `strict-gate-report` 解压后会包含类似路径：`docs/DAILY_REPORTS/STRICT_GATE_CI_<run_id>.md`
- `strict-gate-logs` 解压后会包含类似路径：`tmp/strict-gate/STRICT_GATE_CI_<run_id>/*.log`

## How To Triage A Failure

1) 先看 workflow run 的 **Job Summary**：报告里会标出哪一步失败，并附上该步日志的 tail。

2) 若需要完整上下文：

- 下载 artifact `strict-gate-logs`
- 打开对应的 `tmp/strict-gate/<run_id>/*.log`

3) 常见定位线索：

- `pytest (DB)` 失败：通常与 migrations/DB fixture/事务隔离有关
- `playwright` 失败：通常是 API 响应契约变化、权限变化或导出文件名变化
- `demo_plm_closed_loop` 失败：查看 demo log 的最后 160 行，通常会包含 HTTP code + body 路径
