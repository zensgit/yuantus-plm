# CI Contracts: Contracts Job Wiring Guard (2026-02-10)

## Goal

Prevent silent drift where new contract tests are added in `src/yuantus/meta_engine/tests/`
but not wired into `.github/workflows/ci.yml` `contracts` job.

## Changes

- Added contract test: `src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py`
  - Parses the `Contract checks (perf workflows + delivery doc index)` step in `.github/workflows/ci.yml`
  - Requires all `test_*contracts*.py` files to be included in that step
  - Requires explicit contract-adjacent checks to be included:
    - `test_ci_shell_scripts_syntax.py`
    - `test_perf_gate_config_file.py`
    - `test_perf_ci_baseline_downloader_script.py`
    - `test_readme_runbook_references.py`
    - `test_readme_runbooks_are_indexed_in_delivery_doc_index.py`
    - `test_runbook_index_completeness.py`
    - `test_dev_and_verification_doc_index_completeness.py`
    - `test_delivery_doc_index_references.py`
  - Fails if the CI list contains stale/nonexistent test file paths
- Updated `.github/workflows/ci.yml` to execute the new contract test in `contracts` job.

## Verification

```bash
python3 -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py

python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_perf_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_label_override_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_change_scope_contracts.py \
  src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_perf_gate_config_file.py \
  src/yuantus/meta_engine/tests/test_perf_ci_baseline_downloader_script.py \
  src/yuantus/meta_engine/tests/test_readme_runbook_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: PASS

