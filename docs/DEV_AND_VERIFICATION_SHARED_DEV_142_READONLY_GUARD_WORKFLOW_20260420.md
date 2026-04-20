# DEV / Verification - Shared-dev 142 Readonly Guard Workflow

日期：2026-04-20
仓库基线：`3d52f68`（`Make CAD backend profile selection scope-aware with verifier (#287)`）

## 目标

把 shared-dev `142` 的 readonly/workflow 校验从“只能在本机 wrapper 上跑”收成一条真正可手动触发、可定时执行的 GitHub Actions guard。

## 问题

现有 `scripts/run_p2_shared_dev_142_workflow_readonly_check.sh` 虽然已经能：

1. dispatch `p2-observation-regression`
2. 下载 workflow artifact
3. 跟 frozen readonly baseline 做 compare/eval

但它默认依赖本机未纳管的：

- `./tmp/p2-shared-dev-observation-20260419-193242`
- `./tmp/p2-shared-dev-observation-20260419-193242.tar.gz`

这在 GitHub runner 上并不存在，所以如果直接只加 workflow，调度会在 baseline restore 之前就失败。

## 本轮改动

### 1. 把 142 frozen readonly baseline 纳入仓库

新增受控 baseline 目录：

- `artifacts/p2-observation/shared-dev-142-readonly-20260419/`

包含：

- `summary.json`
- `items.json`
- `export.json`
- `export.csv`
- `anomalies.json`
- `OBSERVATION_RESULT.md`
- `README.txt`

### 2. 让两个 readonly wrapper 都能回退到受控 baseline

更新脚本：

- `scripts/run_p2_shared_dev_142_readonly_rerun.sh`
- `scripts/run_p2_shared_dev_142_workflow_readonly_check.sh`

新行为：

- 仍然优先使用当前 canonical `./tmp/...` baseline dir
- 如果 canonical dir 缺失，仍优先尝试 canonical archive
- 如果 archive 也缺失，则回退到仓库内受控 baseline：
  - `./artifacts/p2-observation/shared-dev-142-readonly-20260419`

这样本机和 GitHub runner 都能恢复同一套 frozen baseline，不再依赖操作者机器上残留的 `tmp/` 目录。

### 3. 新增 shared-dev 142 readonly guard workflow

新增：

- `.github/workflows/shared-dev-142-readonly-guard.yml`

行为：

- `workflow_dispatch`
- `schedule`
- 固定用 repo token 运行 `run_p2_shared_dev_142_workflow_readonly_check.sh`
- 固定对 `main` 进行 dispatch + artifact compare/eval
- 上传：
  - `tmp/p2-shared-dev-142-readonly-guard/<run_id>`
  - `tmp/p2-shared-dev-142-readonly-guard/<run_id>.tar.gz`

### 4. 补 contract test + CI wiring

新增：

- `src/yuantus/meta_engine/tests/test_shared_dev_142_readonly_guard_workflow_contracts.py`

覆盖：

- workflow 触发器、权限、summary、artifact 上传
- 受控 baseline 目录完整性
- readonly wrappers 的 tracked-baseline fallback

同时把这条新 contract test 接进：

- `.github/workflows/ci.yml`

## 验证

执行：

```bash
bash -n scripts/run_p2_shared_dev_142_readonly_rerun.sh
bash -n scripts/run_p2_shared_dev_142_workflow_readonly_check.sh
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_shared_dev_142_readonly_guard_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_manual_dispatch_presence_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py
```

结果：

- shell syntax: 通过
- pytest: 通过

## 结论

到这一步，shared-dev `142` 的 readonly/workflow 路径已经不再依赖操作者本机 `tmp/` 残留状态：

1. baseline 有了仓库内受控来源
2. wrapper 能在 runner 上恢复 baseline
3. GitHub Actions 有了正式的 manual/scheduled guard 入口

这条线后续就可以从“人工触发”进入“持续守护”。
