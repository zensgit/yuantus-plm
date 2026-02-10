# Strict Gate: Script --help + CI Job Summary Download Hints (2026-02-10)

## Goals

- Make `scripts/strict_gate_report.sh` self-documenting (`--help`) to reduce runbook drift and enable CLI-first usage.
- Make strict-gate CI runs easier to triage by printing copy/paste `gh run download` commands at the top of the Job Summary.

## Changes

- Script:
  - `scripts/strict_gate_report.sh` now supports `--help` (prints usage + key environment variables; exits 0).
  - Added argument validation: unexpected args print usage and exit 2.
- CI workflow summary:
  - `.github/workflows/strict-gate.yml` now writes a short "Strict Gate Artifacts" section to `$GITHUB_STEP_SUMMARY` (always),
    including:
    - `gh run download <run_id> -n strict-gate-report`
    - `gh run download <run_id> -n strict-gate-logs`
- Contracts:
  - `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py` now asserts `scripts/strict_gate_report.sh --help` returns 0 and contains expected tokens.
  - `src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py` now asserts the workflow includes `gh run download` hints.

## Verification (Local)

1) Script help:

```bash
scripts/strict_gate_report.sh --help
```

Result (2026-02-10): exit `0`.

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

3) Contracts checks (same set as CI `contracts` job):

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
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result (2026-02-10): `14 passed`.
