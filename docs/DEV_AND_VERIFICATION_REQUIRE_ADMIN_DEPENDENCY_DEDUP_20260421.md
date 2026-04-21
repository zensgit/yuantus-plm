# DEV_AND_VERIFICATION_REQUIRE_ADMIN_DEPENDENCY_DEDUP_20260421

## 1. 目标

收敛 `require_admin` 的 4 处重复实现，避免后续 admin 判定语义在 router 间继续分叉。

本轮只做小范围 refactor：

- 不改业务路由
- 不改错误文案
- 不改鉴权边界
- 只把重复的 admin/superuser 判定提到共享依赖层

## 2. 改动范围

运行时代码：

- `src/yuantus/api/dependencies/auth.py`
- `src/yuantus/meta_engine/web/cad_router.py`
- `src/yuantus/meta_engine/web/search_router.py`
- `src/yuantus/meta_engine/web/permission_router.py`
- `src/yuantus/meta_engine/web/schema_router.py`

测试：

- `src/yuantus/meta_engine/tests/test_admin_dependency_dedup.py`

文档：

- `docs/DELIVERY_DOC_INDEX.md`
- 本 MD

## 3. 实现

### 3.1 共享依赖

在 `yuantus.api.dependencies.auth` 新增：

- `user_has_admin_role(user)`
- `require_admin_user(user=Depends(get_current_user))`

判定逻辑统一为：

- `user.is_superuser == True`
- 或 `roles` 中含 `admin`
- 或 `roles` 中含 `superuser`

失败仍返回：

```python
HTTPException(status_code=403, detail="Admin role required")
```

### 3.2 Router 去重

删除以下 4 个 router 内部各自的本地 `require_admin(...)`：

- `cad_router.py`
- `search_router.py`
- `permission_router.py`
- `schema_router.py`

改为统一依赖：

```python
Depends(require_admin_user)
```

## 4. 测试

新增 `test_admin_dependency_dedup.py`，覆盖两类内容：

1. 共享 helper 语义
   - admin 角色放行
   - `is_superuser=True` 放行
   - viewer 返回 `403 / Admin role required`

2. 路由接线
   - `GET /search/status` viewer → `403`
   - `GET /search/status` admin → `200`
   - `GET /meta/permissions` viewer → `403`
   - `POST /meta/item-types` viewer → `403`

同时复跑已有 `test_cad_backend_profile_router.py`，确认 CAD 侧改成共享依赖后不回归。

## 5. 验证

### 5.1 Focused regression

```bash
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_admin_dependency_dedup.py \
  src/yuantus/meta_engine/tests/test_cad_backend_profile_router.py
```

结果：`11 passed in 0.56s`

### 5.2 Doc-index contracts

```bash
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

结果：待本轮执行回填。
结果：`3 passed in 0.02s`

## 6. 非目标

本轮没有处理：

- `esign_router.py` / `release_readiness_router.py` 中的 `_ensure_admin`
- `numbering_service._floor_allocated_value` 下推
- 更大范围的 auth/rbac 统一

这些仍应作为后续 bounded increment 单独推进。

## 7. 风险与结论

这是一个低风险纯收敛 refactor：

- 共享依赖逻辑与原 4 处本地实现保持同一用户面语义
- 没有改变 route path / request / response
- 通过 focused tests 证明 search / permission / schema / cad 四侧都还按原规则工作

结论：可作为下一条小型 cleanup PR 提交。
