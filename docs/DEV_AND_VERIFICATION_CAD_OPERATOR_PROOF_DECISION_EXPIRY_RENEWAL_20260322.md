# CAD Operator Proof Decision Expiry / Renewal Verification

> 日期：`2026-03-22`
> 对应设计：`docs/DESIGN_CAD_OPERATOR_PROOF_DECISION_EXPIRY_RENEWAL_20260322.md`

## 1. 范围

本次验证覆盖 `cad operator proof decision expiry / renewal governance` 的 contract 与文档闭环。

变更文件：

- `src/yuantus/meta_engine/web/cad_router.py`
- `src/yuantus/meta_engine/tests/test_cad_bom_router.py`
- `docs/DESIGN_CAD_OPERATOR_PROOF_DECISION_EXPIRY_RENEWAL_20260322.md`
- `docs/DEV_AND_VERIFICATION_CAD_OPERATOR_PROOF_DECISION_EXPIRY_RENEWAL_20260322.md`
- `docs/RUNBOOK_CAD_BOM_OPERATIONS.md`
- `docs/DEVELOPMENT_DIRECTION_OPERATIONS_DETAIL_SURPASS_20260321.md`
- `docs/REFERENCE_GROUNDED_SURPASS_BACKLOG_20260321.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 2. Functional Checks

### 2.1 Decision validity is explicit in proof surface

- `/proof` 回显 `decision_validity_status`、`decision_renewal_required`、`decision_renewal_recommended`。
- `missing_expiry` 仅在 `waived` 但无 `expires_at` 时出现。
- 缺失或过期时 `requires_operator_decision=true`。

### 2.2 Expiration window is surfaced as recommendation

- 到期前 72 小时返回 `expiring` 与推荐续签动作。
- 过期返回 `expired` 与 required 续签动作。

### 2.3 Renewal is explicit and auditable

- 续签使用 `renew_from_decision_id`。
- 续签要求 `expires_at` 递增。
- `audit_action` 在历史链路中区分初始与续签动作。

### 2.4 Export and proof manifest remain machine-readable

- `proof_manifest` 与 `operator_proof` 中同时保留 validity 与 renewal 字段。
- `proof_decisions.csv` 保留新增治理列。
- `proof_decisions.json` 能追溯 `renewed_from_decision_id`。

## 3. Test Inventory

### 3.1 Router Contracts

关注测试（同一文件）：

- `test_get_cad_operator_proof_returns_active_waiver_for_current_fingerprint`
- `test_get_cad_operator_proof_marks_expired_waiver_for_renewal`
- `test_get_cad_operator_proof_decisions_returns_current_entries`
- `test_record_cad_operator_proof_waiver_requires_expires_at`
- `test_record_cad_operator_proof_decision_renewal_logs_renewed_action`
- `test_export_cad_bom_bundle_zip_includes_summary_review_and_history`
- `test_export_cad_bom_bundle_json_supports_job_fallback`

### 3.2 Runbook / Index contracts

要求在文档回归中覆盖：

- `docs/RUNBOOK_CAD_BOM_OPERATIONS.md` 包含 `decision_validity_status`、续签动作、示例调用。
- `docs/DEVELOPMENT_DIRECTION_OPERATIONS_DETAIL_SURPASS_20260321.md` 标注该治理已落地并给出后续增量。
- `docs/REFERENCE_GROUNDED_SURPASS_BACKLOG_20260321.md` 将 `cad proof decision expiry / renewal` 标为已完成。
- `docs/DELIVERY_DOC_INDEX.md` 包含 design/verification 两条入口。

## 4. 命令清单（待执行）

```bash
python3 -m pytest -q src/yuantus/meta_engine/tests/test_cad_bom_router.py
```

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_bom_router.py \
  src/yuantus/meta_engine/tests/test_cad_bom_import_service.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py
```

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_doc_index_sorting.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_all_sections_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_core_required_entries_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbook_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py
```

## 5. Verification Judgment

decision expiry / renewal governance 已经把 `cad operator proof` 从一次性决策变成「可失效 + 可续签 + 可交接」的治理面。

剩余风险与下一步：

- 决策窗口目前是固定常量，尚未外部配置化。
- 续签动作还未接入自动提醒/事件系统。
- 需要进一步补 `proof decision consumer adoption evidence`（UI/support 证明该合同被消费）。
