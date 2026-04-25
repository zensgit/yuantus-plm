# Odoo18 PLM Stack Script Discoverability

Date: 2026-04-24

## 1. Purpose

`scripts/verify_odoo18_plm_stack.sh` is now the focused Odoo18 PLM stack
verification entrypoint for router-decomposition closeout. It was referenced by
multiple delivery documents, but it was not listed in
`docs/DELIVERY_SCRIPTS_INDEX_20260202.md`.

This change registers the script in the delivery scripts index and adds a CI
contract so the entry does not disappear.

## 2. Scope

Changed:

- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `.github/workflows/ci.yml`
- `src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_discoverability.py`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DEV_AND_VERIFICATION_ODOO18_PLM_STACK_SCRIPT_DISCOVERABILITY_20260424.md`

## 3. Design

The script index now lists `verify_odoo18_plm_stack.sh` next to
`verify_all.sh` and describes the two modes:

- `smoke`
- `full`

The description also records the dynamic router compile behavior so operators
can understand why the script is useful for router decomposition work.

## 4. Contract

The new contract test asserts that the scripts index includes:

- the script name
- Odoo18 PLM focused smoke wording
- `smoke` / `full` mode wording
- the dynamic `web/*_router.py` compile coverage note

The contract is wired into the CI contracts job.

## 5. Non-Goals

- No runtime script behavior changes.
- No smoke suite expansion.
- No router behavior changes.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_discoverability.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_discoverability.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
bash scripts/verify_odoo18_plm_stack.sh smoke
git diff --check
```

Results:

- Odoo18 PLM stack discoverability contract: `1 passed in 0.01s`
- CI wiring + CI ordering + discoverability contract: `3 passed in 0.02s`
- Doc index contracts: `3 passed in 0.03s`
- Odoo18 PLM stack smoke: `265 passed in 18.81s`
- `git diff --check`: passed

## 7. Review Notes

Review should confirm this remains a discoverability change only. The verifier
behavior itself is covered by the dynamic router compile and shell syntax
contracts.
