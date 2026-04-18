# P2 ECO Bind Product Main Chain Replay Remediation

日期：2026-04-18
接管对象：`b9c60ad feat(eco): add bind-product endpoint and fix PUT to use service layer (PR-1)`

## 目标

把当前 `main` 已经被测试写死、但 runtime 实现缺失的 ECO 主链绑定能力补回主线，并完成最小回归验证。

## 背景

当前主线存在两条直接破坏 ECO 主链的缺口：

- `ECOService.bind_product(...)` 缺失，导致 `create_eco -> bind_product -> new_revision -> approve -> apply` 这条主链在服务层中断
- `ECOService.update_eco(...)` 没有字段白名单，仍然允许 `product_id` 通过普通更新入口写入，违反 `bind-product` 作为唯一绑定入口的约束

本地直接执行：

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py \
  src/yuantus/meta_engine/tests/test_eco_main_chain_e2e.py
```

结果：

```text
2 failed, 39 passed, 1 warning in 5.19s
```

两处失败分别是：

- `AttributeError: 'ECOService' object has no attribute 'bind_product'`
- `update_eco({"product_id": ...})` 未抛出 `cannot be updated via update_eco`

## Replay 范围

- `src/yuantus/meta_engine/services/eco_service.py`
- `src/yuantus/meta_engine/web/eco_router.py`
- `docs/DEV_AND_VERIFICATION_P2_ECO_BIND_PRODUCT_MAIN_CHAIN_REPLAY_REMEDIATION_20260418.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 执行过程

从当前主线开 clean replay 分支：

```bash
git switch -c feature/eco-bind-product-main-chain-replay-20260418
```

随后只补回主链缺失的最小 runtime 行为，不带入其它 ECO 收敛项。

### 1. 服务层

在 `ECOService` 中恢复：

- `_UPDATE_ALLOWED_FIELDS = {"name", "description", "priority", "effectivity_date"}`
- `update_eco(...)` 的状态守卫：
  - 只允许 `draft` / `progress`
- `update_eco(...)` 的字段白名单：
  - 显式拒绝 `product_id`、`state` 等非白名单字段
- `bind_product(...)`

`bind_product(...)` 的恢复行为包括：

- 绑定前做 `bind_product` 字段级权限检查
- 仅允许 `draft` / `progress`
- 同产品重复绑定幂等
- 已绑定其它产品时拒绝 rebind
- 已存在 `target_version_id` 时拒绝重新绑定
- 绑定前校验产品存在
- `create_target_revision=True` 时才联动创建新修订

### 2. 路由层

在 `eco_router.py` 中补回和收口：

- `POST /api/v1/eco/{eco_id}/bind-product`
- `PUT /api/v1/eco/{eco_id}` 改为统一走 `ECOService.update_eco(...)`

路由层行为调整后：

- `bind-product` 成为显式 canonical 绑定入口
- `PUT` 不再直接改模型对象
- 空更新请求会返回 `400: No fields provided for update`
- 服务层 `ValueError` 统一映射到 `400`

## 验证

### 1. 直接命中修复面

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_bind_product.py \
  src/yuantus/meta_engine/tests/test_eco_main_chain_e2e.py
```

结果：

```text
21 passed in 0.25s
```

### 2. 兼容路由回归

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ecm_compat_router.py
```

结果：

```text
14 passed, 1 warning in 3.08s
```

### 3. ECO 审批链最小回归集

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py \
  src/yuantus/meta_engine/tests/test_eco_main_chain_e2e.py
```

结果：

```text
41 passed, 1 warning in 4.52s
```

### 4. 语法检查

```bash
python3 -m py_compile \
  src/yuantus/meta_engine/services/eco_service.py \
  src/yuantus/meta_engine/web/eco_router.py
```

结果：通过。

### 5. 文档索引 contracts

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

- 当前 `main` 重新具备 `bind_product` 这条 ECO 主链能力
- `product_id` 再次被收口到 `bind-product` 这个唯一绑定入口
- `update_eco` 与主链 e2e / compat tests / 审批链最小回归集重新对齐
