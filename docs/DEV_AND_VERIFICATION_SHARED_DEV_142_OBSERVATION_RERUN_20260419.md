# DEV / Verification - Shared-dev 142 Observation Rerun

日期：2026-04-19
仓库基线：`30aad04`（`test(scripts): lock mainline baseline switch helper contracts (#271)`）

## 背景

在 `142` 上，shared-dev 观察面此前已经完成：

- first-run bootstrap
- 一次 `escalate-overdue`
- readonly refreeze

本轮目标不是再做 reset，也不是再做写路径变更，而是按既有 shared-dev 路径重新确认三件事：

1. 本机是否已具备可复用的 142 访问参数
2. `validate -> precheck -> observation` 工具链是否还能直接跑通
3. 当前观察面是否仍与此前冻结的 readonly 基线一致

## 访问参数确认

本机已存在 observation env：

- `$HOME/.config/yuantus/p2-shared-dev.env`

本轮确认到的关键参数为：

- `BASE_URL=http://142.171.239.56:7910`
- auth mode:
  - `USERNAME/PASSWORD`
- `TENANT_ID=tenant-1`
- `ORG_ID=org-1`
- `ENVIRONMENT=shared-dev`

说明：

- 本地没有改成 `TOKEN` 路径
- 现有 env 已足够驱动 shared-dev observation wrappers

## 本机权限收紧

按约定收紧权限：

- `chmod 700 "$HOME/.config/yuantus"`
- `chmod 600 "$HOME/.config/yuantus/p2-shared-dev.env"`

最终权限：

- `~/.config/yuantus`:
  - `drwx------`
- `~/.config/yuantus/p2-shared-dev.env`:
  - `-rw-------`

## 执行过程

### 1. 先校验 observation env

执行：

```bash
scripts/validate_p2_shared_dev_env.sh \
  --mode observation \
  --observation-env "$HOME/.config/yuantus/p2-shared-dev.env"
```

结果：

- `observation env: ok`
- `base_url: http://142.171.239.56:7910`
- `tenant/org: tenant-1 / org-1`
- `auth_mode: username-password`

### 2. 跑 precheck

执行：

```bash
bash scripts/precheck_p2_observation_regression.sh \
  --env-file "$HOME/.config/yuantus/p2-shared-dev.env"
```

结果：

- `login_http_status=200`
- `summary_http_status=200`

产物：

- `tmp/p2-observation-precheck-20260419-193226/OBSERVATION_PRECHECK.md`
- `tmp/p2-observation-precheck-20260419-193226/observation_precheck.json`
- `tmp/p2-observation-precheck-20260419-193226/summary_probe.json`

### 3. 跑 observation regression wrapper

执行：

```bash
OUTPUT_DIR="./tmp/p2-shared-dev-observation-20260419-193242" \
ARCHIVE_RESULT=1 \
bash scripts/run_p2_observation_regression.sh \
  --env-file "$HOME/.config/yuantus/p2-shared-dev.env"
```

结果：

- `summary -> 200`
- `items -> 200`
- `export.json -> 200`
- `export.csv -> 200`
- `anomalies -> 200`
- `write smoke -> skip`

产物：

- `tmp/p2-shared-dev-observation-20260419-193242/summary.json`
- `tmp/p2-shared-dev-observation-20260419-193242/items.json`
- `tmp/p2-shared-dev-observation-20260419-193242/export.json`
- `tmp/p2-shared-dev-observation-20260419-193242/export.csv`
- `tmp/p2-shared-dev-observation-20260419-193242/anomalies.json`
- `tmp/p2-shared-dev-observation-20260419-193242/OBSERVATION_RESULT.md`
- `tmp/p2-shared-dev-observation-20260419-193242.tar.gz`

## 观察结果

### 1. summary

- `pending_count=2`
- `overdue_count=3`
- `escalated_count=1`

分布：

- `Review`:
  - `pending=1`
  - `overdue=3`
- `SpecialistReview`:
  - `pending=1`
  - `overdue=0`

### 2. items / export 一致性

三份清单的总条数一致：

- `items.json = 5`
- `export.json = 5`
- `export.csv = 5`

三份清单中的 `approval_id` 集合一致，均为同一组 5 条记录。

标志位统计也一致：

- overdue flags:
  - `3`
- escalated flags:
  - `1`

其中 5 条记录对应：

- `3` 条 `is_overdue=true`
- `1` 条 `is_escalated=true`
- `2` 条非 overdue pending

### 3. anomalies

- `total_anomalies=2`
- `no_candidates=0`
- `escalated_unresolved=1`
- `overdue_not_escalated=1`

对应关系：

- `escalated_unresolved` 中有 `1` 条已 escalated 且仍 unresolved 的 approval
- `overdue_not_escalated` 中有 `1` 条 overdue 但尚未 escalated 的 approval

## 与既有 frozen baseline 的关系

本轮没有设置 `BASELINE_DIR` 自动 diff，而是直接核对当前观测结果与同日 readonly refreeze 记录。

当前结果与 [DEV_AND_VERIFICATION_SHARED_DEV_142_READONLY_REFREEZE_20260419.md](./DEV_AND_VERIFICATION_SHARED_DEV_142_READONLY_REFREEZE_20260419.md) 中重新冻结后的基线一致：

- `pending_count=2`
- `overdue_count=3`
- `escalated_count=1`
- `items_count=5`
- `export_json_count=5`
- `export_csv_rows=5`
- `total_anomalies=2`
- `no_candidates=0`
- `escalated_unresolved=1`
- `overdue_not_escalated=1`

因此至少从本轮只读 rerun 看：

- 读面没有回到 first-run 当天的 `3 items` 状态
- 也没有继续漂到新的计数面
- 当前 142 shared-dev 仍保持在“refreeze 后的 5-item readonly baseline”

## 结论

- 142 的访问参数已经在本机确认并可直接使用：
  - `BASE_URL`
  - `USERNAME/PASSWORD`
  - `TENANT_ID`
  - `ORG_ID`
- observation env 已落在仓库外，并且权限已收紧到：
  - dir `0700`
  - file `0600`
- `validate -> precheck -> observation` 整条链路已再次跑通
- 当前读面与同日 `readonly refreeze` 冻结的基线一致，没有看到新的观测失真
- 本轮未触发写路径；如果下一轮要验证状态迁移，应显式再做一次 `escalate-overdue` 并带 `BASELINE_DIR/EVAL_MODE=state-change` 采样
