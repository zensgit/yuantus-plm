# Dev & Verification Report - CI/Regression Change Scope Runbook + Release Orchestration Script (2026-02-10)

This delivery improves:

- **CI control**: document and force full runs when change-scope detection would skip heavy jobs.
- **Regression efficiency**: cancel in-progress regression workflow runs on the same ref.
- **Ops ergonomics**: provide a one-command helper script for release orchestration (plan/execute).

## Changes

### 1) Regression workflow-level concurrency

- `.github/workflows/regression.yml`
  - Add workflow-level `concurrency`:
    - `group: ${{ github.workflow }}-${{ github.ref }}`
    - `cancel-in-progress: true`

This cancels older in-progress runs when a newer commit arrives on the same PR/ref.

### 2) CI workflow_dispatch for forcing full runs

- `.github/workflows/ci.yml`
  - Add `workflow_dispatch` trigger.

This enables running the `CI` workflow manually on a PR branch to get **full plugin-tests + playwright + contracts**, even when PR change-scope detection would normally skip them.

### 3) Runbook: skip rules + how to force full runs

- New: `docs/RUNBOOK_CI_CHANGE_SCOPE.md`
  - Documents:
    - what `detect_changes (CI)` / `detect_changes (regression)` decide
    - where to inspect decisions (`GITHUB_STEP_SUMMARY`)
    - how to force full runs (recommended: `workflow_dispatch`)
- Linked from:
  - `README.md`
  - `docs/DELIVERY_DOC_INDEX.md`

### 4) Release orchestration helper script

- New: `scripts/release_orchestration.sh`
  - `plan` and `execute` wrapper around:
    - `GET /api/v1/release-orchestration/items/{item_id}/plan`
    - `POST /api/v1/release-orchestration/items/{item_id}/execute`
  - Writes outputs to `tmp/release-orchestration/<timestamp>/...json` by default.
- `docs/RUNBOOK_RELEASE_ORCHESTRATION.md`
  - Adds a section to recommend the script for day-to-day use.

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
  src/yuantus/meta_engine/tests/test_perf_gate_config_file.py \
  src/yuantus/meta_engine/tests/test_perf_ci_baseline_downloader_script.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Shell helper sanity:

```bash
bash -n scripts/release_orchestration.sh
scripts/release_orchestration.sh --help
```

Result:

- YAML load: OK
- Pytest: `5 passed`
- Script: `--help` exit 0
