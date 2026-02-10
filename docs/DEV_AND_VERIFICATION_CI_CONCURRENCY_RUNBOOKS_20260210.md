# Dev & Verification Report - CI Concurrency + Runbooks (2026-02-10)

This delivery tightens CI usability and operational discoverability:

- Add workflow-level `concurrency` to cancel in-progress runs on the same PR/ref (reduces wasted CI minutes).
- Add an ops-grade runbook for **Release Orchestration** (plan + execute).
- Extend the perf gate config runbook with CI triage locations (job summary + artifacts).

## Changes

### 1) CI concurrency (cancel in-progress runs per ref)

- `.github/workflows/ci.yml`
  - Add workflow-level `concurrency`:
    - `group: ${{ github.workflow }}-${{ github.ref }}`
    - `cancel-in-progress: true`
- `.github/workflows/strict-gate.yml`
  - Add workflow-level `concurrency` (same pattern).

### 2) Concurrency contract test (keeps it from regressing)

- `src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py`
  - Ensures key workflows define `concurrency` with `cancel-in-progress: true`.
- `.github/workflows/ci.yml`
  - `contracts` job now runs this test.

### 3) Release orchestration runbook + discoverability

- New: `docs/RUNBOOK_RELEASE_ORCHESTRATION.md`
  - Covers:
    - `GET /api/v1/release-orchestration/items/{item_id}/plan`
    - `POST /api/v1/release-orchestration/items/{item_id}/execute` (dry-run / rollback)
    - status meanings and common errors
- Linked from:
  - `README.md`
  - `docs/DELIVERY_DOC_INDEX.md`

### 4) Perf gate runbook: CI triage pointers

- `docs/RUNBOOK_PERF_GATE_CONFIG.md`
  - Add where to look in CI (`GITHUB_STEP_SUMMARY`) and artifact names for gate logs/reports.

## Verification

YAML sanity (workflows):

```bash
ruby -ryaml -e 'YAML.load_file(%q(.github/workflows/ci.yml))'
ruby -ryaml -e 'YAML.load_file(%q(.github/workflows/strict-gate.yml))'
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

Result:

- YAML load: OK
- Pytest: `5 passed`
