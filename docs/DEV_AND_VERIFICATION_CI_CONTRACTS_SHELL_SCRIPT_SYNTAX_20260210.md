# Dev & Verification Report - CI Contracts: Shell Script Syntax (2026-02-10)

This delivery strengthens CI “contracts” by adding a fast syntax check for key bash scripts that are used by CI workflows and ops runbooks.

## Changes

### 1) Release orchestration script: global `--help`

- `scripts/release_orchestration.sh`
  - Support `--help` without requiring `plan/execute` arguments (exit 0).

### 2) Contracts: bash `-n` syntax checks for key scripts

- New: `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
  - `bash -n` on:
    - `scripts/strict_gate_report.sh`
    - `scripts/demo_plm_closed_loop.sh`
    - `scripts/release_orchestration.sh`
    - `scripts/verify_all.sh`
    - `scripts/verify_cad_ml_quick.sh`
    - `scripts/verify_cad_preview_online.sh`
    - `scripts/verify_run_h.sh`
  - Also asserts `scripts/release_orchestration.sh --help` works (exit 0 + usage text).

- `.github/workflows/ci.yml`
  - `contracts` job runs `test_ci_shell_scripts_syntax.py`.

## Verification

YAML sanity:

```bash
ruby -ryaml -e 'YAML.load_file(%q(.github/workflows/ci.yml))'
```

Targeted pytest:

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py
```

Result:

- YAML load: OK
- Pytest: PASS

