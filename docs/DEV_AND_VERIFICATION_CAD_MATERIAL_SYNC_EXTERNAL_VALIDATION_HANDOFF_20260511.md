# Dev & Verification - CAD Material Sync External Validation Handoff

Date: 2026-05-11

Path:
`docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_EXTERNAL_VALIDATION_HANDOFF_20260511.md`

## 1. Summary

PR #495 merged the CAD Material Sync delivery package on `main=8593911`.

The repository-side package is delivered and post-merge smoke is green. The
remaining validation is external: Windows + AutoCAD 2018 DLL loading and real
DWG write-back smoke. That external validation is not replaced by macOS/Linux
fixture, SQLite, Playwright, or packaging checks.

## 2. Current State

- Delivery package merged: #495.
- Current main anchor: `8593911`.
- macOS/Linux package verification: green.
- Windows + AutoCAD 2018 real smoke: pending.
- Windows + AutoCAD 2024 regression smoke: pending.

## 3. Required External Evidence

The external validation record must include:

- AutoCAD `ACADVER` output showing `R22.0`.
- Preflight output from `verify_autocad2018_preflight.ps1`.
- Build output and compiled DLL path.
- Command log or screenshots for `DEDUPHELP`, `PLMMATPROFILES`,
  `PLMMATCOMPOSE`, `PLMMATPUSH`, and `PLMMATPULL`.
- Screenshot of the `PLMMATPULL` diff preview before confirmation.
- Before/after screenshot of a real DWG material field.
- Evidence that the saved DWG reopens with the updated field still present.
- Yuantus API or application log excerpt for dry-run and real write.

## 4. Decision Boundary

Until external evidence exists, do not claim:

- AutoCAD 2018 support complete.
- Real DWG write-back validated.
- Windows client runtime accepted.

The merged PR can be used as a delivery package and Windows validation input.
It is not itself the Windows validation result.

## 5. Non-Goals

- No runtime code changes.
- No AutoCAD binary artifact added.
- No fake or synthetic Windows evidence.
- No production DWG modification.
- No Phase 5 implementation.
- No P3.4 evidence creation or acceptance.
- No production cutover.

## 6. Verification Commands

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_material_sync_external_validation_contracts.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_material_sync_external_validation_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m py_compile \
  src/yuantus/meta_engine/tests/test_cad_material_sync_external_validation_contracts.py

git diff --check
```

## 7. Verification Results

- External validation handoff contract: 4 passed.
- Focused contract/doc-index/CI-list suite: 9 passed.
- `py_compile` on the new contract: passed.
- `git diff --check`: clean.

## 8. Reviewer Checklist

- Confirm this document records external validation as pending.
- Confirm it does not weaken the Windows + AutoCAD 2018 requirement.
- Confirm it does not claim real DWG write-back is already validated.
- Confirm it does not touch runtime, AutoCAD source, Phase 5, P3.4 evidence, or
  production cutover.
