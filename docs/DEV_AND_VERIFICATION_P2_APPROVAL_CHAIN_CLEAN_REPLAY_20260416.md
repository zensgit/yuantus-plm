# Dev & Verification: P2 Approval Chain Clean Replay

**Date:** 2026-04-16
**Scope:** 从干净 `origin/main` 基线重放 `P2-2a / P2-2b / P2-3 / P2-3.1` 的最小 clean branch，显式排除 `P1 CAD`、`plm_workspace`、AML handoff 等无关改动。

---

## Why This Replay Exists

原分支 `feature/claude-c43-cutted-parts-throughput` 相对 `main` 已明显陈旧，并把多条无关工作流打包到了同一个 PR 中。

因此这次处理方式改为：

- 从干净 `origin/main` 建新分支
- 只迁移 `P2 approval chain` 运行时代码、测试和核心交付文档
- 单独补观察期模板和索引

---

## Replayed Scope

### Runtime

- `src/yuantus/meta_engine/services/eco_service.py`
- `src/yuantus/meta_engine/web/eco_router.py`

### Tests

- `src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py`
- `src/yuantus/meta_engine/tests/test_eco_approval_escalation.py`
- `src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py`
- `src/yuantus/meta_engine/tests/test_eco_approval_dashboard_export.py`
- `src/yuantus/meta_engine/tests/test_eco_approval_audit.py`

### Docs

- `docs/DEV_AND_VERIFICATION_P2_2_APPROVAL_CHAIN_DELIVERY.md`
- `docs/DEV_AND_VERIFICATION_P2_2a_APPROVAL_AUTO_ASSIGN.md`
- `docs/DEV_AND_VERIFICATION_P2_2b_OVERDUE_ESCALATION.md`
- `docs/DEV_AND_VERIFICATION_P2_3_SLA_DASHBOARD.md`
- `docs/DEV_AND_VERIFICATION_P2_3_1_PR1_DASHBOARD_FILTERS.md`
- `docs/DEV_AND_VERIFICATION_P2_3_1_PR2_DASHBOARD_EXPORT.md`
- `docs/DEV_AND_VERIFICATION_P2_3_1_PR3_APPROVAL_OPS_AUDIT.md`
- `docs/P2_OPS_RUNBOOK.md`
- `docs/P2_OPS_OBSERVATION_TEMPLATE.md`
- `docs/DEV_AND_VERIFICATION_P2_OPS_OBSERVATION_TEMPLATE_20260416.md`
- `docs/DELIVERY_DOC_INDEX.md`

### Explicitly Excluded

- `P1 CAD` checkin / queue / worker binding runtime
- version/file-lock runtime
- `plm_workspace` frontend / Playwright slices
- AML metadata handoff docs
- old oversized PR-only closeout docs unrelated to P2 approval chain replay

---

## Verification

### Focused approval-chain regression

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard_export.py \
  src/yuantus/meta_engine/tests/test_eco_approval_audit.py
```

### Syntax smoke

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/services/eco_service.py \
  src/yuantus/meta_engine/web/eco_router.py
```

### Docs alignment

- `P2_OPS_RUNBOOK` and `P2_OPS_OBSERVATION_TEMPLATE` were manually checked for endpoint references and metric alignment
- `DELIVERY_DOC_INDEX` was updated to include the replayed P2 delivery docs and observation docs

---

## Result

This clean replay branch is intended to be the new merge candidate for the `P2 approval chain` work, replacing the oversized mixed-scope reference branch.
