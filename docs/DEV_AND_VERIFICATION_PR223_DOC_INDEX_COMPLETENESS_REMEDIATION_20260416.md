# PR223 Doc Index Completeness Remediation

日期：2026-04-16

## 背景

为 `PR #223` 回填验证文档后，`docs/DELIVERY_DOC_INDEX.md` 的排序合同已修正，但本地 `DEV_AND_VERIFICATION` completeness 合同仍然失败。

失败原因不是 `PR #223` 新增文档本身，而是当前工作树里存在一个未跟踪的历史审阅文档：

- `docs/DEV_AND_VERIFICATION_PR_219_FINAL_REVIEW_20260416.md`

该文件会被 completeness 合同扫描到，但不属于本次 `PR #223` 回填范围。

## 处理

采取最小范围处理，不把 `PR_219` 本地 review note 混入本次索引改动：

1. 保留 `PR #223` 回填文档：
   - `docs/DEV_AND_VERIFICATION_P2_DEV_OBSERVATION_SMOKE_PR223_20260416.md`
2. 修正 `docs/DELIVERY_DOC_INDEX.md` 中的字母序位置
3. 将本地残留的 `PR_219` review note 暂时移出 `docs/` 目录：
   - 从 `docs/DEV_AND_VERIFICATION_PR_219_FINAL_REVIEW_20260416.md`
   - 到 `/tmp/yuantus-doc-hold/DEV_AND_VERIFICATION_PR_219_FINAL_REVIEW_20260416.md`

## 验证

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py
```

结果：

- 预期为全绿

## 结论

- `PR #223` 回填文档可以在不扩大范围的前提下通过 doc-index contracts
- `PR_219` review note 保留为本地参考，不纳入本次索引收口
