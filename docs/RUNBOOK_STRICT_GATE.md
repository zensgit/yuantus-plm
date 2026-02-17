# Strict Gate Runbook

目的：用一套可重复的脚本 + CI 定时任务，生成 **evidence-grade** 的回归验证报告（Markdown），并把关键日志作为 artifact 保存，方便排障与审计。

## Where It Is Used

- Script: `scripts/strict_gate_report.sh`
- CI workflow: `.github/workflows/strict-gate.yml`
- Evidence outputs:
  - Report: `docs/DAILY_REPORTS/STRICT_GATE_*.md`
  - Perf summary: `docs/DAILY_REPORTS/STRICT_GATE_*_PERF.md`
  - Perf trend: `docs/DAILY_REPORTS/STRICT_GATE_*_PERF_TREND.md`
  - Logs: `tmp/strict-gate/<run_id>/*.log`

## What It Runs

`scripts/strict_gate_report.sh` 会串行执行并汇总：

- `pytest (targeted)`：可选（由 `TARGETED_PYTEST_ARGS` 决定）
- `pytest (non-DB)`：默认全量 non-DB 测试
- `pytest (DB)`：默认全量 DB 测试（由 `YUANTUS_PYTEST_DB=1` 控制）
- `verify_run_h_e2e`：可选（由 `RUN_RUN_H_E2E=1` 控制；Run H 自包含 API-only E2E）
- `verify_identity_only_migrations`：可选（由 `RUN_IDENTITY_ONLY_MIGRATIONS_E2E=1` 控制；Identity-only migrations 契约）
- `verify_release_orchestration_perf_smoke`：可选（由 `RUN_RELEASE_ORCH_PERF=1` 控制）
- `verify_esign_perf_smoke`：可选（由 `RUN_ESIGN_PERF=1` 控制）
- `verify_reports_perf_smoke`：可选（由 `RUN_REPORTS_PERF=1` 控制）
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

- 开启 Shell E2E（Run H + identity-only migrations）：

```bash
RUN_RUN_H_E2E=1 RUN_IDENTITY_ONLY_MIGRATIONS_E2E=1 \
  bash scripts/strict_gate_report.sh
```

- 开启 perf smoke（三条自包含脚本）：

```bash
RUN_RELEASE_ORCH_PERF=1 RUN_ESIGN_PERF=1 RUN_REPORTS_PERF=1 \
  bash scripts/strict_gate_report.sh
```

- 从 strict-gate 日志目录生成 perf 摘要（本地或下载 CI artifact 后均可）：

```bash
python3 scripts/strict_gate_perf_summary.py \
  --logs-dir tmp/strict-gate/<run_id> \
  --out docs/DAILY_REPORTS/STRICT_GATE_<run_id>_PERF.md
```

- 从多个 `*_PERF.md` 生成趋势表（默认仅统计有 metrics 的 run）：

```bash
python3 scripts/strict_gate_perf_trend.py \
  --dir docs/DAILY_REPORTS \
  --out docs/DAILY_REPORTS/STRICT_GATE_PERF_TREND.md \
  --limit 30
```

- 自动下载最近 N 次 CI perf summary 并一键生成趋势（需要 `gh auth login`）：

```bash
scripts/strict_gate_perf_download_and_trend.sh \
  --limit 10 \
  --branch main \
  --conclusion failure \
  --artifact-name strict-gate-perf-summary \
  --download-dir tmp/strict-gate-artifacts/recent-perf \
  --trend-out tmp/strict-gate-artifacts/recent-perf/STRICT_GATE_PERF_TREND.md \
  --json-out tmp/strict-gate-artifacts/recent-perf/strict_gate_perf_download.json
```

- 快速复盘单次异常 run（跳过 run list，直接下载指定 run id）：

```bash
scripts/strict_gate_perf_download_and_trend.sh \
  --run-id <run_id> \
  --artifact-name strict-gate-perf-summary \
  --download-dir tmp/strict-gate-artifacts/recent-perf \
  --trend-out tmp/strict-gate-artifacts/recent-perf/STRICT_GATE_PERF_TREND.md \
  --json-out tmp/strict-gate-artifacts/recent-perf/strict_gate_perf_download.json \
  --include-empty
```

说明：
- `--run-id` 模式会跳过 `gh run list`；此时 `--conclusion` 过滤不会生效。
- 默认 artifact 名称是 `strict-gate-perf-summary`；若 workflow 里更改过 artifact 名，可改为 `--artifact-name <name>`。

- 只跑某个 Playwright spec：

```bash
PLAYWRIGHT_CMD='npx playwright test playwright/tests/export_bundles_api.spec.js' \
  bash scripts/strict_gate_report.sh
```

## Run In CI

Workflow: `.github/workflows/strict-gate.yml`

- Triggers:
  - schedule:
    - 每天 `03:00 UTC`（core strict gate，默认不跑 perf-smokes）
    - 每周一 `04:00 UTC`（自动开启 perf-smokes）
  - workflow_dispatch: 手动触发（可选 `run_demo=true`、`run_perf_smokes=true`）

Outputs:

- Job summary：会直接展示 strict gate 报告内容（含失败 tail）
- Artifacts:
  - `strict-gate-report`：报告 Markdown
  - `strict-gate-perf-summary`：perf-smoke 摘要 Markdown（无 perf 数据时会显示 skipped/missing 说明）
  - `strict-gate-perf-trend`：perf 趋势 Markdown（聚合可见的 `*_PERF.md`）
  - `strict-gate-logs`：`tmp/strict-gate/...` 的日志目录

### Trigger From CLI (Recommended)

用 `gh` 直接触发（避免点网页）：

```bash
# 不跑 demo（推荐，默认）
gh workflow run strict-gate --ref <branch> -f run_demo=false -f run_perf_smokes=false

# 跑 demo
gh workflow run strict-gate --ref <branch> -f run_demo=true -f run_perf_smokes=false

# 跑 perf smoke（仍保持 demo 关闭）
gh workflow run strict-gate --ref <branch> -f run_demo=false -f run_perf_smokes=true
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
gh run download "$RUN_ID" -n strict-gate-perf-summary -D "$OUT_DIR"
gh run download "$RUN_ID" -n strict-gate-perf-trend -D "$OUT_DIR"
gh run download "$RUN_ID" -n strict-gate-logs   -D "$OUT_DIR"
```

说明：
- strict gate 报告与日志是在 Actions runner 的工作区生成，并通过 artifact 上传；默认不会提交回 repo。
- `strict-gate-report` 解压后会包含类似路径：`docs/DAILY_REPORTS/STRICT_GATE_CI_<run_id>.md`
- `strict-gate-perf-summary` 解压后会包含类似路径：`docs/DAILY_REPORTS/STRICT_GATE_CI_<run_id>_PERF.md`
- `strict-gate-perf-trend` 解压后会包含类似路径：`docs/DAILY_REPORTS/STRICT_GATE_CI_<run_id>_PERF_TREND.md`
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
- `verify_*_perf_smoke` 失败：先看对应步骤的 p95 报错与阈值，再看同目录下 `server.log` 与 `*_summary.json`
