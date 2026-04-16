# Dev & Verification: P2 Approval Chain PR220 Contracts Remediation

**Date:** 2026-04-16
**PR:** `#220`
**Scope:** 修复 clean replay PR 首轮 CI 中 `contracts` 失败的问题。

---

## Problem

`contracts` job failed on:

- `test_dev_and_verification_doc_index_sorting_contracts.py`

Root cause:

- `docs/DELIVERY_DOC_INDEX.md` 中新增的 `P2` 文档条目没有完全按 path 字典序排序
- `docs/P2_OPS_OBSERVATION_TEMPLATE.md`
- `docs/P2_OPS_RUNBOOK.md`
  这两条被放在了 `## Development & Verification` 段中过早的位置

---

## Fix

Adjusted `docs/DELIVERY_DOC_INDEX.md` ordering so that:

- `DEV_AND_VERIFICATION_P2_*` entries stay in the sorted `docs/DEV_AND_VERIFICATION_*` block
- `docs/P2_OPS_OBSERVATION_TEMPLATE.md`
- `docs/P2_OPS_RUNBOOK.md`
  move to the correct sorted position after:

- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`

and before:

- `docs/PERFORMANCE_REPORTS/...`

---

## Verification

### Doc index contracts

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py
```

Result:

- `2 passed`

### Approval-chain focused regression re-run

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard_export.py \
  src/yuantus/meta_engine/tests/test_eco_approval_audit.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  -k "audit or dashboard or export or escalat or auto_assign or approval_routing or entity_type or request_create_and_list"
```

Result:

- `99 passed, 29 deselected, 1 warning`

---

## Result

`contracts` failure was reduced to a doc-index sorting issue and fixed locally.

The clean replay branch remains focused on:

- `P2-2a`
- `P2-2b`
- `P2-3`
- `P2-3.1`
- `ops runbook + observation template`
