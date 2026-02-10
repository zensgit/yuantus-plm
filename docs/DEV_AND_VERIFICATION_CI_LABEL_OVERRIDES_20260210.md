# Dev & Verification Report - CI/Regression Label Overrides (2026-02-10)

This delivery adds **PR label overrides** so maintainers can force heavy CI jobs to run inside PR checks (without editing code paths to "hit" a trigger), and documents the behavior in an ops runbook.

## Changes

### 1) CI workflow: label `ci:full` forces all jobs

- `.github/workflows/ci.yml`
  - `detect_changes (CI)` now supports:
    - `ci:full` → `run_plugin_tests=true`, `run_playwright=true`, `run_contracts=true`
  - The job summary includes `force_full (label ci:full)` for quick debugging.

### 2) Regression workflow: force labels for integration + CADGF

- `.github/workflows/regression.yml`
  - `detect_changes (regression)` now supports PR-only overrides:
    - `ci:full` → `regression_needed=true` and `cadgf_changed=true`
    - `regression:force` → `regression_needed=true`
    - `cadgf:force` → `cadgf_changed=true`
  - The job summary includes `force_*` fields.

### 3) Runbook: document overrides + gh CLI examples

- `docs/RUNBOOK_CI_CHANGE_SCOPE.md`
  - Added sections:
    - PR Label Overrides (CI + regression)
    - `gh workflow run ...` examples for `workflow_dispatch`
    - `gh pr edit ... --add-label ...` examples

### 4) Contract test: keep docs/workflows aligned

- `src/yuantus/meta_engine/tests/test_workflow_label_override_contracts.py`
- `.github/workflows/ci.yml`
  - `contracts` job runs this test to prevent regressions.

## Verification

YAML sanity:

```bash
ruby -ryaml -e 'YAML.load_file(%q(.github/workflows/ci.yml))'
ruby -ryaml -e 'YAML.load_file(%q(.github/workflows/regression.yml))'
```

Targeted pytest (contracts):

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_perf_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_label_override_contracts.py \
  src/yuantus/meta_engine/tests/test_perf_gate_config_file.py \
  src/yuantus/meta_engine/tests/test_perf_ci_baseline_downloader_script.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

- YAML load: OK
- Pytest: `6 passed`
