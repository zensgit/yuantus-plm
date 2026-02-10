# CI/Regression Change Scope Debugging (Reasons + Local Script + PR Cost Rule) (2026-02-10)

## Goals

- Make CI/regression gating decisions easy to debug:
  - show *why* a job is enabled/disabled (first matched rule + file)
  - show a truncated list of changed files in the workflow job summary
- Provide a local reproduction tool to avoid “push to see what runs”.
- Reduce PR CI cost: workflow-only edits to `regression.yml` should not trigger heavy runs by default.

## Changes

### 1) Better step summaries (GitHub Actions)

- `.github/workflows/ci.yml` (`detect_changes (CI)`):
  - Add `run_*_reason` fields
  - Add `Changed Files (first 50)` section
- `.github/workflows/regression.yml` (`detect_changes (regression)`):
  - Add `cadgf_reason`, `regression_reason`, `regression_workflow_changed`
  - Add `Changed Files (first 50)` section

### 2) Local debug script

- Added `scripts/ci_change_scope_debug.sh`
  - Computes changed files from `origin/main...HEAD` (merge-base) by default
  - Prints CI flags: `run_plugin_tests`, `run_playwright`, `run_contracts`
  - Prints regression flags: `cadgf_changed`, `regression_needed`
  - Supports simulation flags:
    - `--force-full` (ci:full)
    - `--force-regression`
    - `--force-cadgf`
    - `--event pull_request|push`

### 3) PR cost rule for workflow-only regression edits

- `.github/workflows/regression.yml`:
  - For PRs, `.github/workflows/regression.yml` changes alone no longer trigger:
    - `regression_needed=true`
    - `cadgf_changed=true`
  - Use labels `regression:force` / `cadgf:force` / `ci:full` or `workflow_dispatch` to force.

### 4) Documentation + contracts

- Updated `docs/RUNBOOK_CI_CHANGE_SCOPE.md`:
  - Document new summary fields
  - Document `scripts/ci_change_scope_debug.sh`
  - Document the PR workflow-only skip rule for `regression.yml`
- Updated shell syntax contracts:
  - `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py` now includes `scripts/ci_change_scope_debug.sh`

## Verification (Local)

1) Contracts suite (same set as CI `contracts` job):

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_perf_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_label_override_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_perf_gate_config_file.py \
  src/yuantus/meta_engine/tests/test_perf_ci_baseline_downloader_script.py \
  src/yuantus/meta_engine/tests/test_readme_runbook_references.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result (2026-02-10): `10 passed`.

2) YAML parse sanity:

```bash
python3 - <<'PY'
from pathlib import Path
import yaml

workflows = sorted(Path(".github/workflows").glob("*.y*ml"))
for wf in workflows:
    yaml.safe_load(wf.read_text(encoding="utf-8", errors="replace"))
print(f"workflow_yaml_ok={len(workflows)}")
PY
```

Result (2026-02-10): `workflow_yaml_ok=5`.

3) Local debug script smoke:

```bash
scripts/ci_change_scope_debug.sh --help
scripts/ci_change_scope_debug.sh --show-files
```

Result (2026-02-10): both commands exit `0`.
