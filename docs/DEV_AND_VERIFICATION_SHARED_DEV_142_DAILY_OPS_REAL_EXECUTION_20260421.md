# DEV_AND_VERIFICATION_SHARED_DEV_142_DAILY_OPS_REAL_EXECUTION_20260421

日期：2026-04-21

## 背景

`#306` 已把 `shared-dev 142` 的维护态入口固定为：

1. `readonly-rerun`
2. 失败再 `drift-audit`
3. 仍需解释再 `drift-investigation`

本轮需要确认这个维护态入口在真实 `142` 上可直接使用，而不是只在文档和 contracts 层成立。

## 本轮目标

在真实 `142` 上执行一轮最小 daily ops：

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode readonly-rerun
```

如果成功，则本轮到此结束，不继续进入 `drift-audit`。

## 实际执行

执行入口：

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode readonly-rerun
```

关键输出：

- `MODE=readonly-rerun`
- `SUMMARY_HTTP_STATUS=200`
- `BASELINE_POLICY_KIND=overdue-only-stable`

执行目录：

- precheck:
  - `tmp/p2-shared-dev-observation-142-readonly-rerun-20260421-092324-precheck/`
- readonly rerun:
  - `tmp/p2-shared-dev-observation-142-readonly-rerun-20260421-092324/`

## 结果

### Raw current

- `items_count=5`
- `pending_count=1`
- `overdue_count=4`
- `escalated_count=1`
- `total_anomalies=3`

### Stable current

- `items_count=4`
- `pending_count=0`
- `overdue_count=4`
- `escalated_count=1`
- `total_anomalies=3`

### Excluded future pending

- `approval_id=af1a2dc4-7d73-4d1d-aabb-acdde37abea8`
- `eco_name=eco-specialist`
- `stage_name=SpecialistReview`

### Final readonly eval

- verdict: `PASS`
- checks: `20/20 passed`

## 关键产物

- precheck:
  - `tmp/p2-shared-dev-observation-142-readonly-rerun-20260421-092324-precheck/OBSERVATION_PRECHECK.md`
  - `tmp/p2-shared-dev-observation-142-readonly-rerun-20260421-092324-precheck/observation_precheck.json`
  - `tmp/p2-shared-dev-observation-142-readonly-rerun-20260421-092324-precheck/summary_probe.json`
- raw current:
  - `tmp/p2-shared-dev-observation-142-readonly-rerun-20260421-092324/raw-current/OBSERVATION_RESULT.md`
  - `tmp/p2-shared-dev-observation-142-readonly-rerun-20260421-092324/raw-current/summary.json`
- stable current:
  - `tmp/p2-shared-dev-observation-142-readonly-rerun-20260421-092324/STABLE_CURRENT_TRANSFORM.md`
  - `tmp/p2-shared-dev-observation-142-readonly-rerun-20260421-092324/stable_current_transform.json`
  - `tmp/p2-shared-dev-observation-142-readonly-rerun-20260421-092324/OBSERVATION_RESULT.md`
  - `tmp/p2-shared-dev-observation-142-readonly-rerun-20260421-092324/OBSERVATION_DIFF.md`
  - `tmp/p2-shared-dev-observation-142-readonly-rerun-20260421-092324/OBSERVATION_EVAL.md`
  - `tmp/p2-shared-dev-observation-142-readonly-rerun-20260421-092324.tar.gz`

## 判断

本轮 daily ops 是绿色的：

- `readonly-rerun` 已通过
- 不需要继续执行 `drift-audit`
- 不需要继续执行 `drift-investigation`

这说明 `#306` 的维护态入口已经在真实 `142` 上成立，不只是文档层面可发现。

## 结论

从维护态角度，`shared-dev 142` 现在可以按以下准则日常使用：

1. 先跑 `readonly-rerun`
2. 绿了就结束
3. 只有失败时才进入 drift triage
