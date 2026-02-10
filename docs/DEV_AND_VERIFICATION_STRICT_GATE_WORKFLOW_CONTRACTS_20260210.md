# Strict Gate: Runbook CLI + Workflow Contracts (2026-02-10)

## Goals

- Make strict-gate runnable and triageable without the GitHub UI (CLI-first).
- Freeze the strict-gate workflow wiring (report path, artifact names, script invocation) via CI contracts, so ops flows cannot silently break.

## Changes

- Runbook:
  - Updated `docs/RUNBOOK_STRICT_GATE.md` with:
    - `gh workflow run strict-gate --ref <branch> ...`
    - `gh run list --workflow strict-gate ...`
    - `gh run download ...` (artifacts)
    - Notes on where the report/logs live after extraction.
- Contracts:
  - Added `src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py`
    - checks `.github/workflows/strict-gate.yml` includes:
      - scheduled trigger + workflow_dispatch input wiring
      - concurrency config
      - `scripts/strict_gate_report.sh` invocation
      - report/log output paths and artifact names (`strict-gate-report`, `strict-gate-logs`)
    - checks `docs/RUNBOOK_STRICT_GATE.md` documents the CLI flow and artifact names
  - Wired the new test into `.github/workflows/ci.yml` `contracts` job.

## Verification (Local)

1) Workflow YAML parse sanity:

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

2) Contracts suite (same set as CI `contracts` job):

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_perf_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_label_override_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_change_scope_contracts.py \
  src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_perf_gate_config_file.py \
  src/yuantus/meta_engine/tests/test_perf_ci_baseline_downloader_script.py \
  src/yuantus/meta_engine/tests/test_readme_runbook_references.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result (2026-02-10): `12 passed`.
