# Yuantus Odoo18 PLM Parallel Execution Verification

## Increment 2026-03-18 C6-Integration-And-P2A-Workorder-Locale

### Touched Areas
- `src/yuantus/api/app.py`
- `src/yuantus/meta_engine/web/locale_router.py`
- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `src/yuantus/meta_engine/tests/test_locale_router.py`
- `src/yuantus/meta_engine/tests/test_locale_service.py`
- `src/yuantus/meta_engine/tests/test_report_locale_service.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/web/locale_router.py \
  src/yuantus/meta_engine/services/parallel_tasks_service.py \
  src/yuantus/meta_engine/web/parallel_tasks_router.py \
  src/yuantus/meta_engine/tests/test_locale_router.py \
  src/yuantus/meta_engine/tests/test_locale_service.py \
  src/yuantus/meta_engine/tests/test_report_locale_service.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_locale_service.py \
  src/yuantus/meta_engine/tests/test_report_locale_service.py \
  src/yuantus/meta_engine/tests/test_locale_router.py
```

```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_services.py \
  -k 'workorder_doc_pack_supports_inherited_links_and_zip_export or workorder_doc_pack_includes_locale_profile_context'
```

```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_router.py \
  -k 'workorder_doc_export_json_includes_export_meta or workorder_doc_export_passes_locale_query_contract or workorder_doc_export_pdf_returns_pdf_payload'
```

```bash
git diff --check
```

### Actual Results
- `py_compile`: passed
- `test_locale_service.py + test_report_locale_service.py + test_locale_router.py`:
  - `22 passed, 3 warnings`
- `test_parallel_tasks_services.py` targeted locale export pack:
  - `2 passed, 54 deselected`
- `test_parallel_tasks_router.py` targeted locale export endpoints:
  - `3 passed, 113 deselected, 4 warnings`
- combined locale/export pack:
  - `28 passed, 166 deselected, 7 warnings`
- `git diff --check`: passed

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack

### Residual Risks
- locale 仅接入了 `workorder-docs/export`
- `C6` 目前只在本分支集成，还未合并回主线
- `C7` 仍由 Claude 在独立分支继续推进，尚未和本分支联调

## Increment 2026-03-18 P2A-Parallel-Ops-Locale

### Touched Areas
- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/services/parallel_tasks_service.py \
  src/yuantus/meta_engine/web/parallel_tasks_router.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py
```

```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_services.py \
  -k 'parallel_ops_overview_summary_and_window_validation or workorder_doc_pack_includes_locale_profile_context'
```

```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_router.py \
  -k 'parallel_ops_summary_export or parallel_ops_trends_export or workorder_doc_export_passes_locale_query_contract'
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_locale_service.py \
  src/yuantus/meta_engine/tests/test_report_locale_service.py \
  src/yuantus/meta_engine/tests/test_locale_router.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py \
  -k 'locale or workorder_doc_pack or workorder_doc_export or parallel_ops_summary_export or parallel_ops_trends_export or parallel_ops_overview_summary_and_window_validation'
```

```bash
git diff --check
```

### Actual Results
- `py_compile`: passed
- `test_parallel_tasks_services.py` targeted:
  - `2 passed, 54 deselected`
- `test_parallel_tasks_router.py` targeted:
  - `7 passed, 111 deselected, 8 warnings`
- combined locale/export pack:
  - `35 passed, 161 deselected, 13 warnings`
- `git diff --check`: passed

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack

### Residual Risks
- locale export 目前只覆盖：
  - `workorder-docs/export`
  - `parallel-ops/summary/export`
  - `parallel-ops/trends/export`
- 还未把 locale 接到更广泛的 breakage / maintenance / BOM 导出

## Increment 2026-03-18 P2A-Breakage-Metrics-Locale

### Touched Areas
- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/services/parallel_tasks_service.py \
  src/yuantus/meta_engine/web/parallel_tasks_router.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py
```

```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_services.py \
  -k 'breakage_metrics_export_json_csv_md or breakage_metrics_groups_export_json_csv_md'
```

```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_router.py \
  -k 'breakage_metrics_export or breakage_metrics_groups_export'
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_locale_service.py \
  src/yuantus/meta_engine/tests/test_report_locale_service.py \
  src/yuantus/meta_engine/tests/test_locale_router.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py \
  -k 'locale or workorder_doc_pack or workorder_doc_export or parallel_ops_summary_export or parallel_ops_trends_export or parallel_ops_overview_summary_and_window_validation or breakage_metrics_export or breakage_metrics_groups_export'
```

```bash
git diff --check
```

### Actual Results
- `py_compile`: passed
- `test_parallel_tasks_services.py` targeted:
  - `2 passed, 54 deselected`
- `test_parallel_tasks_router.py` targeted:
  - `6 passed, 114 deselected, 7 warnings`
- combined locale/export pack:
  - `45 passed, 153 deselected, 19 warnings`
- `git diff --check`: passed

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack

### Residual Risks
- locale export 目前覆盖：
  - `workorder-docs/export`
  - `parallel-ops/summary/export`
  - `parallel-ops/trends/export`
  - `breakage metrics/groups export`
- 还未把 locale 接到 maintenance / BOM / more report pipelines

## Increment 2026-03-18 P2A-Breakage-Incidents-Locale

### Touched Areas
- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/services/parallel_tasks_service.py \
  src/yuantus/meta_engine/web/parallel_tasks_router.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py
```

```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_services.py \
  -k 'breakage_incidents_export_supports_bom_line_filter_and_formats or breakage_metrics_export_json_csv_md or breakage_metrics_groups_export_json_csv_md'
```

```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_router.py \
  -k 'breakage_export or breakage_metrics_export or breakage_metrics_groups_export'
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_locale_service.py \
  src/yuantus/meta_engine/tests/test_report_locale_service.py \
  src/yuantus/meta_engine/tests/test_locale_router.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py \
  -k 'locale or workorder_doc_pack or workorder_doc_export or parallel_ops_summary_export or parallel_ops_trends_export or parallel_ops_overview_summary_and_window_validation or breakage_export or breakage_metrics_export or breakage_metrics_groups_export or breakage_incidents_export_supports_bom_line_filter_and_formats'
```

```bash
git diff --check
```

### Actual Results
- `py_compile`: passed
- `test_parallel_tasks_services.py` targeted:
  - `3 passed, 53 deselected`
- `test_parallel_tasks_router.py` targeted:
  - `13 passed, 108 deselected, 14 warnings`
- combined locale/export pack:
  - `53 passed, 146 deselected, 26 warnings`
- `git diff --check`: passed

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack

## Increment 2026-03-19 C7-C8-C9-Locale Cross Regression

### Touched Areas
- `feature/codex-c7-bom-compare-integration`
- `feature/codex-c8-quality-integration`
- `feature/codex-c9-maintenance-integration`
- `feature/codex-p2a-locale-export`

### Verification Commands
```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_bom_summarized_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_compare_router.py \
  src/yuantus/meta_engine/tests/test_bom_delta_preview.py \
  src/yuantus/meta_engine/tests/test_bom_delta_router.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_quality_service.py \
  src/yuantus/meta_engine/tests/test_quality_router.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_maintenance_service.py \
  src/yuantus/meta_engine/tests/test_maintenance_router.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_locale_service.py \
  src/yuantus/meta_engine/tests/test_report_locale_service.py \
  src/yuantus/meta_engine/tests/test_locale_router.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py -k 'locale or report_locale or export_' \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py -k 'locale or export'
```

### Actual Results
- `C7` BOM summarized + delta pack:
  - `24 passed, 19 warnings`
- `C8` quality pack:
  - `32 passed, 8 warnings`
- `C9` maintenance pack:
  - `35 passed, 8 warnings`
- locale/export combined pack:
  - `84 passed, 123 deselected, 44 warnings`

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack

### Residual Risks
- 这轮是分支内定向回归，不是多分支合并后的单一工作树全量回归
- `C11/C12/C13` 仍未开始实现

### Residual Risks
- locale export 目前覆盖：
  - `workorder-docs/export`
  - `parallel-ops/summary/export`
  - `parallel-ops/trends/export`
  - `breakage metrics/groups export`
  - `breakage incidents export`
- 还未把 locale 接到 maintenance / BOM / more report pipelines

## Increment 2026-03-19 C11-C12 Integration Stack

### Touched Areas
- `src/yuantus/meta_engine/services/cad_converter_service.py`
- `src/yuantus/meta_engine/web/file_router.py`
- `src/yuantus/meta_engine/tests/test_file_viewer_readiness.py`
- `src/yuantus/meta_engine/approvals/__init__.py`
- `src/yuantus/meta_engine/approvals/models.py`
- `src/yuantus/meta_engine/approvals/service.py`
- `src/yuantus/meta_engine/web/approvals_router.py`
- `src/yuantus/meta_engine/tests/test_approvals_service.py`
- `src/yuantus/meta_engine/tests/test_approvals_router.py`
- `src/yuantus/api/app.py`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/services/cad_converter_service.py \
  src/yuantus/meta_engine/web/file_router.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py \
  src/yuantus/meta_engine/approvals/__init__.py \
  src/yuantus/meta_engine/approvals/models.py \
  src/yuantus/meta_engine/approvals/service.py \
  src/yuantus/meta_engine/web/approvals_router.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  src/yuantus/api/app.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py \
  src/yuantus/meta_engine/tests/test_quality_router.py \
  src/yuantus/meta_engine/tests/test_maintenance_router.py \
  src/yuantus/meta_engine/tests/test_locale_router.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py
```

```bash
git diff --check
```

### Actual Results
- `py_compile`: passed
- `C11 + C12` targeted pack:
  - `47 passed, 24 warnings`
- cross-pack regression:
  - `57 passed, 44 warnings`
- `git diff --check`: passed

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack

### Residual Risks
- `C11` 当前只验证了 file/viewer 消费侧，不包含更深的 CAD rule stack
- `C12` 当前是 generic approvals bootstrap，还未接入 ECO/quality 等写侧业务

## Increment 2026-03-19 Unified Stack C7-C13

### Touched Areas
- `feature/codex-stack-c11c12`
- `src/yuantus/meta_engine/tests/test_bom_summarized_router.py`
- `src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_router.py`
- `src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_compare_router.py`
- `src/yuantus/meta_engine/tests/test_quality_router.py`
- `src/yuantus/meta_engine/tests/test_maintenance_router.py`
- `src/yuantus/meta_engine/tests/test_locale_router.py`
- `src/yuantus/meta_engine/tests/test_subcontracting_router.py`
- `src/yuantus/meta_engine/tests/test_file_viewer_readiness.py`
- `src/yuantus/meta_engine/tests/test_approvals_service.py`
- `src/yuantus/meta_engine/tests/test_approvals_router.py`

### Verification Commands
```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_bom_summarized_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_compare_router.py \
  src/yuantus/meta_engine/tests/test_quality_router.py \
  src/yuantus/meta_engine/tests/test_maintenance_router.py \
  src/yuantus/meta_engine/tests/test_locale_router.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py
```

### Actual Results
- unified cross-pack regression:
  - `86 passed, 60 warnings`

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack

### Residual Risks
- 这仍是模块级交叉回归，不是主仓最终合并后的全仓回归
- `C11/C12/C13` 已处于 stack 分支稳定态，但还未进入主仓合并窗口

## Increment 2026-03-19 Wider Cross Regression

### Touched Areas
- `feature/codex-stack-c11c12`
- BOM summarized snapshot + delta test pack
- quality service/router pack
- maintenance service/router pack
- locale/report-locale/router pack
- subcontracting service/router pack
- file viewer readiness pack
- approvals service/router pack

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/services/cad_converter_service.py \
  src/yuantus/meta_engine/web/file_router.py \
  src/yuantus/meta_engine/approvals/__init__.py \
  src/yuantus/meta_engine/approvals/models.py \
  src/yuantus/meta_engine/approvals/service.py \
  src/yuantus/meta_engine/web/approvals_router.py \
  src/yuantus/meta_engine/quality/models.py \
  src/yuantus/meta_engine/quality/service.py \
  src/yuantus/meta_engine/web/quality_router.py \
  src/yuantus/meta_engine/maintenance/models.py \
  src/yuantus/meta_engine/maintenance/service.py \
  src/yuantus/meta_engine/web/maintenance_router.py \
  src/yuantus/meta_engine/locale/service.py \
  src/yuantus/meta_engine/report_locale/service.py \
  src/yuantus/meta_engine/web/locale_router.py \
  src/yuantus/meta_engine/subcontracting/models.py \
  src/yuantus/meta_engine/subcontracting/service.py \
  src/yuantus/meta_engine/web/subcontracting_router.py \
  src/yuantus/meta_engine/web/bom_router.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_bom_summarized_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_compare_router.py \
  src/yuantus/meta_engine/tests/test_bom_delta_preview.py \
  src/yuantus/meta_engine/tests/test_bom_delta_router.py \
  src/yuantus/meta_engine/tests/test_quality_service.py \
  src/yuantus/meta_engine/tests/test_quality_router.py \
  src/yuantus/meta_engine/tests/test_maintenance_service.py \
  src/yuantus/meta_engine/tests/test_maintenance_router.py \
  src/yuantus/meta_engine/tests/test_locale_service.py \
  src/yuantus/meta_engine/tests/test_report_locale_service.py \
  src/yuantus/meta_engine/tests/test_locale_router.py \
  src/yuantus/meta_engine/tests/test_subcontracting_service.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py
```

### Actual Results
- `py_compile`: passed
- wider cross-pack regression:
  - `177 passed, 62 warnings`

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack

### Residual Risks
- 仍未覆盖主仓最终合并后的全仓回归
- 当前结果证明的是 `C7-C13` 统一 stack 的组合稳定性

## Increment 2026-03-19 Unified Stack Regression Automation

### Touched Areas
- `scripts/verify_odoo18_plm_stack.sh`
- `.github/workflows/odoo18-plm-stack-regression.yml`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`

### Verification Commands
```bash
chmod +x scripts/verify_odoo18_plm_stack.sh
```

```bash
bash -n scripts/verify_odoo18_plm_stack.sh
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc scripts/verify_odoo18_plm_stack.sh full
```

```bash
git diff --check
```

### Actual Results
- `bash -n`: passed
- stack regression script (`full`):
  - `177 passed, 62 warnings in 14.45s`
- `git diff --check`: passed

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack

### Residual Risks
- workflow 目前只提供手动触发，不会自动替代现有回归流水线
- `C14/C15/C16` 仍需等实际分支返回后，再用该脚本做增量集成验证

## Increment 2026-03-19 C14-C15 Unified Stack Integration

### Touched Areas
- `src/yuantus/meta_engine/approvals/service.py`
- `src/yuantus/meta_engine/web/approvals_router.py`
- `src/yuantus/meta_engine/tests/test_approvals_service.py`
- `src/yuantus/meta_engine/tests/test_approvals_router.py`
- `src/yuantus/meta_engine/subcontracting/service.py`
- `src/yuantus/meta_engine/web/subcontracting_router.py`
- `src/yuantus/meta_engine/tests/test_subcontracting_service.py`
- `src/yuantus/meta_engine/tests/test_subcontracting_router.py`
- `scripts/verify_odoo18_plm_stack.sh`
- shared `PLAN/DESIGN/VERIFICATION` docs

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/approvals/service.py \
  src/yuantus/meta_engine/web/approvals_router.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  src/yuantus/meta_engine/subcontracting/service.py \
  src/yuantus/meta_engine/web/subcontracting_router.py \
  src/yuantus/meta_engine/tests/test_subcontracting_service.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  src/yuantus/meta_engine/tests/test_subcontracting_service.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router.py
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc scripts/verify_odoo18_plm_stack.sh full
```

```bash
git diff --check
```

### Actual Results
- targeted pack:
  - `44 passed, 16 warnings in 4.70s`
- unified stack script (`full`):
  - `191 passed, 68 warnings in 11.44s`
- `git diff --check`: passed

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack

### Residual Risks
- `C16` 仍未进入统一栈
- `C14/C15` 是基于 worker 交付契约在统一栈复刻并验证，不是直接 cherry-pick worker branch

## Increment 2026-03-19 C16 Unified Stack Integration

### Touched Areas
- `contracts/claude_allowed_paths.json`
- `src/yuantus/api/app.py`
- `src/yuantus/meta_engine/quality/analytics_service.py`
- `src/yuantus/meta_engine/quality/spc_service.py`
- `src/yuantus/meta_engine/web/quality_analytics_router.py`
- `src/yuantus/meta_engine/tests/test_quality_analytics_service.py`
- `src/yuantus/meta_engine/tests/test_quality_analytics_router.py`
- `src/yuantus/meta_engine/tests/test_quality_spc_service.py`
- `scripts/verify_odoo18_plm_stack.sh`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/quality/analytics_service.py \
  src/yuantus/meta_engine/quality/spc_service.py \
  src/yuantus/meta_engine/web/quality_analytics_router.py \
  src/yuantus/meta_engine/tests/test_quality_analytics_service.py \
  src/yuantus/meta_engine/tests/test_quality_analytics_router.py \
  src/yuantus/meta_engine/tests/test_quality_spc_service.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_quality_analytics_service.py \
  src/yuantus/meta_engine/tests/test_quality_analytics_router.py \
  src/yuantus/meta_engine/tests/test_quality_spc_service.py
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc scripts/verify_odoo18_plm_stack.sh full
```

```bash
git diff --check
```

### Actual Results
- targeted C16 pack:
  - `27 passed, 8 warnings in 4.73s`
- unified stack script (`full`):
  - `218 passed, 75 warnings in 13.09s`
- `git diff --check`: passed

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack

### Residual Risks
- `C14/C15/C16` 虽已进入统一栈，但还没有做主仓最终合并回归
- 当前建议不再继续给 Claude 开新功能分支，先进入 merge-prep

## Increment 2026-03-19 Merge Prep Broader Regression

### Touched Areas
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`
- `docs/DELIVERY_DOC_INDEX.md`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc pytest -q \
  src/yuantus/meta_engine/tests/test_bom_summarized_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_compare_router.py \
  src/yuantus/meta_engine/tests/test_bom_delta_preview.py \
  src/yuantus/meta_engine/tests/test_bom_delta_router.py \
  src/yuantus/meta_engine/tests/test_quality_service.py \
  src/yuantus/meta_engine/tests/test_quality_router.py \
  src/yuantus/meta_engine/tests/test_quality_analytics_service.py \
  src/yuantus/meta_engine/tests/test_quality_analytics_router.py \
  src/yuantus/meta_engine/tests/test_quality_spc_service.py \
  src/yuantus/meta_engine/tests/test_maintenance_service.py \
  src/yuantus/meta_engine/tests/test_maintenance_router.py \
  src/yuantus/meta_engine/tests/test_locale_service.py \
  src/yuantus/meta_engine/tests/test_report_locale_service.py \
  src/yuantus/meta_engine/tests/test_locale_router.py \
  src/yuantus/meta_engine/tests/test_subcontracting_service.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py -k 'locale or report_locale or export_' \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py -k 'locale or export'
```

### Actual Results
- broader merge-prep pack:
  - `112 passed, 283 deselected, 62 warnings in 14.38s`

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack

### Residual Risks
- 当前 wider pack 仍不是主仓最终全仓回归
- merge-prep 热点仍集中在 `app.py`、path guard 和共享文档，不是功能性阻塞

## Increment 2026-03-19 Next Claude Batch Preparation

### Touched Areas
- `contracts/claude_allowed_paths.json`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DESIGN_PARALLEL_C17_PLM_BOX_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C17_PLM_BOX_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C18_DOCUMENT_SYNC_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C18_DOCUMENT_SYNC_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C19_CUTTED_PARTS_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C19_CUTTED_PARTS_BOOTSTRAP_20260319.md`

### Verification Commands
```bash
python3 -m json.tool contracts/claude_allowed_paths.json >/dev/null
```

```bash
git diff --check
```

### Actual Results
- path guard JSON parse: passed
- `git diff --check`: passed

### Residual Risks
- `C17-C19` 已汇总到 greenfield 候选栈，但仍未接入统一主应用

## Increment 2026-03-19 Codex-C19-Integration

### Touched Areas
- `feature/codex-c19-cutted-parts-integration`
- `src/yuantus/meta_engine/cutted_parts/__init__.py`
- `src/yuantus/meta_engine/cutted_parts/models.py`
- `src/yuantus/meta_engine/cutted_parts/service.py`
- `src/yuantus/meta_engine/web/cutted_parts_router.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_service.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_router.py`
- `docs/DESIGN_PARALLEL_C19_CUTTED_PARTS_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C19_CUTTED_PARTS_BOOTSTRAP_20260319.md`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/cutted_parts/__init__.py \
  src/yuantus/meta_engine/cutted_parts/models.py \
  src/yuantus/meta_engine/cutted_parts/service.py \
  src/yuantus/meta_engine/web/cutted_parts_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_service.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_cutted_parts_service.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router.py \
  src/yuantus/meta_engine/tests/test_quality_analytics_router.py \
  src/yuantus/meta_engine/tests/test_maintenance_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py
```

```bash
git diff --check
```

### Actual Results
- `py_compile`: passed
- targeted `C19` pack:
  - `35 passed, 11 warnings`
- light cross-pack regression:
  - `69 passed, 56 warnings`
- `git diff --check`: passed

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack

### Residual Risks
- `C19` 仍保持未注册到 `src/yuantus/api/app.py`
- 当前只证明 greenfield router/service 与现有已集成子域不冲突，尚未证明全应用接线

## Increment 2026-03-19 Codex-C17-Integration

### Touched Areas
- `feature/codex-c17-box-integration`
- `src/yuantus/meta_engine/box/__init__.py`
- `src/yuantus/meta_engine/box/models.py`
- `src/yuantus/meta_engine/box/service.py`
- `src/yuantus/meta_engine/web/box_router.py`
- `src/yuantus/meta_engine/tests/test_box_service.py`
- `src/yuantus/meta_engine/tests/test_box_router.py`
- `docs/DESIGN_PARALLEL_C17_PLM_BOX_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C17_PLM_BOX_BOOTSTRAP_20260319.md`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/box/__init__.py \
  src/yuantus/meta_engine/box/models.py \
  src/yuantus/meta_engine/box/service.py \
  src/yuantus/meta_engine/web/box_router.py \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router.py \
  src/yuantus/meta_engine/tests/test_quality_analytics_router.py \
  src/yuantus/meta_engine/tests/test_maintenance_router.py \
  src/yuantus/meta_engine/tests/test_box_router.py
```

```bash
git diff --check
```

### Actual Results
- `py_compile`: passed
- targeted `C17` pack:
  - `19 passed, 8 warnings`
- light cross-pack regression:
  - `66 passed, 53 warnings`
- `git diff --check`: passed

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack

### Residual Risks
- `C17` 仍保持未注册到 `src/yuantus/api/app.py`
- 当前只证明 greenfield router/service 与现有已集成子域不冲突，尚未证明全应用接线

## Increment 2026-03-19 C7-C8-C9 Stack Branch

### Touched Areas
- `feature/codex-stack-c7c8c9`
- `src/yuantus/api/app.py`
- `contracts/claude_allowed_paths.json`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/web/maintenance_router.py \
  src/yuantus/meta_engine/web/quality_router.py \
  src/yuantus/meta_engine/web/bom_router.py \
  src/yuantus/meta_engine/web/locale_router.py \
  src/yuantus/meta_engine/maintenance/service.py \
  src/yuantus/meta_engine/quality/service.py \
  src/yuantus/meta_engine/locale/service.py \
  src/yuantus/meta_engine/report_locale/service.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_locale_service.py \
  src/yuantus/meta_engine/tests/test_report_locale_service.py \
  src/yuantus/meta_engine/tests/test_locale_router.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py -k 'locale or report_locale or export_' \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py -k 'locale or export' \
  src/yuantus/meta_engine/tests/test_maintenance_service.py \
  src/yuantus/meta_engine/tests/test_maintenance_router.py \
  src/yuantus/meta_engine/tests/test_quality_service.py \
  src/yuantus/meta_engine/tests/test_quality_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_compare_router.py \
  src/yuantus/meta_engine/tests/test_bom_delta_preview.py \
  src/yuantus/meta_engine/tests/test_bom_delta_router.py
```

```bash
git diff --check
```

### Actual Results
- `py_compile`: passed
- integrated stack regression:
  - `98 passed, 200 deselected, 54 warnings in 12.37s`
- `git diff --check`: passed

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack

### Residual Risks
- stack branch 目前还没有把 `C11/C12/C13` 实现并入
- 主仓 `/Users/huazhou/Downloads/Github/Yuantus` 仍在 Claude 分支，不应直接在主仓上继续叠集成改动

## Increment 2026-03-19 C13-Subcontracting Bootstrap

### Touched Areas
- `src/yuantus/meta_engine/subcontracting/__init__.py`
- `src/yuantus/meta_engine/subcontracting/models.py`
- `src/yuantus/meta_engine/subcontracting/service.py`
- `src/yuantus/meta_engine/web/subcontracting_router.py`
- `src/yuantus/meta_engine/tests/test_subcontracting_service.py`
- `src/yuantus/meta_engine/tests/test_subcontracting_router.py`
- `src/yuantus/api/app.py`
- `docs/DESIGN_PARALLEL_C13_SUBCONTRACTING_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C13_SUBCONTRACTING_BOOTSTRAP_20260319.md`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/subcontracting/__init__.py \
  src/yuantus/meta_engine/subcontracting/models.py \
  src/yuantus/meta_engine/subcontracting/service.py \
  src/yuantus/meta_engine/web/subcontracting_router.py \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/tests/test_subcontracting_service.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_subcontracting_service.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router.py
```

### Actual Results
- `py_compile`: passed
- subcontracting bootstrap pack:
  - `9 passed, 3 warnings`

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack

### Residual Risks
- 目前还是 bootstrap 读模型，没有采购/收货单据联动
- 目前不回写制造主服务，只消费已有 `Operation` 委外字段

## Increment 2026-03-18 C10-Locale-Resolver

### Touched Areas
- `src/yuantus/meta_engine/locale/service.py`
- `src/yuantus/meta_engine/report_locale/service.py`
- `src/yuantus/meta_engine/web/locale_router.py`
- `src/yuantus/meta_engine/tests/test_locale_service.py`
- `src/yuantus/meta_engine/tests/test_report_locale_service.py`
- `src/yuantus/meta_engine/tests/test_locale_router.py`
- `docs/DESIGN_PARALLEL_C10_LOCALE_RESOLVER_EXPORT_HELPERS_20260318.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C10_LOCALE_RESOLVER_EXPORT_HELPERS_20260318.md`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/locale/service.py \
  src/yuantus/meta_engine/report_locale/service.py \
  src/yuantus/meta_engine/web/locale_router.py \
  src/yuantus/meta_engine/tests/test_locale_service.py \
  src/yuantus/meta_engine/tests/test_report_locale_service.py \
  src/yuantus/meta_engine/tests/test_locale_router.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_locale_service.py \
  src/yuantus/meta_engine/tests/test_report_locale_service.py \
  src/yuantus/meta_engine/tests/test_locale_router.py
```

```bash
git diff --check
```

### Actual Results
- `py_compile`: passed
- locale domain pack:
  - `30 passed, 5 warnings`
- `git diff --check`: passed

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack

### Residual Risks
- `C10` 目前只完成 locale 域 contract 与独立验证
- 还未在 BOM / maintenance / quality 等域直接消费 `resolve` / `export-context`

## Increment 2026-03-19 Merge-Prep Final Regression

### Touched Areas
- `feature/codex-stack-c11c12`
- `scripts/verify_odoo18_plm_stack.sh`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc scripts/verify_odoo18_plm_stack.sh full
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc pytest -q \
  src/yuantus/meta_engine/tests/test_bom_summarized_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_compare_router.py \
  src/yuantus/meta_engine/tests/test_bom_delta_preview.py \
  src/yuantus/meta_engine/tests/test_bom_delta_router.py \
  src/yuantus/meta_engine/tests/test_quality_service.py \
  src/yuantus/meta_engine/tests/test_quality_router.py \
  src/yuantus/meta_engine/tests/test_quality_analytics_service.py \
  src/yuantus/meta_engine/tests/test_quality_analytics_router.py \
  src/yuantus/meta_engine/tests/test_quality_spc_service.py \
  src/yuantus/meta_engine/tests/test_maintenance_service.py \
  src/yuantus/meta_engine/tests/test_maintenance_router.py \
  src/yuantus/meta_engine/tests/test_locale_service.py \
  src/yuantus/meta_engine/tests/test_report_locale_service.py \
  src/yuantus/meta_engine/tests/test_locale_router.py \
  src/yuantus/meta_engine/tests/test_subcontracting_service.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py -k 'locale or report_locale or export_' \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py -k 'locale or export'
```

```bash
git diff --check
```

### Actual Results
- unified stack script:
  - `218 passed, 75 warnings in 12.43s`
- broader merge-prep pack:
  - `112 passed, 283 deselected, 62 warnings in 15.07s`
- `git diff --check`: passed

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack

### Residual Risks
- wider final pack 仍不是整仓全量回归
- 当前主风险已从功能缺陷转移为合并顺序和审阅质量

## Increment 2026-03-19 Codex-C18-Integration

### Touched Areas
- `feature/codex-c18-document-sync-integration`
- `src/yuantus/meta_engine/document_sync/__init__.py`
- `src/yuantus/meta_engine/document_sync/models.py`
- `src/yuantus/meta_engine/document_sync/service.py`
- `src/yuantus/meta_engine/web/document_sync_router.py`
- `src/yuantus/meta_engine/tests/test_document_sync_service.py`
- `src/yuantus/meta_engine/tests/test_document_sync_router.py`
- `docs/DESIGN_PARALLEL_C18_DOCUMENT_SYNC_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C18_DOCUMENT_SYNC_BOOTSTRAP_20260319.md`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/document_sync/__init__.py \
  src/yuantus/meta_engine/document_sync/models.py \
  src/yuantus/meta_engine/document_sync/service.py \
  src/yuantus/meta_engine/web/document_sync_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router.py \
  src/yuantus/meta_engine/tests/test_quality_analytics_router.py \
  src/yuantus/meta_engine/tests/test_maintenance_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py
```

```bash
git diff --check
```

### Actual Results
- `py_compile`: passed
- targeted `C18` pack:
  - `33 passed, 12 warnings`
- light cross-pack regression:
  - `70 passed, 57 warnings`
- `git diff --check`: passed

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack

### Residual Risks
- `C18` 仍保持未注册到 `src/yuantus/api/app.py`
- 当前只证明 greenfield router/service 与现有已集成子域不冲突，尚未证明全应用接线

## Increment 2026-03-19 Codex-C17-C18-Stack

### Touched Areas
- `feature/codex-stack-c17c18`
- `src/yuantus/meta_engine/box/__init__.py`
- `src/yuantus/meta_engine/box/models.py`
- `src/yuantus/meta_engine/box/service.py`
- `src/yuantus/meta_engine/web/box_router.py`
- `src/yuantus/meta_engine/document_sync/__init__.py`
- `src/yuantus/meta_engine/document_sync/models.py`
- `src/yuantus/meta_engine/document_sync/service.py`
- `src/yuantus/meta_engine/web/document_sync_router.py`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DELIVERY_DOC_INDEX.md`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/box/__init__.py \
  src/yuantus/meta_engine/box/models.py \
  src/yuantus/meta_engine/box/service.py \
  src/yuantus/meta_engine/web/box_router.py \
  src/yuantus/meta_engine/document_sync/__init__.py \
  src/yuantus/meta_engine/document_sync/models.py \
  src/yuantus/meta_engine/document_sync/service.py \
  src/yuantus/meta_engine/web/document_sync_router.py \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router.py \
  src/yuantus/meta_engine/tests/test_quality_analytics_router.py \
  src/yuantus/meta_engine/tests/test_maintenance_router.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py
```

```bash
git diff --check
```

### Actual Results
- `py_compile`: passed
- `C17 + C18` targeted pack:
  - `52 passed, 19 warnings`
- light cross-pack regression:
  - `77 passed, 64 warnings`
- `git diff --check`: passed

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack

### Residual Risks
- `C17/C18` 仍都保持未注册到 `src/yuantus/api/app.py`
- 当前只证明两个 greenfield 子域可以一起叠加且不踩现有已集成子域，尚未证明统一主应用接线

## Increment 2026-03-19 Codex-C17-C18-C19-Stack

### Touched Areas
- `feature/codex-stack-c17c18c19`
- `src/yuantus/meta_engine/box/__init__.py`
- `src/yuantus/meta_engine/box/models.py`
- `src/yuantus/meta_engine/box/service.py`
- `src/yuantus/meta_engine/web/box_router.py`
- `src/yuantus/meta_engine/document_sync/__init__.py`
- `src/yuantus/meta_engine/document_sync/models.py`
- `src/yuantus/meta_engine/document_sync/service.py`
- `src/yuantus/meta_engine/web/document_sync_router.py`
- `src/yuantus/meta_engine/cutted_parts/__init__.py`
- `src/yuantus/meta_engine/cutted_parts/models.py`
- `src/yuantus/meta_engine/cutted_parts/service.py`
- `src/yuantus/meta_engine/web/cutted_parts_router.py`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/box/__init__.py \
  src/yuantus/meta_engine/box/models.py \
  src/yuantus/meta_engine/box/service.py \
  src/yuantus/meta_engine/web/box_router.py \
  src/yuantus/meta_engine/document_sync/__init__.py \
  src/yuantus/meta_engine/document_sync/models.py \
  src/yuantus/meta_engine/document_sync/service.py \
  src/yuantus/meta_engine/web/document_sync_router.py \
  src/yuantus/meta_engine/cutted_parts/__init__.py \
  src/yuantus/meta_engine/cutted_parts/models.py \
  src/yuantus/meta_engine/cutted_parts/service.py \
  src/yuantus/meta_engine/web/cutted_parts_router.py \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_service.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_service.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router.py \
  src/yuantus/meta_engine/tests/test_quality_analytics_router.py \
  src/yuantus/meta_engine/tests/test_maintenance_router.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py
```

```bash
git diff --check
```

### Actual Results
- `py_compile`: passed
- `C17 + C18 + C19` targeted pack:
  - `87 passed, 29 warnings`
- light cross-pack regression:
  - `87 passed, 74 warnings`
- `git diff --check`: passed

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack

### Residual Risks
- `C17/C18/C19` 仍都保持未注册到 `src/yuantus/api/app.py`
- 当前只证明三个 greenfield 子域可以一起叠加且不踩现有已集成子域，尚未证明统一主应用接线

## Increment 2026-03-19 Codex-C17-C18-C19-Merge-Prep

### Touched Areas
- `feature/codex-stack-c17c18c19`
- `scripts/verify_odoo18_plm_stack.sh`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `feature/codex-merge-rehearsal-c17c18c19`

### Verification Commands
```bash
bash -n scripts/verify_odoo18_plm_stack.sh
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc scripts/verify_odoo18_plm_stack.sh full
```

```bash
git worktree add /Users/huazhou/Downloads/Github/Yuantus-worktrees/codex-merge-rehearsal-c17c18c19 \
  -b feature/codex-merge-rehearsal-c17c18c19 \
  main
```

```bash
git -C /Users/huazhou/Downloads/Github/Yuantus-worktrees/codex-merge-rehearsal-c17c18c19 \
  merge --no-ff feature/codex-stack-c17c18c19 \
  -m "Merge branch 'feature/codex-stack-c17c18c19' into feature/codex-merge-rehearsal-c17c18c19"
```

```bash
git diff --check
```

### Actual Results
- `bash -n scripts/verify_odoo18_plm_stack.sh`: passed
- expanded stack script full baseline:
  - `305 passed, 103 warnings in 121.86s`
- merge rehearsal:
  - no manual conflict resolution needed
  - merge rehearsal commit: `7db4fc6`
  - rehearsal-branch full baseline:
    - `305 passed, 103 warnings in 20.43s`
- `git diff --check`: passed

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack

### Residual Risks
- `C17/C18/C19` 仍未接入 `src/yuantus/api/app.py`
- 当前证明的是候选栈可稳定回归且可干净合入 `main`，还未把这三域并回统一主栈

## Increment 2026-03-19 Codex-Main-Merge-C17-C18-C19

### Touched Areas
- `main`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`

### Verification Commands
```bash
bash -n scripts/verify_odoo18_plm_stack.sh
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc scripts/verify_odoo18_plm_stack.sh full
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc pytest -q \
  src/yuantus/meta_engine/tests/test_bom_summarized_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_compare_router.py \
  src/yuantus/meta_engine/tests/test_bom_delta_preview.py \
  src/yuantus/meta_engine/tests/test_bom_delta_router.py \
  src/yuantus/meta_engine/tests/test_quality_service.py \
  src/yuantus/meta_engine/tests/test_quality_router.py \
  src/yuantus/meta_engine/tests/test_quality_analytics_service.py \
  src/yuantus/meta_engine/tests/test_quality_analytics_router.py \
  src/yuantus/meta_engine/tests/test_quality_spc_service.py \
  src/yuantus/meta_engine/tests/test_maintenance_service.py \
  src/yuantus/meta_engine/tests/test_maintenance_router.py \
  src/yuantus/meta_engine/tests/test_locale_service.py \
  src/yuantus/meta_engine/tests/test_report_locale_service.py \
  src/yuantus/meta_engine/tests/test_locale_router.py \
  src/yuantus/meta_engine/tests/test_subcontracting_service.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py -k 'locale or report_locale or export_' \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py -k 'locale or export'
```

```bash
git diff --check
```

### Actual Results
- actual merge:
  - source branch `feature/codex-stack-c17c18c19`
  - target branch `main`
  - merge commit: `f46ff5e`
- `bash -n scripts/verify_odoo18_plm_stack.sh`: passed
- post-merge expanded stack script:
  - `305 passed, 103 warnings in 17.86s`
- broader merge-prep pack:
  - `112 passed, 283 deselected, 63 warnings in 46.91s`
- `git diff --check`: passed

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack
- `pytest` cache write warning:
  - `.pytest_cache` emitted `No space left on device`
  - test execution still completed successfully

### Residual Risks
- `C17/C18/C19` 仍未接入 `src/yuantus/api/app.py`
- 当前已证明 `main` 上的合并结果可稳定回归，但磁盘空间压力需要在后续稳定窗口内处理

## Increment 2026-03-19 Codex-Post-Merge-Stabilization-Refresh

### Touched Areas
- `main`
- clean Codex worktrees under `/Users/huazhou/Downloads/Github/Yuantus-worktrees/`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`

### Verification Commands
```bash
bash -n scripts/verify_odoo18_plm_stack.sh
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc scripts/verify_odoo18_plm_stack.sh full
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc pytest -q \
  src/yuantus/meta_engine/tests/test_bom_summarized_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_compare_router.py \
  src/yuantus/meta_engine/tests/test_bom_delta_preview.py \
  src/yuantus/meta_engine/tests/test_bom_delta_router.py \
  src/yuantus/meta_engine/tests/test_quality_service.py \
  src/yuantus/meta_engine/tests/test_quality_router.py \
  src/yuantus/meta_engine/tests/test_quality_analytics_service.py \
  src/yuantus/meta_engine/tests/test_quality_analytics_router.py \
  src/yuantus/meta_engine/tests/test_quality_spc_service.py \
  src/yuantus/meta_engine/tests/test_maintenance_service.py \
  src/yuantus/meta_engine/tests/test_maintenance_router.py \
  src/yuantus/meta_engine/tests/test_locale_service.py \
  src/yuantus/meta_engine/tests/test_report_locale_service.py \
  src/yuantus/meta_engine/tests/test_locale_router.py \
  src/yuantus/meta_engine/tests/test_subcontracting_service.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py -k 'locale or report_locale or export_' \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py -k 'locale or export'
```

### Actual Results
- removed superseded rehearsal and integration worktrees and cleaned cache directories from the remaining clean Codex worktrees
- available disk space recovered to roughly `4.3Gi`
- `bash -n scripts/verify_odoo18_plm_stack.sh`: passed
- post-cleanup expanded stack script:
  - `305 passed, 103 warnings in 13.98s`
- post-cleanup broader merge-prep pack:
  - `112 passed, 283 deselected, 62 warnings in 17.06s`

### Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack

### Residual Risks
- `C17/C18/C19` 仍未接入 `src/yuantus/api/app.py`
- 当前已证明磁盘清理后的 merged `main` 可稳定回归，但仍需人工接受稳定窗口后再恢复新一轮并行开发

## Increment 2026-03-19 Codex-Prepare-Next-Claude-Batch-C20-C22

### Touched Areas
- `main`
- `contracts/claude_allowed_paths.json`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DESIGN_PARALLEL_C20_PLM_BOX_ANALYTICS_EXPORT_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C20_PLM_BOX_ANALYTICS_EXPORT_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C21_DOCUMENT_SYNC_ANALYTICS_EXPORT_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C21_DOCUMENT_SYNC_ANALYTICS_EXPORT_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C22_CUTTED_PARTS_ANALYTICS_EXPORT_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C22_CUTTED_PARTS_ANALYTICS_EXPORT_BOOTSTRAP_20260319.md`

### Verification Commands
```bash
python3 -m json.tool contracts/claude_allowed_paths.json >/dev/null
```

```bash
git diff --check
```

### Actual Results
- added path-guard profiles `C20`, `C21`, `C22`
- prepared shared PLAN / DESIGN / VERIFICATION entries for the next Claude batch
- added standalone design / verification templates for `C20/C21/C22`
- `python3 -m json.tool contracts/claude_allowed_paths.json >/dev/null`: passed
- `git diff --check`: passed

### Residual Risks
- `C20` and `C21` have now moved beyond task preparation into Codex-verified candidate-stack state
- `C22` was still pending at this point in the timeline and should stay off `src/yuantus/api/app.py` and all integrated hot routers until integrated

## Increment 2026-03-19 Codex-C20-C21-Stack-Verification

### Touched Areas
- `feature/codex-stack-c20c21`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C20_PLM_BOX_ANALYTICS_EXPORT_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C21_DOCUMENT_SYNC_ANALYTICS_EXPORT_BOOTSTRAP_20260319.md`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c20c21 python3 -m py_compile \
  src/yuantus/meta_engine/box/service.py \
  src/yuantus/meta_engine/web/box_router.py \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/document_sync/service.py \
  src/yuantus/meta_engine/web/document_sync_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c20c21 pytest -q \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py
```

```bash
git diff --check
```

### Actual Results
- cherry-picked `4102f55` into candidate stack as `e85d046`
- cherry-picked `18ecb5b` into candidate stack as `b45e7a4`
- `py_compile`: passed
- combined targeted regression: `83 passed, 33 warnings in 9.00s`
- greenfield cross-regression with `C19`: `118 passed, 43 warnings in 31.73s`
- `git diff --check`: passed

### Residual Risks
- disk free space remained low during the first attempt, so single-domain temp worktrees had to be removed before the combined stack could be verified
- warnings remain the existing `starlette.formparsers` and `httpx app=` deprecations

## Increment 2026-03-19 Codex-C22-Integration

### Touched Areas
- `feature/codex-stack-c20c21c22`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C22_CUTTED_PARTS_ANALYTICS_EXPORT_BOOTSTRAP_20260319.md`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c20c21c22 python3 -m py_compile \
  src/yuantus/meta_engine/cutted_parts/service.py \
  src/yuantus/meta_engine/web/cutted_parts_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_service.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c20c21c22 pytest -q -p no:cacheprovider \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_service.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py
```

```bash
git diff --check
```

### Actual Results
- cherry-picked `64c9724` into candidate stack as `68e3dbb`
- `py_compile`: passed
- combined greenfield regression with `C20+C21+C22`: `133 passed, 49 warnings in 3.32s`
- unified stack script on `feature/codex-stack-c20c21c22`: `351 passed, 123 warnings in 28.77s`
- `git diff --check`: passed

### Residual Risks
- warnings remain the existing `starlette.formparsers` and `httpx app=` deprecations

## Increment 2026-03-19 Main-FastForward-C29-C30-C31

### Touched Areas
- `main`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`

### Verification Commands
```bash
git merge --ff-only feature/codex-c29c30c31-staging
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-main-c29c30c31-target PYTEST_ADDOPTS='-p no:cacheprovider' pytest -q \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_service.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-main-c29c30c31-full PYTEST_ADDOPTS='-p no:cacheprovider' \
  scripts/verify_odoo18_plm_stack.sh full
```

```bash
git diff --check
```

### Actual Results
- `main` fast-forwarded from `c620f94` to `5feeb4a`
- post-merge targeted greenfield rerun on `main`: `267 passed, 98 warnings in 2.74s`
- post-merge unified stack rerun on `main`: `485 passed, 172 warnings in 12.59s`
- `git diff --check`: passed

### Residual Risks
- warnings remain the existing `starlette.formparsers` and `httpx app=` deprecations
- no new post-merge functional regression was observed

## Increment 2026-03-19 Main-Stability-Refresh-C29-C30-C31

### Touched Areas
- `main`
- no functional code changes; verification-only stability pass

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-main-c29c30c31-stability-target PYTEST_ADDOPTS='-p no:cacheprovider' pytest -q \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_service.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-main-c29c30c31-stability-full PYTEST_ADDOPTS='-p no:cacheprovider' \
  scripts/verify_odoo18_plm_stack.sh full
```

### Actual Results
- targeted greenfield stability rerun on `main`: `267 passed, 98 warnings in 2.67s`
- unified stack stability rerun on `main`: `485 passed, 172 warnings in 14.52s`

### Residual Risks
- warnings remain the existing `starlette.formparsers` and `httpx app=` deprecations
- no new stability-window regression was observed

## Increment 2026-03-19 Codex-Prepare-Next-Claude-Batch-C32-C34

### Touched Areas
- `main`
- `contracts/claude_allowed_paths.json`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DESIGN_PARALLEL_C32_PLM_BOX_POLICY_EXCEPTIONS_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C32_PLM_BOX_POLICY_EXCEPTIONS_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C33_DOCUMENT_SYNC_BASELINE_LINEAGE_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C33_DOCUMENT_SYNC_BASELINE_LINEAGE_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C34_CUTTED_PARTS_VARIANCE_RECOMMENDATIONS_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C34_CUTTED_PARTS_VARIANCE_RECOMMENDATIONS_BOOTSTRAP_20260319.md`

### Verification Commands
```bash
python3 -m json.tool contracts/claude_allowed_paths.json >/dev/null
```

```bash
git diff --check
```

### Actual Results
- added path-guard profiles `C32`, `C33`, `C34`
- created frozen Claude base branch `feature/claude-greenfield-base-6`
- prepared shared PLAN / DESIGN / VERIFICATION entries for the next Claude batch
- added standalone design / verification templates for `C32/C33/C34`

### Residual Risks
- this preparation step itself introduces no code changes
- the next Claude batch should still stay off `src/yuantus/api/app.py` and all integrated hot routers outside their own domains

## Increment 2026-03-20 Codex-C32-C33-Stack-Verification

### Touched Areas
- `feature/codex-c32c33-staging`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C32_PLM_BOX_POLICY_EXCEPTIONS_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C33_DOCUMENT_SYNC_BASELINE_LINEAGE_BOOTSTRAP_20260319.md`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c32c33 python3 -m py_compile \
  src/yuantus/meta_engine/box/service.py \
  src/yuantus/meta_engine/web/box_router.py \
  src/yuantus/meta_engine/document_sync/service.py \
  src/yuantus/meta_engine/web/document_sync_router.py \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c32c33-target PYTEST_ADDOPTS='-p no:cacheprovider' pytest -q \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c32c33-full PYTEST_ADDOPTS='-p no:cacheprovider' \
  scripts/verify_odoo18_plm_stack.sh full
```

```bash
git diff --check
```

### Actual Results
- cherry-picked `3c6c869` into staging as `80c2e7e`
- cherry-picked `a157314` into staging as `c0d3e06`
- `py_compile`: passed
- combined targeted regression: `198 passed, 77 warnings in 6.03s`
- unified stack script on `feature/codex-c32c33-staging`: `514 passed, 183 warnings in 11.98s`
- `git diff --check`: passed

### Residual Risks
- warnings remain the existing `starlette.formparsers` and `httpx app=` deprecations
- `C34` had not been integrated yet at this point in the timeline

## Increment 2026-03-20 Codex-C34-Stack-Verification

### Touched Areas
- `feature/codex-c32c33c34-staging`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C34_CUTTED_PARTS_VARIANCE_RECOMMENDATIONS_BOOTSTRAP_20260319.md`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c32c33c34 python3 -m py_compile \
  src/yuantus/meta_engine/box/service.py \
  src/yuantus/meta_engine/web/box_router.py \
  src/yuantus/meta_engine/document_sync/service.py \
  src/yuantus/meta_engine/web/document_sync_router.py \
  src/yuantus/meta_engine/cutted_parts/service.py \
  src/yuantus/meta_engine/web/cutted_parts_router.py \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_service.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c32c33c34-target PYTEST_ADDOPTS='-p no:cacheprovider' pytest -q \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_service.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c32c33c34-full PYTEST_ADDOPTS='-p no:cacheprovider' \
  scripts/verify_odoo18_plm_stack.sh full
```

```bash
git diff --check
```

### Actual Results
- cherry-picked `45a94fc` into staging as `7b50ea2`
- `py_compile`: passed
- combined targeted regression with `C32/C33/C34`: `314 passed, 114 warnings in 3.32s`
- unified stack script on `feature/codex-c32c33c34-staging`: `532 passed, 188 warnings in 12.93s`
- `git diff --check`: passed

### Residual Risks
- warnings remain the existing `starlette.formparsers` and `httpx app=` deprecations

## Increment 2026-03-19 Codex-Merge-Rehearsal-C29-C30-C31

### Touched Areas
- `feature/codex-c29c30c31-staging`
- `feature/codex-merge-rehearsal-c29c30c31`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`

### Verification Commands
```bash
git merge --ff-only feature/codex-c29c30c31-staging
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-merge-c29c30c31-full PYTEST_ADDOPTS='-p no:cacheprovider' \
  scripts/verify_odoo18_plm_stack.sh full
```

```bash
git diff --check
```

### Actual Results
- rehearsal branch fast-forwarded from `c620f94` to `64bfae3`
- no manual conflict resolution was required
- unified stack script on `feature/codex-merge-rehearsal-c29c30c31`: `485 passed, 172 warnings in 15.85s`
- `git diff --check`: passed

### Residual Risks
- warnings remain the existing `starlette.formparsers` and `httpx app=` deprecations
- no app registration or hot-path integration has been performed yet, by design

## Increment 2026-03-19 Codex-Merge-Rehearsal-C26-C27-C28

### Touched Areas
- `feature/codex-c26c27c28-staging`
- `feature/codex-merge-rehearsal-c26c27c28`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`

### Verification Commands
```bash
git merge --ff-only feature/codex-c26c27c28-staging
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-merge-c26c27c28-full PYTEST_ADDOPTS='-p no:cacheprovider' \
  scripts/verify_odoo18_plm_stack.sh full
```

```bash
git diff --check
```

### Actual Results
- rehearsal branch fast-forwarded from `d068476` to `019e874`
- no manual conflict resolution was required
- unified stack script on `feature/codex-merge-rehearsal-c26c27c28`: `440 passed, 156 warnings in 13.61s`
- `git diff --check`: passed

### Residual Risks
- warnings remain the existing `starlette.formparsers` and `httpx app=` deprecations
- actual `main` has not been advanced yet at this point in the timeline

## Increment 2026-03-19 Main-FastForward-C26-C27-C28

### Touched Areas
- `main`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`

### Verification Commands
```bash
git merge --ff-only feature/codex-c26c27c28-staging
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-main-c26c27c28-postfull PYTEST_ADDOPTS='-p no:cacheprovider' \
  scripts/verify_odoo18_plm_stack.sh full
```

```bash
git diff --check
```

### Actual Results
- `main` fast-forwarded from `d068476` to `129e773`
- post-merge unified stack rerun on `main`: `440 passed, 156 warnings in 13.96s`
- `git diff --check`: passed

### Residual Risks
- warnings remain the existing `starlette.formparsers` and `httpx app=` deprecations
- no new post-merge functional regression was observed

## Increment 2026-03-19 Main-Stability-Refresh-C26-C27-C28

### Touched Areas
- `main`
- no functional code changes; verification-only stability pass

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-main-c26c27c28-stability-target PYTEST_ADDOPTS='-p no:cacheprovider' pytest -q \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_service.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-main-c26c27c28-stability-full PYTEST_ADDOPTS='-p no:cacheprovider' \
  scripts/verify_odoo18_plm_stack.sh full
```

### Actual Results
- targeted greenfield stability rerun on `main`: `222 passed, 82 warnings in 2.12s`
- unified stack stability rerun on `main`: `440 passed, 156 warnings in 12.63s`

### Residual Risks
- warnings remain the existing `starlette.formparsers` and `httpx app=` deprecations
- no new stability-window regression was observed

## Increment 2026-03-19 Codex-Prepare-Next-Claude-Batch-C29-C31

### Touched Areas
- `main`
- `contracts/claude_allowed_paths.json`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DESIGN_PARALLEL_C29_PLM_BOX_CAPACITY_COMPLIANCE_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C29_PLM_BOX_CAPACITY_COMPLIANCE_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C30_DOCUMENT_SYNC_DRIFT_SNAPSHOTS_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C30_DOCUMENT_SYNC_DRIFT_SNAPSHOTS_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C31_CUTTED_PARTS_BENCHMARK_QUOTE_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C31_CUTTED_PARTS_BENCHMARK_QUOTE_BOOTSTRAP_20260319.md`

### Verification Commands
```bash
python3 -m json.tool contracts/claude_allowed_paths.json >/dev/null
```

```bash
git diff --check
```

### Actual Results
- added path-guard profiles `C29`, `C30`, `C31`
- created frozen Claude base branch `feature/claude-greenfield-base-5`
- prepared shared PLAN / DESIGN / VERIFICATION entries for the next Claude batch
- added standalone design / verification templates for `C29/C30/C31`

### Residual Risks
- this preparation step itself introduces no code changes
- the next Claude batch should still stay off `src/yuantus/api/app.py` and all integrated hot routers outside their own domains

## Increment 2026-03-19 Codex-C29-C30-Stack-Verification

### Touched Areas
- `feature/codex-c29c30-staging`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C29_PLM_BOX_CAPACITY_COMPLIANCE_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C30_DOCUMENT_SYNC_DRIFT_SNAPSHOTS_BOOTSTRAP_20260319.md`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c29c30 python3 -m py_compile \
  src/yuantus/meta_engine/box/service.py \
  src/yuantus/meta_engine/web/box_router.py \
  src/yuantus/meta_engine/document_sync/service.py \
  src/yuantus/meta_engine/web/document_sync_router.py \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c29c30-target PYTEST_ADDOPTS='-p no:cacheprovider' pytest -q \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c29c30-full PYTEST_ADDOPTS='-p no:cacheprovider' \
  scripts/verify_odoo18_plm_stack.sh full
```

```bash
git diff --check
```

### Actual Results
- cherry-picked `ab909e4` into staging as `31e59bb`
- cherry-picked `b0b27b0` into staging as `6fcf9be`
- `py_compile`: passed
- combined targeted regression: `169 passed, 66 warnings in 2.17s`
- unified stack script on `feature/codex-c29c30-staging`: `469 passed, 167 warnings in 12.95s`
- `git diff --check`: passed

### Residual Risks
- warnings remain the existing `starlette.formparsers` and `httpx app=` deprecations
- `C31` had not been integrated yet at this point in the timeline

## Increment 2026-03-19 Codex-C31-Stack-Verification

### Touched Areas
- `feature/codex-c29c30c31-staging`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C31_CUTTED_PARTS_BENCHMARK_QUOTE_BOOTSTRAP_20260319.md`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c29c30c31 python3 -m py_compile \
  src/yuantus/meta_engine/box/service.py \
  src/yuantus/meta_engine/web/box_router.py \
  src/yuantus/meta_engine/document_sync/service.py \
  src/yuantus/meta_engine/web/document_sync_router.py \
  src/yuantus/meta_engine/cutted_parts/service.py \
  src/yuantus/meta_engine/web/cutted_parts_router.py \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_service.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c29c30c31-target PYTEST_ADDOPTS='-p no:cacheprovider' pytest -q \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_service.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c29c30c31-full PYTEST_ADDOPTS='-p no:cacheprovider' \
  scripts/verify_odoo18_plm_stack.sh full
```

```bash
git diff --check
```

### Actual Results
- cherry-picked `c190634` into staging as `4f2e54b`
- `py_compile`: passed
- combined targeted regression with `C29/C30/C31`: `267 passed, 98 warnings in 3.61s`
- unified stack script on `feature/codex-c29c30c31-staging`: `485 passed, 172 warnings in 14.77s`
- `git diff --check`: passed

### Residual Risks
- warnings remain the existing `starlette.formparsers` and `httpx app=` deprecations

## Increment 2026-03-19 Main-FastForward-C20-C21-C22

### Touched Areas
- `main`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-main-c20c21c22 PYTEST_ADDOPTS='-p no:cacheprovider' scripts/verify_odoo18_plm_stack.sh full
```

### Actual Results
- `main` fast-forwarded from `dd4b72a` to `aebdc09`
- unified stack script on merged `main`: `351 passed, 123 warnings in 30.86s`

### Residual Risks
- warnings remain the existing `starlette.formparsers` and `httpx app=` deprecations

## Increment 2026-03-19 Main-Stability-Refresh-C20-C21-C22

### Touched Areas
- `main`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-main-stability PYTEST_ADDOPTS='-p no:cacheprovider' scripts/verify_odoo18_plm_stack.sh full
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-main-broader PYTEST_ADDOPTS='-p no:cacheprovider' pytest -q \
  src/yuantus/meta_engine/tests/test_bom_summarized_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_compare_router.py \
  src/yuantus/meta_engine/tests/test_bom_delta_preview.py \
  src/yuantus/meta_engine/tests/test_bom_delta_router.py \
  src/yuantus/meta_engine/tests/test_quality_service.py \
  src/yuantus/meta_engine/tests/test_quality_analytics_service.py \
  src/yuantus/meta_engine/tests/test_quality_analytics_router.py \
  src/yuantus/meta_engine/tests/test_quality_spc_service.py \
  src/yuantus/meta_engine/tests/test_quality_router.py \
  src/yuantus/meta_engine/tests/test_maintenance_service.py \
  src/yuantus/meta_engine/tests/test_maintenance_router.py \
  src/yuantus/meta_engine/tests/test_locale_service.py \
  src/yuantus/meta_engine/tests/test_report_locale_service.py \
  src/yuantus/meta_engine/tests/test_locale_router.py \
  src/yuantus/meta_engine/tests/test_subcontracting_service.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_service.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py
```

### Actual Results
- merged-`main` unified stack rerun: `351 passed, 123 warnings in 42.37s`
- merged-`main` broader rerun: `351 passed, 123 warnings in 42.32s`
- no new post-merge defect surfaced during the stabilization refresh

### Residual Risks
- warnings remain the existing `starlette.formparsers` and `httpx app=` deprecations

## Increment 2026-03-19 Codex-Prepare-Next-Claude-Batch-C23-C25

### Touched Areas
- `main`
- `contracts/claude_allowed_paths.json`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DESIGN_PARALLEL_C23_PLM_BOX_OPS_REPORT_TRANSITIONS_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C23_PLM_BOX_OPS_REPORT_TRANSITIONS_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C24_DOCUMENT_SYNC_RECONCILIATION_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C24_DOCUMENT_SYNC_RECONCILIATION_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C25_CUTTED_PARTS_COST_UTILIZATION_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C25_CUTTED_PARTS_COST_UTILIZATION_BOOTSTRAP_20260319.md`

### Verification Commands
```bash
python3 -m json.tool contracts/claude_allowed_paths.json >/dev/null
```

```bash
git diff --check
```

### Actual Results
- added path-guard profiles `C23`, `C24`, `C25`
- created frozen Claude base branch `feature/claude-greenfield-base-3`
- prepared shared PLAN / DESIGN / VERIFICATION entries for the next Claude batch
- added standalone design / verification templates for `C23/C24/C25`

### Residual Risks
- `C23/C24/C25` are task-prep only at this stage; no implementation has been started
- the next Claude batch should still stay off `src/yuantus/api/app.py` and all integrated hot routers outside their own domains

## Increment 2026-03-19 Codex-C23-C24-Stack-Verification

### Touched Areas
- `feature/codex-c23c24-staging`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C23_PLM_BOX_OPS_REPORT_TRANSITIONS_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C24_DOCUMENT_SYNC_RECONCILIATION_BOOTSTRAP_20260319.md`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c23c24 python3 -m py_compile \
  src/yuantus/meta_engine/box/service.py \
  src/yuantus/meta_engine/web/box_router.py \
  src/yuantus/meta_engine/document_sync/service.py \
  src/yuantus/meta_engine/web/document_sync_router.py
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c23c24 PYTEST_ADDOPTS='-p no:cacheprovider' pytest -q \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py
```

```bash
git diff --check
```

### Actual Results
- cherry-picked `48af7e3` into staging as `585d5f3`
- cherry-picked `00df973` into staging as `7ab31dc`
- `py_compile`: passed
- combined targeted regression: `111 passed, 44 warnings in 3.99s`
- unified stack script on `feature/codex-c23c24-staging`: `379 passed, 134 warnings in 31.56s`
- `git diff --check`: passed

### Residual Risks
- warnings remain the existing `starlette.formparsers` and `httpx app=` deprecations
- `C25` had not been integrated yet at this point in the timeline

## Increment 2026-03-19 Codex-C25-Integration

### Touched Areas
- `feature/codex-c23c24c25-staging`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C25_CUTTED_PARTS_COST_UTILIZATION_BOOTSTRAP_20260319.md`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c23c24c25 python3 -m py_compile \
  src/yuantus/meta_engine/cutted_parts/service.py \
  src/yuantus/meta_engine/web/cutted_parts_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_service.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c23c24c25 PYTEST_ADDOPTS='-p no:cacheprovider' pytest -q \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_service.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c23c24c25-full PYTEST_ADDOPTS='-p no:cacheprovider' scripts/verify_odoo18_plm_stack.sh full
```

```bash
git diff --check
```

### Actual Results
- cherry-picked `30b7d3b` into staging as `b2fec86`
- `py_compile`: passed
- combined greenfield regression with `C23+C24+C25`: `178 passed, 66 warnings in 3.62s`
- unified stack script on `feature/codex-c23c24c25-staging`: `396 passed, 140 warnings in 15.87s`
- `git diff --check`: passed

### Residual Risks
- warnings remain the existing `starlette.formparsers` and `httpx app=` deprecations
- no app registration or hot-path integration has been performed yet, by design

## Increment 2026-03-19 Main-FastForward-C23-C24-C25

### Touched Areas
- `main`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-main-c23c24c25-postfull PYTEST_ADDOPTS='-p no:cacheprovider' \
  scripts/verify_odoo18_plm_stack.sh full
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-main-c23c24c25-postbroad PYTEST_ADDOPTS='-p no:cacheprovider' pytest -q \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_service.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py \
  src/yuantus/meta_engine/tests/test_locale_router.py \
  src/yuantus/meta_engine/tests/test_quality_router.py \
  src/yuantus/meta_engine/tests/test_quality_analytics_router.py \
  src/yuantus/meta_engine/tests/test_maintenance_router.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py
```

```bash
git diff --check
```

### Actual Results
- `main` already fast-forwarded to `88abb79` from the verified staging lineage
- post-merge unified stack rerun on `main`: `396 passed, 140 warnings in 11.78s`
- post-merge broader rerun on `main`: `249 passed, 122 warnings in 9.26s`
- `git diff --check`: passed

### Residual Risks
- warnings remain the existing `starlette.formparsers` and `httpx app=` deprecations
- no new post-merge functional regression was observed

## Increment 2026-03-19 Codex-Prepare-Next-Claude-Batch-C26-C28

### Touched Areas
- `main`
- `contracts/claude_allowed_paths.json`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DESIGN_PARALLEL_C26_PLM_BOX_RECONCILIATION_AUDIT_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C26_PLM_BOX_RECONCILIATION_AUDIT_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C27_DOCUMENT_SYNC_REPLAY_AUDIT_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C27_DOCUMENT_SYNC_REPLAY_AUDIT_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C28_CUTTED_PARTS_TEMPLATES_SCENARIOS_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C28_CUTTED_PARTS_TEMPLATES_SCENARIOS_BOOTSTRAP_20260319.md`

### Verification Commands
```bash
python3 -m json.tool contracts/claude_allowed_paths.json >/dev/null
```

```bash
git diff --check
```

### Actual Results
- added path-guard profiles `C26`, `C27`, `C28`
- created frozen Claude base branch `feature/claude-greenfield-base-4`
- prepared shared PLAN / DESIGN / VERIFICATION entries for the next Claude batch
- added standalone design / verification templates for `C26/C27/C28`

### Residual Risks
- `C26/C27/C28` are task-prep only at this stage; no implementation has been started
- the next Claude batch should still stay off `src/yuantus/api/app.py` and all integrated hot routers outside their own domains

## Increment 2026-03-19 Codex-C26-C27-Stack-Verification

### Touched Areas
- `feature/codex-c26c27-staging`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C26_PLM_BOX_RECONCILIATION_AUDIT_BOOTSTRAP_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C27_DOCUMENT_SYNC_REPLAY_AUDIT_BOOTSTRAP_20260319.md`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c26c27 python3 -m py_compile \
  src/yuantus/meta_engine/box/service.py \
  src/yuantus/meta_engine/web/box_router.py \
  src/yuantus/meta_engine/document_sync/service.py \
  src/yuantus/meta_engine/web/document_sync_router.py \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c26c27-target PYTEST_ADDOPTS='-p no:cacheprovider' pytest -q \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c26c27-full PYTEST_ADDOPTS='-p no:cacheprovider' \
  scripts/verify_odoo18_plm_stack.sh full
```

```bash
git diff --check
```

### Actual Results
- cherry-picked `77b5d4d` into staging as `37e81be`
- cherry-picked `608d4cd` into staging as `f828406`
- `py_compile`: passed
- combined targeted regression: `140 passed, 55 warnings in 2.35s`
- unified stack script on `feature/codex-c26c27-staging`: `425 passed, 151 warnings in 13.34s`
- `git diff --check`: passed

### Residual Risks
- warnings remain the existing `starlette.formparsers` and `httpx app=` deprecations
- `C28` had not been integrated yet at this point in the timeline

## Increment 2026-03-19 Codex-C28-Integration

### Touched Areas
- `feature/codex-c26c27c28-staging`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_C28_CUTTED_PARTS_TEMPLATES_SCENARIOS_BOOTSTRAP_20260319.md`

### Verification Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c26c27c28 python3 -m py_compile \
  src/yuantus/meta_engine/box/service.py \
  src/yuantus/meta_engine/web/box_router.py \
  src/yuantus/meta_engine/document_sync/service.py \
  src/yuantus/meta_engine/web/document_sync_router.py \
  src/yuantus/meta_engine/cutted_parts/service.py \
  src/yuantus/meta_engine/web/cutted_parts_router.py \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_service.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c26c27c28-target PYTEST_ADDOPTS='-p no:cacheprovider' pytest -q \
  src/yuantus/meta_engine/tests/test_box_service.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_service.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_service.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py
```

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-c26c27c28-full PYTEST_ADDOPTS='-p no:cacheprovider' \
  scripts/verify_odoo18_plm_stack.sh full
```

```bash
git diff --check
```

### Actual Results
- cherry-picked `13c8c90` into staging as `fabc2b5`
- `py_compile`: passed
- combined greenfield regression with `C26+C27+C28`: `222 passed, 82 warnings in 3.75s`
- unified stack script on `feature/codex-c26c27c28-staging`: `440 passed, 156 warnings in 13.91s`
- `git diff --check`: passed

### Residual Risks
- warnings remain the existing `starlette.formparsers` and `httpx app=` deprecations
- no app registration or hot-path integration has been performed yet, by design
