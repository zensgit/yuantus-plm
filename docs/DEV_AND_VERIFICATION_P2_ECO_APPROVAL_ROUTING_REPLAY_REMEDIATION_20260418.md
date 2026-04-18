# P2 ECO Approval Routing Replay Remediation

日期：2026-04-18
接管对象：`19bdc47 feat(eco): add approval routing summary surface`

## 目标

把已经被文档和测试定义、但当前 `main` 实现缺失的 `approval-routing` runtime surface 补回主线，并完成最小回归验证。

## 背景

当前仓库存在一个明确失配：

- `docs/DEV_AND_VERIFICATION_P2_ECO_APPROVAL_ROUTING_MVP_20260415.md` 记录了：
  - `ECOApprovalService.get_approval_routing(...)`
  - `GET /api/v1/eco/{eco_id}/approval-routing`
- `src/yuantus/meta_engine/tests/test_eco_approval_routing.py` 也已经把这条服务/路由契约写成 focused tests
- 但当前 `main` 实际上缺少：
  - `ECOApprovalService.get_approval_routing(...)`
  - `GET /api/v1/eco/{eco_id}/approval-routing`

本地直接执行：

```bash
python3 -m pytest -q src/yuantus/meta_engine/tests/test_eco_approval_routing.py
```

结果是：

```text
4 failed
```

失败原因全部直接指向实现缺失：

- `AttributeError: 'ECOApprovalService' object has no attribute 'get_approval_routing'`
- `/api/v1/eco/{eco_id}/approval-routing` 返回 `404`

## Replay 范围

- `src/yuantus/meta_engine/services/eco_service.py`
- `src/yuantus/meta_engine/web/eco_router.py`
- `docs/DEV_AND_VERIFICATION_P2_ECO_APPROVAL_ROUTING_REPLAY_REMEDIATION_20260418.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 执行过程

从当前主线开 clean replay 分支：

```bash
git switch -c feature/p2-approval-routing-replay-20260418
```

随后只摘取 `19bdc47` 里和当前主线仍然缺失的最小 runtime 行为，不带入其它 approval-chain / dashboard / observation 变更。

### 1. 服务层

在 `ECOApprovalService` 中补回：

- `_resolve_stage_candidate_users(stage)`
- `get_approval_routing(eco_id)`

行为包括：

- 根据当前 stage 的 `approval_roles` 解析 active candidate users
- 汇总当前 stage 的 approval progress：
  - `approved_count`
  - `rejected_count`
  - `remaining_required`
  - `stage_complete`
- 输出显式 routing summary：
  - `routing_mode`
  - `routing_ready`
  - `routing_gap`
  - `candidate_approvers`
  - `candidate_approver_count`

### 2. 路由层

在 `eco_router.py` 补回：

```text
GET /api/v1/eco/{eco_id}/approval-routing
```

路由行为：

- 先做 `read ECO` 权限检查
- 调用 `ECOApprovalService.get_approval_routing(...)`
- `ValueError("ECO not found")` 映射到 `404`
- 其它输入型错误映射到 `400`

## 验证

### 1. 先验证缺口被补齐

```bash
python3 -m pytest -q src/yuantus/meta_engine/tests/test_eco_approval_routing.py
```

结果：

```text
4 passed, 1 warning in 2.58s
```

### 2. 最小 approval-routing / diagnostics / hook 回归集

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_routing.py \
  src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py \
  src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py
```

结果：

```text
42 passed, 1 warning in 11.23s
```

### 3. 语法检查

```bash
python3 -m py_compile \
  src/yuantus/meta_engine/services/eco_service.py \
  src/yuantus/meta_engine/web/eco_router.py
```

结果：通过。

### 4. 文档索引 contracts

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py
```

结果：

```text
5 passed in 0.02s
```

## 结论

- 当前 `main` 现在重新具备 `approval-routing` 这条 canonical ECO read surface
- 4 月 15 日的开发验证文档、focused tests 和当前 runtime 实现重新对齐
- 这轮只补回缺失的最小 runtime 行为，没有把更大的 approval-chain / observation 变更重新带进来
