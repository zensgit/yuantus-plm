# Dev & Verification: P2 Dev Observation Startup Checklist

**Date:** 2026-04-16
**Scope:** 为开发环境的 `P2` 运营观察期补一份启动 checklist。

---

## Delivered

- 新增启动文档：
  - `docs/P2_DEV_OBSERVATION_STARTUP_CHECKLIST.md`
- 更新交付索引：
  - `docs/DELIVERY_DOC_INDEX.md`

---

## Checklist Coverage

这份 checklist 覆盖了开发环境观察期启动的最小闭环：

1. 环境准备
2. 认证准备
3. 端点 smoke
4. 样本数据准备
5. 基线观察
6. 运营事件演练
7. 每日 / 每周节奏
8. 退出条件

它和以下文档保持对齐：

- `docs/P2_OPS_RUNBOOK.md`
- `docs/P2_OPS_OBSERVATION_TEMPLATE.md`

---

## Verification

- 人工核对 checklist 与 runbook / observation template 的字段和流程一致
- 运行 doc-index contracts：

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py
```

---

## Result

当前 `P2` 阶段除了 runbook 和 observation template 外，已补齐开发环境观察期的启动文档，可以直接用于：

- dev 环境值班演练
- 周度复盘
- `P2-4` 启动前的证据沉淀
