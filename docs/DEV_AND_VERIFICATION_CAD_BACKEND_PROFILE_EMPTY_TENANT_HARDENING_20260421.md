# DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_EMPTY_TENANT_HARDENING_20260421

## 1. 目标

补齐 `cad_pipeline_tasks.py::_cad_backend_profile_resolution()` 的输入卫生缺口。

`PR #288` 的 hardening 已经保证 **缺失** `tenant_id` 会 fail-loud，但当前实现只拦 `ctx.tenant_id is None`。如果 job payload 或 request context 带入空串/纯空白串，代码会把它当成有效租户继续往下走，导致 profile resolution 以脏 tenant scope 执行。

本轮目标：**把 `None`、空串、纯空白串统一视为无效 tenant context，并保持错误语义不变（`JobFatalError`）**。

## 2. 改动范围

仅触碰以下 4 处：

1. `src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py`
2. `src/yuantus/meta_engine/tests/test_cad_backend_profile.py`
3. `docs/DELIVERY_DOC_INDEX.md`
4. 本 MD + 两份上一轮遗留 merge MD

未触碰：

- `numbering_service.py`
- `latest_released_guard.py`
- 任一 router / migration / GraphQL 路径

## 3. 实现

### 3.1 Runtime hardening

原实现：

```python
if ctx.tenant_id is None:
    raise JobFatalError(...)
```

现实现：

```python
tenant_id = (ctx.tenant_id or "").strip()
if not tenant_id:
    raise JobFatalError(...)
```

效果：

- `None` → fail-loud
- `""` → fail-loud
- `"   "` → fail-loud
- `" tenant-1 "` → 归一化为 `"tenant-1"` 再进入 `CadBackendProfileService.resolve(...)`

这让 worker/job payload 的租户上下文在进入 profile resolution 前就完成最小清洗，不再把脏 scope 传给后续服务层。

### 3.2 测试

在 `test_cad_backend_profile.py` 补了两类覆盖：

1. 参数化失败路径：`tenant_id in [None, "", "   "]` 全部抛 `JobFatalError`
2. 正向清洗路径：`" tenant-1 "` 会被 strip 后再传给 `CadBackendProfileService.resolve(...)`

## 4. 文档收口

本轮同时把上一轮遗留、尚未进任何 PR 的两份 merge 执行记录一并带上：

- `docs/DEV_AND_VERIFICATION_PR294_AUTO_NUMBERING_MERGE_20260421.md`
- `docs/DEV_AND_VERIFICATION_PR300_DOC_ARCHIVE_MERGE_20260421.md`

并补齐 `docs/DELIVERY_DOC_INDEX.md` 索引，避免 completeness contract 挂红。

## 5. 验证

### 5.1 CAD backend profile focused tests

```bash
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_backend_profile.py \
  src/yuantus/meta_engine/tests/test_cad_backend_profile_service.py \
  src/yuantus/meta_engine/tests/test_cad_backend_profile_router.py \
  src/yuantus/meta_engine/tests/test_cad_capabilities_router.py
```

结果：`26 passed in 0.55s`

### 5.2 Doc-index contract tests

```bash
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

结果：`3 passed in 0.02s`

## 6. 结论

这是一个极小但必要的输入卫生补丁：

- 不改变 profile resolution 的对外语义
- 不扩大 CAD backend profile 的 scope
- 直接堵住 `tenant_id=""` / `"   "` 的漏网路径
- 顺手收走 `PR294` / `PR300` 的本地 merge 归档文档

## 7. 下一步

若本轮 focused regression 通过，下一条同侧小增量可以继续考虑：

1. `require_admin` 4 份拷贝去重
2. `numbering_service._floor_allocated_value` 的 DB 下推

这两条都独立于本补丁，可后续单开 bounded increment。
