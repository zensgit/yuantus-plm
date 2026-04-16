# P2-3 R2: ECO Stage SLA Dashboard — Development & Verification

**Branch:** feature/claude-c43-cutted-parts-throughput
**Date:** 2026-04-15
**Status:** ✅ 241 passed, 0 failed (17 focused tests)

---

## R1 → R2 修复

### Fix 1 (High): Items 绑定当前 stage

**问题**: `ECOApproval` 只按 `eco_id` join，历史 stage 的 pending 审批混进仪表盘。

**修复**: 抽取 `_base_dashboard_query()`，join 条件加 `ECOApproval.stage_id == ECO.stage_id`：

```python
def _base_dashboard_query(self):
    return (
        self.session.query(ECO, ECOStage, ECOApproval)
        .join(ECOStage, ECO.stage_id == ECOStage.id)
        .join(ECOApproval, (
            (ECOApproval.eco_id == ECO.id)
            & (ECOApproval.stage_id == ECO.stage_id)  # ← Fix
        ))
        .filter(...)
    )
```

**Tests:**
- `test_base_query_joins_approval_stage_to_eco_stage` — 源码验证 join 条件
- `test_summary_and_items_share_base_query` — 两个方法共用同一 base query

### Fix 2 (High): Summary 和 Items 统一统计口径

**问题**: headline (pending/overdue) 按 ECO 数，by_assignee/escalated 按 ECOApproval 数 → 不可对账。

**修复**: summary 也从 `_base_dashboard_query()` 的三表行推导，每行 = 一条 pending ECOApproval。

| 指标 | 统计单位 | 来源 |
|---|---|---|
| `pending_count` | ECOApproval rows (not overdue) | base query |
| `overdue_count` | ECOApproval rows (overdue) | base query |
| `escalated_count` | ECOApproval rows (required_role=admin) | base query |
| `by_stage` | ECOApproval rows grouped by stage | base query |
| `by_role` | ECOApproval rows expanded by stage roles | base query |
| `by_assignee` | ECOApproval rows grouped by user | base query |

**Tests:**
- `test_summary_counts_match_row_count` — pending + overdue == total rows
- `test_by_assignee_sums_to_total` — sum(assignee.pending_count) == total
- `test_escalated_count_subset_of_total` — escalated <= total

---

## 文件改动

| File | Change |
|---|---|
| `services/eco_service.py` | `_base_dashboard_query()` 新增; `get_approval_dashboard_summary()` 重写从 base query 推导; `get_approval_dashboard_items()` 改用 base query |
| `tests/test_eco_approval_dashboard.py` | 旧 summary tests 改用 `_base_dashboard_query` mock; +5 new R2 tests |

---

## Focused Tests (17)

```
TestDashboardRoutes (2)
  test_summary_route_registered                         PASSED
  test_items_route_registered                           PASSED

TestDashboardSummary (5)
  test_returns_all_required_keys                        PASSED
  test_counts_overdue_vs_pending                        PASSED
  test_by_stage_aggregation                             PASSED
  test_by_role_aggregation                              PASSED
  test_excludes_none_approval_stages                    PASSED

TestDashboardItems (3)
  test_returns_item_shape                               PASSED
  test_overdue_filter                                   PASSED
  test_escalated_filter                                 PASSED

TestDashboardHTTP (2)
  test_summary_200                                      PASSED
  test_items_200_with_filter                            PASSED

TestCurrentStageBinding (2)  ← R2 new
  test_base_query_joins_approval_stage_to_eco_stage     PASSED
  test_summary_and_items_share_base_query               PASSED

TestUnifiedStatistics (3)  ← R2 new
  test_summary_counts_match_row_count                   PASSED
  test_by_assignee_sums_to_total                        PASSED
  test_escalated_count_subset_of_total                  PASSED
```

---

## 验证命令

```bash
# P2-3 focused
python3 -m pytest src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py -v
# Expected: 17 passed

# Full P2 suite
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py \
  -v
# Expected: 55 passed

# Full regression
python3 -m pytest src/yuantus/meta_engine/tests/ -q
# Expected: 241 passed
```

---

## 验收对照

| 要求 | R1 | R2 |
|---|---|---|
| Items 绑定当前 stage | ❌ 历史 stage 混入 | ✅ `stage_id == ECO.stage_id` |
| Summary 统计口径一致 | ❌ headline vs detail 不同单位 | ✅ 全部从 base query rows 推导 |
| Summary 和 Items 可对账 | ❌ | ✅ 共用 `_base_dashboard_query` |
| by_assignee sum == total | ❌ | ✅ tested |
| escalated <= total | ❌ | ✅ tested |

---

## Known Limitations (non-blocker, accepted)

### 1. HTTP 测试为 contract-level

Dashboard 的 HTTP 测试（`test_summary_200`, `test_items_200_with_filter`）通过 patch service 验证路由注册和响应形状，不是完整数据驱动 E2E。Service 层的数据正确性由 `TestUnifiedStatistics` 和 `TestCurrentStageBinding` 覆盖（使用 `_base_dashboard_query` patch + 受控数据行）。

**后续改进**：如需 E2E 级验证，需引入 SQLite in-memory 测试 DB fixture。

### 2. `by_role` 口径说明

`by_role` 按 **stage 配置的 `approval_roles`** 聚合，不是按 assignee 实际持有的 RBAC 角色聚合。

这是有意的设计选择：
- stage 的 `approval_roles` 代表"这个阶段需要哪些角色参与"，是运营关心的维度
- assignee 的实际角色可能包含多个不相关的角色（如 viewer + engineer），按实际角色聚合会引入噪音
- 如果需要"按 assignee 实际角色"的视图，应作为独立 filter 或新指标补充

---

## Signed Off

Codex review: `DEV_AND_VERIFICATION_P2_3_APPROVAL_DASHBOARD_R2_REVIEW_20260416.md`
Verdict: **通过**
