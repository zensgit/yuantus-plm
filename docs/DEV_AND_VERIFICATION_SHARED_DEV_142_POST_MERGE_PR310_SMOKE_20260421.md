# DEV_AND_VERIFICATION_SHARED_DEV_142_POST_MERGE_PR310_SMOKE_20260421

## 1. 目标

PR #310 `feat: add lifecycle suspended write guard` 合入 `main` 后，对真实 shared-dev 142 做一次 post-merge readonly smoke。

本轮只验证远端观察面仍稳定：

- 不执行 first-run bootstrap
- 不重置 142
- 不 seed fixture
- 不打开 write smoke
- 只使用 existing shared-dev observation / readonly rerun 工具链

## 2. 基线

- local branch: `docs/shared-dev-142-pr310-smoke-20260421`
- local main before branch: `3eb986bae54b4ddfe178de77769b4437a3288849`
- merged PR: `#310`
- merged commit: `3eb986b feat: add lifecycle suspended write guard (#310)`
- target: `http://142.171.239.56:7910`
- tenant/org: `tenant-1 / org-1`
- auth mode: username/password via local env file
- env file: `$HOME/.config/yuantus/p2-shared-dev.env`

## 3. 执行命令

### 3.1 env validation

```bash
bash scripts/validate_p2_shared_dev_env.sh \
  --mode observation \
  --observation-env "$HOME/.config/yuantus/p2-shared-dev.env"
```

结果：

```text
[ok] observation env: /Users/chouhua/.config/yuantus/p2-shared-dev.env
     base_url: http://142.171.239.56:7910
     tenant/org: tenant-1 / org-1
     auth_mode: username-password
```

### 3.2 readonly rerun

```bash
bash scripts/run_p2_shared_dev_142_readonly_rerun.sh \
  --env-file "$HOME/.config/yuantus/p2-shared-dev.env" \
  --output-dir ./tmp/p2-shared-dev-142-post-merge-pr310-20260421-112847
```

结果：

- precheck: success
- summary endpoint: HTTP 200
- observation endpoints: all HTTP 200
- write smoke: skipped
- baseline policy: `overdue-only-stable`
- readonly evaluation: PASS

## 4. 产物

- precheck: `tmp/p2-shared-dev-142-post-merge-pr310-20260421-112847-precheck/OBSERVATION_PRECHECK.md`
- raw current: `tmp/p2-shared-dev-142-post-merge-pr310-20260421-112847/raw-current/OBSERVATION_RESULT.md`
- stable transform: `tmp/p2-shared-dev-142-post-merge-pr310-20260421-112847/STABLE_CURRENT_TRANSFORM.md`
- stable current: `tmp/p2-shared-dev-142-post-merge-pr310-20260421-112847/OBSERVATION_RESULT.md`
- diff: `tmp/p2-shared-dev-142-post-merge-pr310-20260421-112847/OBSERVATION_DIFF.md`
- eval: `tmp/p2-shared-dev-142-post-merge-pr310-20260421-112847/OBSERVATION_EVAL.md`
- archive: `tmp/p2-shared-dev-142-post-merge-pr310-20260421-112847.tar.gz`

## 5. Precheck

`OBSERVATION_PRECHECK.md`:

```text
result: success
reason: summary endpoint ok
environment: shared-dev-142-readonly-precheck
login_http_status: 200
summary_http_status: 200
tenant_id: tenant-1
org_id: org-1
```

## 6. Raw Current

Raw current 是远端实时观察结果，包含 1 条未来 deadline pending approval：

| Metric | Value |
|---|---:|
| pending_count | 1 |
| overdue_count | 4 |
| escalated_count | 1 |
| items_count | 5 |
| export_json_count | 5 |
| export_csv_rows | 5 |
| total_anomalies | 3 |

该 pending 项：

- ECO: `eco-specialist`
- stage: `SpecialistReview`
- assignee: `admin`
- deadline: `2026-04-21T09:34:33.658929`

## 7. Stable Transform

当前 tracked baseline 使用 `overdue-only-stable` policy。工具链按该 policy 排除 raw current 中 1 条 future-deadline pending approval，生成 stable current。

`STABLE_CURRENT_TRANSFORM.md`：

```text
verdict: PASS
stable_current_ready: true
summary: Excluded 1 pending approval(s) from the raw shared-dev 142 observation set.
```

Stable current 结果：

| Metric | Raw current | Stable current | Delta |
|---|---:|---:|---:|
| items_count | 5 | 4 | -1 |
| pending_count | 1 | 0 | -1 |
| overdue_count | 4 | 4 | 0 |
| escalated_count | 1 | 1 | 0 |
| total_anomalies | 3 | 3 | 0 |

## 8. Readonly Diff

Stable current 与 `shared-dev-142-readonly-20260421` baseline 完全一致。

| Metric | Baseline | Current | Delta |
|---|---:|---:|---:|
| pending_count | 0 | 0 | 0 |
| overdue_count | 4 | 4 | 0 |
| escalated_count | 1 | 1 | 0 |
| items_count | 4 | 4 | 0 |
| export_json_count | 4 | 4 | 0 |
| export_csv_rows | 4 | 4 | 0 |
| total_anomalies | 3 | 3 | 0 |
| no_candidates | 0 | 0 | 0 |
| escalated_unresolved | 1 | 1 | 0 |
| overdue_not_escalated | 2 | 2 | 0 |

## 9. Evaluation

`OBSERVATION_EVAL.md`：

```text
mode: readonly
verdict: PASS
checks: 20/20 passed
```

关键检查：

- items/export row count consistency: PASS
- summary matches items: PASS
- anomaly total matches category counts: PASS
- readonly stability for all tracked metrics: PASS

## 10. 结论

PR #310 合入后，shared-dev 142 observation/read-only 回归稳定：

- 142 服务可访问
- 登录成功
- dashboard summary/items/export/audit anomalies 全部 HTTP 200
- stable current 与 official readonly baseline 无差异
- 20/20 readonly evaluation checks passed
- 未执行任何 bootstrap/reset/seed/write smoke

本轮结论：PR #310 没有破坏 shared-dev 142 的 P2 observation 读面与 readonly baseline。

## 11. 下一步

按当前路线，下一条开发建议进入 CAD backend profile A：

- STEP/IGES 双后端选择
- backend registry/profile 分派最小闭环
- 完成后再把 scheduler bounded increment 提为 P0 决策点
