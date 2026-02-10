# CI Contracts: Run Contracts When Scripts Change (2026-02-10)

## Goals

- Ensure CI `contracts` runs when operational scripts change, so the shell-script syntax contracts can catch regressions early.
- Keep local change-scope debug tooling aligned with CI behavior.

## Changes

- `.github/workflows/ci.yml`:
  - `detect_changes (CI)` now sets `run_contracts=true` when PR changes include:
    - `scripts/*.sh` or `scripts/*.py`
- `scripts/ci_change_scope_debug.sh`:
  - mirrors the same `scripts/*.sh|scripts/*.py` => `run_contracts=true` rule
- Contracts:
  - Added `src/yuantus/meta_engine/tests/test_ci_change_scope_contracts.py`
    - asserts CI workflow includes the scripts trigger
    - asserts CI job summary includes reason fields
    - asserts the local debug script is documented in `docs/RUNBOOK_CI_CHANGE_SCOPE.md`
    - asserts regression workflow keeps `regression_workflow_changed` (PR cost rule wiring)
  - Wired this new test into `.github/workflows/ci.yml` `contracts` job.

## Verification (Local)

1) Contracts suite:

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_perf_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_label_override_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_change_scope_contracts.py \
  src/yuantus/meta_engine/tests/test_perf_gate_config_file.py \
  src/yuantus/meta_engine/tests/test_perf_ci_baseline_downloader_script.py \
  src/yuantus/meta_engine/tests/test_readme_runbook_references.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result (2026-02-10): `11 passed`.

2) Workflow YAML parse sanity:

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
