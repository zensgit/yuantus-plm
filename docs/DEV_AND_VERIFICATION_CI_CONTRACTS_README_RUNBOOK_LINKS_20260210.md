# Dev & Verification Report - CI Contracts: README Runbook Links (2026-02-10)

This delivery prevents doc regressions by validating that the `README.md` Runbooks section only references existing files, and ensures the lightweight CI `contracts` job runs when runbook/docs entrypoints change.

## Changes

### 1) CI change-scope: run `contracts` when runbook entrypoints change

- `.github/workflows/ci.yml`
  - `detect_changes (CI)` now sets `run_contracts=true` when these paths change:
    - `README.md`
    - `docs/RUNBOOK_*.md`
    - `docs/OPS_RUNBOOK_MT.md`
    - `docs/ERROR_CODES*.md`

### 2) Contract test: README Runbooks references exist

- New: `src/yuantus/meta_engine/tests/test_readme_runbook_references.py`
  - Parses the `## Runbooks` section in `README.md`
  - Extracts backticked paths and asserts they exist in the repo

### 3) Wire test into CI contracts job

- `.github/workflows/ci.yml`
  - `contracts` job runs `test_readme_runbook_references.py`.

## Verification

YAML sanity:

```bash
ruby -ryaml -e 'YAML.load_file(%q(.github/workflows/ci.yml))'
```

Targeted pytest:

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_readme_runbook_references.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

- YAML load: OK
- Pytest: PASS

