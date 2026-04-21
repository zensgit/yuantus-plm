# DEV / Verification - PR294 Effectivity Router Remediation

日期：2026-04-21

## 目标

补齐 PR `#294` 剩余的一个真实 API 语义漏洞：

- `EffectivityService.create_effectivity()` 在 latest-released guard 期间可能抛出 `ValueError`
- `effectivity_router.py` 之前只映射了 `NotLatestReleasedError -> 409`
- 缺失 target 的场景会冒成 `500`

本轮只修这个 router 映射问题，并把上一轮尚未入库的 `PR300` doc archive merge 记录一并带进当前 PR。

## 改动

### 1. Effectivity router 异常映射

文件：

- `src/yuantus/meta_engine/web/effectivity_router.py`

改动：

- 保留原有 `NotLatestReleasedError -> 409`
- 新增 `ValueError -> 404`
- 两条异常路径都先执行 `db.rollback()`

结果：

- latest-released 语义冲突仍返回 `409`
- target 缺失不再冒 `500`

### 2. Focused router test

文件：

- `src/yuantus/meta_engine/tests/test_latest_released_guard_router.py`

新增：

- `test_effectivity_create_maps_missing_target_value_error_to_404`

覆盖点：

- service 抛 `ValueError("Effectivity target ... not found")`
- router 返回 `404`
- `db.rollback()` 被调用
- `db.commit()` 不被调用

### 3. 同步收走 PR300 merge MD

文件：

- `docs/DEV_AND_VERIFICATION_PR300_DOC_ARCHIVE_MERGE_20260421.md`

说明：

- 这是主仓库上一轮未提交的 merge 归档文档
- 本轮与 `#294` follow-up 一起收走，避免再开单独 doc-only PR

## 验证

执行命令：

```bash
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_latest_released_guard_router.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

结果：

- `8 passed in 0.60s`

## 边界

- 未处理 `utcnow` / `expire_all()` / migration timestamp defaults
- 未调整 GraphQL brittle contract tests
- 未修改 numbering / latest-released 的核心业务逻辑
- 未改变 PR `#294` 其余 review 结论

## 结论

本轮是一个极小 follow-up：

- 修掉 `effectivity_router.py` 的真实 `500` 风险
- 补上对应 focused test
- 顺手收走 `PR300` merge 归档文档
