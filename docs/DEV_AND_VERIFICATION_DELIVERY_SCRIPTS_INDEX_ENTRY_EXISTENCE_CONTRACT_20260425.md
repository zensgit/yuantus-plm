# Delivery Scripts Index Entry Existence Contract

Date: 2026-04-25

## 1. Purpose

`docs/DELIVERY_SCRIPTS_INDEX_20260202.md` is the operator-facing discovery
surface for delivery and verification scripts. Several individual contracts
pin specific script entries, but there was no generic guard ensuring every
listed entry still exists under `scripts/`.

This change adds a general scripts-index integrity contract.

## 2. Scope

Changed:

- `src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py`
- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DEV_AND_VERIFICATION_DELIVERY_SCRIPTS_INDEX_ENTRY_EXISTENCE_CONTRACT_20260425.md`

## 3. Design

The contract reads the bullet list before `## Notes` in
`DELIVERY_SCRIPTS_INDEX_20260202.md` and asserts:

- the index has at least one script entry
- entries are unique
- each repo-local entry resolves to an existing file under `scripts/`
- legacy package-only entries are explicitly documented in
  `docs/DELIVERY_TREE_20260202.md`
- each indexed repo-local `.sh` entry passes `bash -n`

The check intentionally does not require all files in `scripts/` to be indexed.
The delivery scripts index is curated, not a complete filesystem inventory.

Package-only entries are currently:

- `backup.sh`
- `restore.sh`
- `verify_extract_start.sh`
- `verify_package.sh`

## 4. CI Wiring

The new contract is included in the CI contracts job. It sits next to the
existing delivery scripts index contract for native workspace Playwright
wrappers.

## 5. Non-Goals

- No changes to script behavior.
- No changes to script index ordering.
- No requirement that every `scripts/*` file be indexed.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
git diff --check
```

Results:

- Delivery scripts index entries contract: `2 passed in 0.23s`
- CI wiring + CI ordering + entries contract: `4 passed in 0.23s`
- Doc index contracts: `3 passed in 0.03s`
- Odoo18 PLM stack smoke: `265 passed in 18.92s`
- `git diff --check`: passed

## 7. Review Notes

Review should confirm the parser stays deliberately narrow: only the top bullet
list before `## Notes` is treated as script entries. Note bullets are prose and
must not be interpreted as script inventory.
