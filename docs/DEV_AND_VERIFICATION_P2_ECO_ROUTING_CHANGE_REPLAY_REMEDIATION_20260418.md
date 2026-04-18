# P2 ECO Routing Change Replay Remediation

日期：2026-04-18
接管对象：

- `8cbc50d feat(eco): add ECO routing change tracking with rebase conflict detection (P0-3)`
- `43b1888 fix(eco): match routing changes across cloned operations`

## 目标

把当前 `main` 已经被 `test_eco_routing_change.py` 写成契约、但 runtime 实现缺失的 ECO routing change 能力补回主线，并完成最小回归验证。

## 背景

在当前主线扩大到整个 `eco/ecm` 测试面后，出现一组明确收敛到 `routing change` 的失败：

```bash
PYTHONPATH=src python3 -m pytest -q \
  $(find src/yuantus/meta_engine/tests -maxdepth 1 \( -name 'test_eco_*.py' -o -name 'test_ecm_*.py' \) | sort)
```

结果：

```text
15 failed, 189 passed, 1 warning in 29.90s
```

失败原因集中为两类：

- `ECOService` 侧缺失 routing change 相关依赖/实现，测试连 `yuantus.meta_engine.services.eco_service.Operation` 都 patch 不上
- `eco_router.py` 中缺少：
  - `GET /api/v1/eco/{eco_id}/routing-changes`
  - `POST /api/v1/eco/{eco_id}/compute-routing-changes`

对应失败信号包括：

- `AttributeError: ... eco_service ... does not have the attribute 'Operation'`
- `/api/v1/eco/eco-1/routing-changes` 返回 `404`
- `/api/v1/eco/eco-1/compute-routing-changes` 返回 `404`

## Replay 范围

- `src/yuantus/meta_engine/services/eco_service.py`
- `src/yuantus/meta_engine/web/eco_router.py`
- `docs/DEV_AND_VERIFICATION_P2_ECO_ROUTING_CHANGE_REPLAY_REMEDIATION_20260418.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 执行过程

从当前主线开 clean replay 分支：

```bash
git switch -c feature/eco-routing-change-replay-20260418
```

随后只补回 `routing change` 这条最小 runtime 行为，不带入其它 manufacturing / routing 扩展面。

### 1. 服务层

在 `ECOService` 中补回：

- `Operation` / `Routing` / `ECORoutingChange` 依赖导入
- `_operation_snapshot(...)`
- `_operation_match_key(...)`
- `_get_operations_for_product_version(...)`
- `get_routing_changes(...)`
- `compute_routing_changes(...)`
- `_create_eco_routing_change(...)`
- `_detect_routing_rebase_conflicts(...)`

恢复后的关键行为：

- `compute_routing_changes(...)` 会校验：
  - `eco` 存在
  - `product_id` 存在
  - `source_version_id` / `target_version_id` 存在
- 每次重算前先清掉该 ECO 旧的 `ECORoutingChange` 记录
- source/target operation 匹配采用 `_operation_match_key(...)`
  - 优先用 `operation_number`
  - 没有时回退到 `id`
- 因此 clone/copy 流程里 `Operation.id` 变化、但 `operation_number` 一致的 operation，会被识别为同一条业务操作
- 产出三类变化：
  - `add`
  - `remove`
  - `update`
- routing rebase conflict 会并入现有 `detect_rebase_conflicts(...)`，并以 `ECORoutingChange(conflict=True)` 落表

### 2. 路由层

在 `eco_router.py` 中补回：

- `GET /api/v1/eco/{eco_id}/routing-changes`
- `POST /api/v1/eco/{eco_id}/compute-routing-changes`

路由行为：

- `routing-changes`：
  - ECO 不存在返回 `404`
  - 否则返回 `service.get_routing_changes(...).to_dict()` 列表
- `compute-routing-changes`：
  - 调用 `service.compute_routing_changes(..., compare_mode=...)`
  - 成功后 `db.commit()`
  - `ValueError` 映射为 `400`
  - 其它异常 `rollback` 后映射为 `500`

## 验证

### 1. 直接命中 routing change 修复面

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_routing_change.py
```

结果：

```text
18 passed, 1 warning in 3.67s
```

### 2. ECO / ECM 全测试面回归

```bash
PYTHONPATH=src python3 -m pytest -q \
  $(find src/yuantus/meta_engine/tests -maxdepth 1 \( -name 'test_eco_*.py' -o -name 'test_ecm_*.py' \) | sort)
```

结果：

```text
204 passed, 1 warning in 29.56s
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
5 passed in 0.01s
```

## 结论

- 当前 `main` 重新具备 ECO routing change tracking 这条 runtime surface
- clone 后 operation `id` 变化的场景，重新能按 `operation_number` 稳定匹配
- routing diff、routing rebase conflict 和对应 API 入口，已与现有 focused tests 重新对齐
