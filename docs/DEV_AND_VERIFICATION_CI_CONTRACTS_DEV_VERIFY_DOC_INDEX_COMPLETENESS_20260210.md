# CI Contracts: Dev & Verification Doc Index Completeness (2026-02-10)

## Goal

Keep `docs/DELIVERY_DOC_INDEX.md` as a reliable entrypoint by ensuring every evidence doc matching
`docs/DEV_AND_VERIFICATION_*.md` is listed under the `## Development & Verification` section.

## Changes

- Added a CI contract test:
  - `src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py`
- Updated the index section to include the previously missing Week Plan evidence docs:
  - `docs/DEV_AND_VERIFICATION_WEEK_PLAN_20260202.md`
  - `docs/DEV_AND_VERIFICATION_WEEK_PLAN_20260202_FEATURES2.md`
  - `docs/DEV_AND_VERIFICATION_WEEK_PLAN_20260203_ENHANCEMENTS.md`

## Verification

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py

# Full contracts suite (matches .github/workflows/ci.yml "contracts" job)
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_perf_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_label_override_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_change_scope_contracts.py \
  src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_perf_gate_config_file.py \
  src/yuantus/meta_engine/tests/test_perf_ci_baseline_downloader_script.py \
  src/yuantus/meta_engine/tests/test_readme_runbook_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: PASS

