# CAD Operator Proof Acknowledgement / Waiver Verification

> 日期：`2026-03-22`
> 对应设计：`docs/DESIGN_CAD_OPERATOR_PROOF_ACKNOWLEDGEMENT_WAIVER_20260322.md`

## 1. Scope

本次验证覆盖三类结果：

1. 新的 proof decision contract 是否成立
2. unified proof / export bundle 是否回显 decision trail
3. 文档与 runbook 是否和代码保持一致

## 2. Changed Files

代码：

- `src/yuantus/meta_engine/web/cad_router.py`
- `src/yuantus/meta_engine/tests/test_cad_bom_router.py`

文档：

- `docs/DESIGN_CAD_OPERATOR_PROOF_ACKNOWLEDGEMENT_WAIVER_20260322.md`
- `docs/DEV_AND_VERIFICATION_CAD_OPERATOR_PROOF_ACKNOWLEDGEMENT_WAIVER_20260322.md`
- `docs/RUNBOOK_CAD_BOM_OPERATIONS.md`
- `docs/DEVELOPMENT_DIRECTION_OPERATIONS_DETAIL_SURPASS_20260321.md`
- `docs/REFERENCE_GROUNDED_SURPASS_BACKLOG_20260321.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Functional Checks

### 3.1 Proof surface exposes decision governance

验证点：

- `/proof` 在 degraded/mismatch 场景下返回 `decision_status=open`
- `requires_operator_decision=true`
- `proof_decisions=[]`
- `active_decision=null`

对应测试：

- `test_get_cad_operator_proof_returns_linked_asset_quality_and_mismatch_surface`

### 3.2 Current-fingerprint waiver is surfaced as active decision

验证点：

- history 中的 `cad_operator_proof_waived` 被 `/proof` 结构化回读
- `operator_proof.decision_status=waived`
- `active_decision.covers_current_proof=true`

对应测试：

- `test_get_cad_operator_proof_returns_active_waiver_for_current_fingerprint`

### 3.3 POST decision persists current proof snapshot

验证点：

- `POST /proof/decisions` 成功写入 `CadChangeLog`
- payload 中保存 `proof_fingerprint`
- payload 中保存 `proof_status`
- payload 中保存 `proof_decisions_url`

对应测试：

- `test_record_cad_operator_proof_decision_logs_current_snapshot`

### 3.4 Export bundle includes decision trail

验证点：

- ZIP bundle 新增 `active_decision.json`
- ZIP bundle 新增 `proof_decisions.json`
- ZIP bundle 新增 `proof_decisions.csv`
- `proof_manifest.json` 包含 `decision_status` / `active_decision_status`
- `README.txt` 包含 `proof_decisions_url` / `decision_status`

对应测试：

- `test_export_cad_bom_bundle_zip_includes_summary_review_and_history`
- `test_export_cad_bom_bundle_json_supports_job_fallback`

## 4. Commands

### 4.1 Syntax

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-proof-ack-pycompile \
python3 -m py_compile \
  src/yuantus/meta_engine/web/cad_router.py \
  src/yuantus/meta_engine/tests/test_cad_bom_router.py
```

结果：

- pass

### 4.2 Router contracts

```bash
python3 -m pytest src/yuantus/meta_engine/tests/test_cad_bom_router.py -vv -x
```

结果：

- `12 passed, 2 warnings in 6.06s`

### 4.3 CAD targeted regression pack

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_bom_router.py \
  src/yuantus/meta_engine/tests/test_cad_bom_import_service.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py
```

结果：

- `49 passed, 2 warnings in 13.08s`

### 4.4 Delivery-doc-index / runbook contracts

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

结果：

- `9 passed in 0.09s`

### 4.5 Full stack

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-proof-ack-full \
PYTEST_ADDOPTS='-p no:cacheprovider' \
scripts/verify_odoo18_plm_stack.sh full
```

结果：

- `739 passed, 253 warnings in 19.07s`
- trailing script status: `[verify_odoo18_plm_stack] PASS`

### 4.6 Diff hygiene

```bash
git diff --check
```

结果：

- pass

## 5. Verification Judgment

这次增量验证通过的关键不只是“新增 endpoint 可用”，而是：

- technical proof 和 operator decision 之间有稳定 fingerprint 绑定
- decision trail 能被 `/proof` 回读
- decision trail 能进入 export bundle
- runbook 已经明确 operator 应该如何读取、记录、导出 decision

这使得 Yuantus 在 `CAD/BOM/import/export/review` 这一条线上，不再只是
“能展示问题”，而是已经具备比参考实现更强的审计与交接语义。
