# Dev & Verification - CAD Material Sync PR #495 CI Remediation

Date: 2026-05-11

Path:
`docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_PR495_CI_REMEDIATION_20260511.md`

## 1. Summary

This remediation refreshes PR #495 after the main branch advanced through the
post-Phase-6 and external-gate closeout PRs.

The change keeps PR #495 scoped to the CAD material sync delivery package. It
does not start Phase 5, does not touch P3.4 evidence, and does not change any
runtime tenancy or cutover behavior.

## 2. Issues Addressed

1. `contracts` failed because
   `docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_PLUGIN_20260506.md` was added
   without its `docs/DELIVERY_DOC_INDEX.md` entry on the pushed PR branch.
2. `playwright-esign` failed because
   `playwright/tests/cad_material_workbench_ui.spec.js` attempted to launch a
   browser even when CI exported `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`.
3. The PR branch was behind current `origin/main`; rebasing reduces merge risk
   and verifies the package against the current post-#510 baseline.

## 3. Delivered

- Rebased `feat/cad-material-sync-plugin-20260506` onto `origin/main=01ee08a`.
- Kept the existing doc-index repair commit for the three CAD material sync
  control docs.
- Added the same `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` skip guard used by the
  existing CAD preview Playwright smoke.
- Added this remediation record and its doc-index entry.

## 4. Scope Controls

- No Phase 5 implementation.
- No P3.4 evidence creation or acceptance.
- No production cutover.
- No database credential, token, or secret added.
- No AutoCAD binary artifact added.
- No change to `.claude/` or `local-dev-env/`.

## 5. Verification Commands

```bash
python3 scripts/verify_cad_material_delivery_package.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py \
  src/yuantus/api/tests/test_workbench_router.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

python3 scripts/verify_cad_material_diff_confirm_contract.py

PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npx playwright test \
  playwright/tests/cad_material_workbench_ui.spec.js --reporter=line

git diff --check
```

## 6. Verification Results

- CAD material delivery package verifier: passed.
- Focused CAD material + Workbench pytest suite: 46 passed.
- Doc-index trio: 4 passed.
- CAD material diff confirm contract: passed.
- Playwright skip-guard smoke with `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`: 1
  skipped, exit 0.
- `git diff --check`: clean.

## 7. Windows Boundary

macOS/Linux verification still does not replace Windows + AutoCAD 2018 loading
of the compiled DLL. PR #495 remains a delivery package with a documented
Windows validation path, not proof of real AutoCAD runtime execution.

## 8. Reviewer Checklist

- Confirm the doc-index entries close the contract failure.
- Confirm the Playwright skip guard only applies when CI explicitly sets
  `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`.
- Confirm the branch is based on current `origin/main`.
- Confirm no Phase 5, P3.4 evidence, production cutover, or secret material was
  introduced.
