# CI Contracts: Runbook Index Completeness + Change Scope Summaries (2026-02-10)

## Goals

- Prevent drift: any new `docs/RUNBOOK_*.md` must be indexed in:
  - `README.md` (`## Runbooks`)
  - `docs/DELIVERY_DOC_INDEX.md` (`## Ops & Deployment`)
- Make CI / regression gating decisions easier to debug by including a truncated changed-files list in the `detect_changes` job summary.

## Changes

- CI change-scope summaries:
  - `.github/workflows/ci.yml`: add `Changed Files (first 50)` section to the `detect_changes (CI)` job summary.
  - `.github/workflows/regression.yml`: add `Changed Files (first 50)` section to the `detect_changes (regression)` job summary.
- Contracts:
  - Added `src/yuantus/meta_engine/tests/test_runbook_index_completeness.py`:
    - enumerates `docs/RUNBOOK_*.md`
    - asserts each runbook is referenced in `README.md` Runbooks section (backticked path)
    - asserts each runbook is referenced in `docs/DELIVERY_DOC_INDEX.md` (backticked path)
  - Wired the new test into `.github/workflows/ci.yml` `contracts` job.
- Indexing:
  - Added this document to `docs/DELIVERY_DOC_INDEX.md`.

## Verification (Local)

Ran the same contracts suite as the CI `contracts` job:

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

Additionally validated that all workflow YAML files parse:

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
