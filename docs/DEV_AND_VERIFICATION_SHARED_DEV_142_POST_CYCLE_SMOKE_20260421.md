# DEV_AND_VERIFICATION_SHARED_DEV_142_POST_CYCLE_SMOKE_20260421

日期：2026-04-21

## 1. 目标

本轮在连续合入 scheduler、CAD profile、Line A、Suspended guard、BOM import dedup aggregation 等 bounded increments 后，做一次 shared-dev `142` 只读收口验证。

目标不是启动新功能，也不是 first-run bootstrap，而是确认当前 `main` 合并后：

- `142` 仍能通过官方 readonly baseline 入口；
- P2 observation dashboard / export / audit 读面稳定；
- 当前 cycle 可以进入收口状态，再决定下一条业务增量。

## 2. 执行入口

执行命令：

```bash
OUTPUT_DIR="./tmp/p2-shared-dev-142-post-cycle-smoke-20260421-173223" \
bash scripts/run_p2_shared_dev_142_entrypoint.sh \
  --mode readonly-rerun \
  -- --output-dir "$OUTPUT_DIR"
```

实际入口展开：

- selector: `scripts/run_p2_shared_dev_142_entrypoint.sh`
- mode: `readonly-rerun`
- target: `scripts/run_p2_shared_dev_142_readonly_rerun.sh`
- env file: `$HOME/.config/yuantus/p2-shared-dev.env`
- base URL: `http://142.171.239.56:7910`
- tenant/org: `tenant-1` / `org-1`
- auth mode: username/password login

边界：

- 未执行 first-run bootstrap；
- 未启用 write smoke；
- 未直接写 DB；
- 未开启 scheduler on shared-dev；
- 未修改远端配置。

## 3. Precheck

Precheck 输出：

- directory: `tmp/p2-shared-dev-142-post-cycle-smoke-20260421-173223-precheck/`
- `SUMMARY_HTTP_STATUS=200`
- `login_http_status=200`
- `summary_http_status=200`
- result: `success`
- reason: `summary endpoint ok`

关键产物：

- `tmp/p2-shared-dev-142-post-cycle-smoke-20260421-173223-precheck/OBSERVATION_PRECHECK.md`
- `tmp/p2-shared-dev-142-post-cycle-smoke-20260421-173223-precheck/observation_precheck.json`
- `tmp/p2-shared-dev-142-post-cycle-smoke-20260421-173223-precheck/summary_probe.json`

## 4. Raw Current

Raw current 是直接从 `142` 当前状态读取的结果。

产物目录：

- `tmp/p2-shared-dev-142-post-cycle-smoke-20260421-173223/raw-current/`

核心指标：

| Metric | Value |
|---|---:|
| `items_count` | 5 |
| `pending_count` | 1 |
| `overdue_count` | 4 |
| `escalated_count` | 1 |
| `total_anomalies` | 3 |

Raw current 包含 1 条未来 pending：

- approval: `af1a2dc4-7d73-4d1d-aabb-acdde37abea8`
- ECO: `eco-specialist`
- stage: `SpecialistReview`
- assignee: `admin`

该 pending 属于已知 baseline policy 处理范围，不作为 readonly drift。

## 5. Stable Current Transform

当前 official baseline 使用 `overdue-only-stable` policy。脚本按策略从 raw current 中排除未来 pending，生成用于 readonly compare 的 stable current。

Transform 结果：

- verdict: `PASS`
- stable_current_ready: `true`
- excluded pending approvals: `1`
- policy kind: `overdue-only-stable`

Stable current 指标：

| Metric | Raw | Stable | Delta |
|---|---:|---:|---:|
| `items_count` | 5 | 4 | -1 |
| `pending_count` | 1 | 0 | -1 |
| `overdue_count` | 4 | 4 | 0 |
| `escalated_count` | 1 | 1 | 0 |
| `total_anomalies` | 3 | 3 | 0 |

关键产物：

- `tmp/p2-shared-dev-142-post-cycle-smoke-20260421-173223/STABLE_CURRENT_TRANSFORM.md`
- `tmp/p2-shared-dev-142-post-cycle-smoke-20260421-173223/stable_current_transform.json`

## 6. Readonly Compare

Baseline：

- `tmp/p2-shared-dev-observation-20260421-stable`
- label: `shared-dev-142-readonly-20260421`

Current：

- `tmp/p2-shared-dev-142-post-cycle-smoke-20260421-173223`
- label: `current-rerun`

Readonly diff：

| Metric | Baseline | Current | Delta |
|---|---:|---:|---:|
| `pending_count` | 0 | 0 | 0 |
| `overdue_count` | 4 | 4 | 0 |
| `escalated_count` | 1 | 1 | 0 |
| `items_count` | 4 | 4 | 0 |
| `export_json_count` | 4 | 4 | 0 |
| `export_csv_rows` | 4 | 4 | 0 |
| `total_anomalies` | 3 | 3 | 0 |
| `no_candidates` | 0 | 0 | 0 |
| `escalated_unresolved` | 1 | 1 | 0 |
| `overdue_not_escalated` | 2 | 2 | 0 |

Evaluation：

- verdict: `PASS`
- checks: `20/20 passed`

关键产物：

- `tmp/p2-shared-dev-142-post-cycle-smoke-20260421-173223/OBSERVATION_RESULT.md`
- `tmp/p2-shared-dev-142-post-cycle-smoke-20260421-173223/OBSERVATION_DIFF.md`
- `tmp/p2-shared-dev-142-post-cycle-smoke-20260421-173223/OBSERVATION_EVAL.md`
- `tmp/p2-shared-dev-142-post-cycle-smoke-20260421-173223.tar.gz`

## 7. 判断

本轮 post-cycle smoke 结论为绿色：

- precheck 成功；
- 5 个 observation read endpoints 全部 HTTP 200；
- stable current transform 成功；
- readonly compare 对 frozen baseline 无漂移；
- eval `20/20 passed`；
- 不需要进入 `drift-audit`；
- 不需要进入 `drift-investigation`。

这说明当前 cycle 合入后的 `main` 没有破坏 `142` 的官方 readonly baseline 观察面。

## 8. Gap Analysis 下一步建议

Claude 给出的 gap progress redraw 基本成立，但我建议先做这次收口，再进入下一条功能线。基于本轮 smoke 已绿，下一步排序如下：

1. `§一.5 BOM→MBOM handler`
   - scheduler 基础设施和 activation smoke 已就绪；
   - 这是下一个能把 scheduler 从基础设施推进到业务 consumer 的增量；
   - 建议先写 bounded task doc，再实现 handler，避免一次性扩大到全套 MBOM 日期生效调度。
2. 产品描述多语言 helper
   - 小到中等规模，独立于 scheduler；
   - 可作为 §一.6 的剩余项处理。
3. 同 `(parent, child)` 不同 UOM 双 BOM line 支持
   - 需要重新定义 `BOMService.get_bom_line_by_parent_child` 的唯一语义；
   - 会影响 where-used / 报表 / import 行为，不能作为极小修补处理。
4. `_refdes_tokens` natural sort
   - 极小修补；
   - 只影响显示稳定性，不改变业务主链，优先级低于 §一.5。

## 9. 本轮未做

- 未启动 Claude Code CLI 做新实现；
- 未改运行时代码；
- 未做 142 write smoke；
- 未做 first-run bootstrap；
- 未 refreeze baseline；
- 未启动 §一.5 handler 实现。

## 10. 结论

当前 cycle 可以标记为收口完成。

下一条建议进入 `§一.5 BOM→MBOM handler`，但应先输出任务书并明确：

- 只做第一个 scheduler business consumer；
- 默认保持 scheduler off；
- 142 只做只读/no-op smoke，不做远端写入；
- handler 的写入行为先在 local activation smoke 中证明。
