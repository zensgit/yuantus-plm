# Delivery Doc Index Cleanup

日期：2026-04-16

## 目标

收口 `docs/DELIVERY_DOC_INDEX.md` 中 `## Development & Verification` 段的存量问题，使其重新满足仓库 contract：

- 路径唯一
- 路径按字典序稳定排序
- 所有 `docs/DEV_AND_VERIFICATION_*.md` 都被索引

## 本次改动

- 重建 `## Development & Verification` 段
- 删除重复的 parallel bootstrap 条目
- 补齐此前缺失的 P2 approval review 文档、P2 dashboard review 文档、runbook review 文档、parallel review 文档
- 保留现有 `Core`、`Ops & Deployment`、`Product/UI Integration`、`Verification Reports`、`Optional`、`External` 章节结构不变

## 结果

- `Development & Verification` 段从原先的重复/漏挂状态收口为唯一路径列表
- `docs/P2_DEV_OBSERVATION_STARTUP_CHECKLIST.md`
- `docs/P2_OPS_OBSERVATION_TEMPLATE.md`
- 以及对应验证文档都已稳定挂入索引

## 验证

执行：

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py
```

结果：

- `2 passed`

## 备注

本次为 docs-only 清理，不涉及业务代码。
