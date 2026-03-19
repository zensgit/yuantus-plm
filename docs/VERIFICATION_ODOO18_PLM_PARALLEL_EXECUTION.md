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
