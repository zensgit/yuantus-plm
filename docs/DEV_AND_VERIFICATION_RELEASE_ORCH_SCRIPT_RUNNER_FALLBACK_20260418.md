# Dev & Verification Report - Release Orchestration Script Runner Fallback (2026-04-18)

## Goal

Harden the real script execution path for release orchestration verification after the repository path moved, so the helper and verification scripts still run when `.venv` wrapper shebangs point at an old workspace path.

## Background

The first contract layer was green:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_perf_smokes.py
```

Result:

```text
12 passed in 0.25s
```

But the real script execution layer failed immediately:

```bash
OUT_DIR="$(pwd)/tmp/verify-release-orchestration-manual" \
  bash scripts/verify_release_orchestration.sh
```

and

```bash
OUT_DIR="$(pwd)/tmp/verify-release-orchestration-perf-manual" \
  PERF_RELEASE_ORCH_SAMPLES=5 \
  bash scripts/verify_release_orchestration_perf_smoke.sh
```

Both died with:

```text
... .venv/bin/yuantus: ... bad interpreter: No such file or directory
```

Root cause:

- `.venv/bin/yuantus` and `.venv/bin/uvicorn` still had shebangs pointing to the old path:
  - `#!/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/python`
- the scripts only checked whether the wrapper files were executable, not whether they were actually runnable

An initial fallback to `python -m yuantus.cli` was also invalid for this repo shape:

- it returned `0`
- but did not invoke `main()`
- so `seed-identity` / `seed-meta` silently did nothing
- the scripts then failed later at login with `401 Invalid credentials`

## Scope

- `scripts/verify_release_orchestration.sh`
- `scripts/verify_release_orchestration_perf_smoke.sh`
- `docs/DEV_AND_VERIFICATION_RELEASE_ORCH_SCRIPT_RUNNER_FALLBACK_20260418.md`
- `docs/DELIVERY_DOC_INDEX.md`

## Remediation

In both verification scripts:

1. Keep the existing preference for local `.venv` wrappers when they are truly runnable.
2. Upgrade the fallback check from “is executable” to “can actually run”.
3. For `yuantus`, fall back to:

```bash
PYTHONPATH=src .venv/bin/python -c 'from yuantus.cli import main; main()'
```

instead of:

```bash
PYTHONPATH=src .venv/bin/python -m yuantus.cli
```

4. For `uvicorn`, fall back to:

```bash
PYTHONPATH=src .venv/bin/python -m uvicorn
```

This keeps the scripts resilient when the repo is moved or copied and old wrapper shebangs become stale.

## Verification

### 1. Script / CI contract layer

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_perf_smokes.py
```

Result:

```text
12 passed in 0.25s
```

### 2. Shell syntax

```bash
bash -n \
  scripts/verify_release_orchestration.sh \
  scripts/verify_release_orchestration_perf_smoke.sh
```

Result: pass.

### 3. Real script execution: orchestration E2E

```bash
OUT_DIR="$(pwd)/tmp/verify-release-orchestration-manual" \
  bash scripts/verify_release_orchestration.sh
```

Result:

```text
[19:59:58] ALL CHECKS PASSED out=/Users/chouhua/Downloads/Github/Yuantus/tmp/verify-release-orchestration-manual
```

Key evidence from the run:

- `plan_steps_total=3 requires_esign=1`
- `execute_results_total=5 missing_required=0`
- `mbom.state=released`

### 4. Real script execution: perf smoke

```bash
OUT_DIR="$(pwd)/tmp/verify-release-orchestration-perf-manual" \
  PERF_RELEASE_ORCH_SAMPLES=5 \
  bash scripts/verify_release_orchestration_perf_smoke.sh
```

Result:

```text
[19:59:57] ALL CHECKS PASSED out=/Users/chouhua/Downloads/Github/Yuantus/tmp/verify-release-orchestration-perf-manual
```

Measured output:

```text
release_orchestration.plan: samples=5 p50=5.734ms p95=12.897ms threshold=1800.000ms
release_orchestration.execute_dry_run: samples=5 p50=7.268ms p95=9.882ms threshold=2200.000ms
metrics_summary: OK
```

### 5. Documentation index contracts

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py
```

Result:

```text
5 passed in 0.02s
```

## Conclusion

- The failure was in the verification toolchain runner resolution, not in release orchestration business logic.
- The verification scripts now survive stale `.venv` wrapper shebangs after workspace relocation.
- Both real script paths now execute successfully:
  - evidence-grade orchestration E2E
  - perf smoke
