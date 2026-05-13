# Access Guard Taxonomy Closeout - Development and Verification

Date: 2026-05-12

## 1. Goal

Close the guard-consolidation thread after the config superuser follow-up by
pinning the complete access-guard failure-detail taxonomy in one contract.

This is a test and documentation closeout. It does not change runtime behavior.

## 2. Scope

Added:

- `src/yuantus/meta_engine/tests/test_access_guard_taxonomy_closeout_contracts.py`

Modified:

- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Guard Taxonomy

The contract pins these shared dependency owners:

| Helper | Detail | Owner |
| --- | --- | --- |
| `require_admin_user` | `Admin role required` | `src/yuantus/api/dependencies/auth.py` |
| `require_admin_permission` | `Admin permission required` | `src/yuantus/api/dependencies/auth.py` |
| `require_admin_access` | `Admin required` | `src/yuantus/api/dependencies/auth.py` |
| `require_superuser` | `Superuser required` | `src/yuantus/api/dependencies/admin_auth.py` |

The meta-engine router layer must consume these helpers instead of defining
local admin or superuser guard helpers and local guard failure literals.

## 4. Contract Coverage

The new contract verifies:

- no `src/yuantus/meta_engine/web/*.py` file defines `_ensure_admin`
- no `src/yuantus/meta_engine/web/*.py` file defines `_ensure_superuser`
- no meta-engine web router owns any of the four shared access-guard failure
  literals
- each failure detail remains owned by its shared dependency helper
- the three admin-role helpers still use `user_has_admin_role(user)`
- the closeout contract is registered in CI
- this MD is registered in `docs/DELIVERY_DOC_INDEX.md`

## 5. Non-Goals

- No conversion of route dependency shape.
- No change to `require_admin_user`, `require_admin_permission`,
  `require_admin_access`, or `require_superuser`.
- No change to platform-admin or org-admin guards.
- No CAD, Phase 3 cutover, scheduler, or service extraction work.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/tests/test_access_guard_taxonomy_closeout_contracts.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_access_guard_taxonomy_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_admin_guard_consolidation_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_config_superuser_guard_contracts.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py

.venv/bin/python -c "from yuantus.api.app import create_app; app = create_app(); print(f'routes={len(app.routes)} middleware={len(app.user_middleware)}')"

git diff --check
```

Results:

- `py_compile`: passed
- access taxonomy + admin closeout + config superuser contracts: 15 passed
- doc-index / CI list quartet: 5 passed
- boot check: `routes=676 middleware=4`
- `git diff --check`: clean

## 7. Review Checklist

- Confirm this is test/docs only.
- Confirm the taxonomy includes both `auth.py` and `admin_auth.py`.
- Confirm `Superuser required` is not folded into the admin-role helpers.
- Confirm CI list ordering and doc-index ordering stay green.
