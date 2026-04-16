# P2-2: Approval Auto-Assignment, Escalation & Bridge

**Branch:** feature/claude-c43-cutted-parts-throughput
**Date:** 2026-04-15
**Status:** ✅ 241 passed, 0 failed, 0 regressions (9 new tests)

---

## 1. Problem

ECO 审批路由面（`get_approval_routing`）已存在，能显示谁能批、差几票、是否超时。但这只是**只读诊断**——系统不会自动做任何事：

- ❌ 没有自动分派审批人
- ❌ 超时后没有升级机制
- ❌ ECO 专用的 `ECOApproval` 和通用的 `ApprovalRequest` 两套独立、互不相通

---

## 2. Solution

### P2-2a: `auto_assign_stage_approvers(eco_id)`

**触发时机**: ECO 进入新 stage 时（`approve()` 中 `auto_progress` → 下一 stage）

**逻辑**:
1. 读取 `ECOStage.approval_roles`
2. 查询所有 `is_active=True` 的 RBAC 用户
3. 筛选 role 匹配的候选人（`_user_has_stage_role`）
4. 为每个候选人创建 `ECOApproval(status="pending")`
5. 跳过已存在的 approval 记录（幂等）
6. 发送 `eco.approvers_assigned` 通知

```python
svc.auto_assign_stage_approvers("eco-1")
→ {
    "assigned": [
        {"user_id": 10, "username": "alice", "approval_id": "...", "already_existed": False},
    ],
    "approval_request_ids": ["ar-1"]
}
```

### P2-2b: `escalate_overdue_approvals()`

**触发时机**: 定时调用（cron / scheduler）

**逻辑**:
1. 调用已有的 `list_overdue_approvals()` 获取超时 ECO 列表
2. 对每个超时 ECO，查找 `status="pending"` 的 ECOApproval
3. 查找 `is_superuser=True` 的管理员用户
4. 为管理员创建额外的 `ECOApproval(required_role="admin")`
5. 发送 `eco.approval_escalated` 通知

```python
svc.escalate_overdue_approvals()
→ {
    "escalated": 1,
    "items": [{
        "eco_id": "eco-1",
        "stage_id": "stage-1",
        "hours_overdue": 5.0,
        "reassigned": [{
            "original_user_id": 10,
            "escalated_to_user_id": 99,
            "escalated_to_username": "admin-user",
        }]
    }]
}
```

### P2-2c: ApprovalRequest Bridge

**集成在 P2-2a 内部**。每次 auto-assign 时：
1. 调用 `ApprovalService.create_request(entity_type="ECO", entity_id=eco_id, assigned_to_id=user_id)`
2. 调用 `transition_request(ar.id, target_state="pending")`
3. 桥接失败不阻塞 ECO 流程（catch + pass）

这保证两个域的可见性一致：
- `GET /approvals/requests?entity_type=ECO` 能看到 ECO 审批
- `GET /eco/{id}/approvals` 也能看到（ECOApproval 记录）

---

## 3. Wire-Up

`approve()` 方法中，当 stage complete + `auto_progress` 推进到下一 stage 后，自动调用 `auto_assign_stage_approvers(eco.id)`：

```python
# eco_service.py — approve() method, auto-progress branch
if next_stage and stage.auto_progress:
    eco.stage_id = next_stage.id
    eco.state = ECOState.PROGRESS.value
    self._apply_stage_sla(eco, next_stage)
    ...
    self.auto_assign_stage_approvers(eco.id)  # ← P2-2a wire-up
```

---

## 4. Router Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `POST /eco/{eco_id}/auto-assign-approvers` | 手动触发 | 按 stage 角色分派审批人 |
| `POST /eco/approvals/escalate-overdue` | 定时/手动 | 超时审批升级到管理员 |

---

## 5. Files Changed

| File | Change |
|---|---|
| `services/eco_service.py` | +`_resolve_candidate_users`, +`auto_assign_stage_approvers`, +`escalate_overdue_approvals`; `approve()` wire-up |
| `web/eco_router.py` | +2 endpoints (`auto-assign-approvers`, `escalate-overdue`) |
| `tests/test_eco_approval_auto_assign.py` | **新建** — 9 tests |

---

## 6. Test Coverage

| Class | Tests | Covers |
|---|---|---|
| `TestAutoAssignStageApprovers` | 4 | role matching, idempotent skip, none type, notification |
| `TestEscalateOverdueApprovals` | 3 | admin escalation, skip non-overdue, notification |
| `TestApprovalRequestBridge` | 2 | create_request + transition, failure tolerance |
| **Total** | **9** | |

---

## 7. Verification Commands

```bash
# P2-2 tests only
python3 -m pytest src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py -v

# Expected: 9 passed

# Full regression
python3 -m pytest src/yuantus/meta_engine/tests/ -q

# Expected: 241 passed, 0 failed
```

---

## 8. 验收标准

- [x] `auto_assign_stage_approvers` 按 `approval_roles` 分派候选人
- [x] 已存在 approval 记录时幂等跳过
- [x] `approval_type="none"` 不分派
- [x] 分派后发送 `eco.approvers_assigned` 通知
- [x] `escalate_overdue_approvals` 为超时 ECO 增加管理员审批
- [x] 升级后发送 `eco.approval_escalated` 通知
- [x] `auto_assign` 同时写 `ApprovalRequest`（bridge）
- [x] bridge 失败不阻塞 ECO 流程
- [x] `approve()` + `auto_progress` 自动触发下一 stage 分派
- [x] 241 全量通过，0 回归

---

## 9. 下一步

| 步骤 | 内容 |
|---|---|
| **P2-3** | ECO Stage SLA Dashboard 聚合读面（dwell time, throughput, overdue trend） |
| **P2-4** | BOM Diff 可视化 |
| **P2-5** | CAD Viewer 嵌入 |
