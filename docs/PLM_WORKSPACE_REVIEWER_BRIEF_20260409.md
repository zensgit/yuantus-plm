# PLM Workspace Reviewer Brief

Date: `2026-04-09`
Branch: `feature/claude-c43-cutted-parts-throughput`

## Scope

This bundle lands the native Yuantus PLM workspace browser harness and its
runtime wiring. It is intentionally separate from the earlier Pact/provider
work so reviewers can focus on the native workspace surface and its verification
entrypoints.

## Included commits

- `402f4c6` `feat(plm-workspace): land native workspace browser harness bundle`
- `0b8fda9` `fix(plm-workspace): complete runtime wiring and scope helper`
- `83efdaa` `chore(dev): ignore local playwright workspace artifacts`

Follow-up reviewer / split-safety tooling:

- `958aba9` `chore(dev): add Claude Code parallel helper`
- `04bbb54` `chore(dev): add Claude reviewer sidecar runner`
- `d7af6dc` `docs(dev): add dirty tree domain inventory`
- `b7a1843` `chore(dev): add dirty tree domain split helper`
- `a846ae9` `docs(dev): add dirty tree split order`
- `e63b101` `chore(dev): add subcontracting first cut anchors`
- `0df3185` `chore(dev): add subcontracting first cut hunk guide`
- `be3489d` `chore(dev): add subcontracting operator checklist`
- `1d0e852` `chore(dev): add subcontracting patch decision cheat sheet`
- `8e7c787` `chore(dev): add subcontracting branch execution note`
- `99a9d7d` `docs(dev): add post-subcontracting next step note`
- `2a9d7d6` `docs(dev): add docs-parallel split helper`
- `346b4c0` `docs(dev): add cross-domain services split helper`
- `0c8aa90` `docs(dev): add strict-gate split helper`
- `8713fd6` `docs(dev): add delivery-pack split helper`
- `681a042` `docs(dev): add dirty tree split matrix`

## What changed

### Runtime/UI

- Adds the native workspace shell at
  `src/yuantus/web/plm_workspace.html`
- Adds the workbench shell at
  `src/yuantus/web/workbench.html`
- Wires `/api/v1/plm-workspace`, `/api/v1/workbench`, and `/favicon.ico`
  through:
  - `src/yuantus/api/routers/plm_workspace.py`
  - `src/yuantus/api/routers/workbench.py`
  - `src/yuantus/api/routers/favicon.py`
  - `src/yuantus/api/app.py`
  - `src/yuantus/api/middleware/auth_enforce.py`

### Browser verification

- Adds checked-in Playwright regressions:
  - `playwright/tests/plm_workspace_documents_ui.spec.js`
  - `playwright/tests/plm_workspace_demo_resume.spec.js`
  - `playwright/tests/plm_workspace_document_handoff.spec.js`
  - helper: `playwright/tests/helpers/plmWorkspaceDemo.js`
- Adds operator-facing wrappers:
  - `scripts/verify_playwright_plm_workspace_documents_ui.sh`
  - `scripts/verify_playwright_plm_workspace_demo_resume.sh`
  - `scripts/verify_playwright_plm_workspace_document_handoff.sh`
  - aggregate: `scripts/verify_playwright_plm_workspace_all.sh`
- Wires workspace Playwright into `scripts/verify_all.sh` under
  `RUN_UI_PLAYWRIGHT=1`

### Contracts / discoverability

- Adds/extends CI contract tests for:
  - aggregate wrapper wiring
  - package/readme/verification/doc index entrypoints
  - bundle-scope completeness
  - local temp artifact ignore rules
- Documents the workspace verification surface in:
  - `README.md`
  - `docs/VERIFICATION.md`
  - `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
  - `playwright/tests/README_plm_workspace.md`

### Scope helper

- Adds `scripts/list_native_workspace_bundle.sh`
- Useful commands:
  - `bash scripts/list_native_workspace_bundle.sh --full --status`
  - `bash scripts/list_native_workspace_bundle.sh --full --git-add-cmd`
  - `bash scripts/list_native_workspace_bundle.sh --full --commit-plan`

## Reviewer path

Start here if you want the shortest path:

1. `src/yuantus/api/app.py`
2. `src/yuantus/api/middleware/auth_enforce.py`
3. `src/yuantus/api/routers/plm_workspace.py`
4. `src/yuantus/api/routers/workbench.py`
5. `src/yuantus/web/plm_workspace.html`
6. `playwright/tests/plm_workspace_documents_ui.spec.js`
7. `playwright/tests/plm_workspace_demo_resume.spec.js`
8. `playwright/tests/plm_workspace_document_handoff.spec.js`
9. `scripts/verify_all.sh`

If you only need the branch-hygiene context after that:

10. `docs/DIRTY_TREE_SPLIT_MATRIX_20260409.md`
11. `scripts/print_dirty_tree_split_matrix.sh`

Final checklist:

- `docs/PR_155_FINAL_REVIEW_CHECKLIST_20260409.md`

Branch closeout summary:

- `docs/BRANCH_CLOSEOUT_SUMMARY_20260409.md`
- `docs/DIRTY_TREE_RESIDUAL_CLOSEOUT_20260409.md`

## Verification run

Executed during landing:

- `pytest src/yuantus/api/tests/test_plm_workspace_router.py src/yuantus/api/tests/test_workbench_router.py -q`
- `bash scripts/verify_playwright_plm_workspace_documents_ui.sh http://127.0.0.1:7910`
- `bash scripts/verify_playwright_plm_workspace_demo_resume.sh http://127.0.0.1:7910`
- `bash scripts/verify_playwright_plm_workspace_document_handoff.sh http://127.0.0.1:7910`
- `pytest src/yuantus/meta_engine/tests/test_ci_contracts_native_workspace_*.py -q`
- `pytest src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py -q`
- `bash -n scripts/verify_all.sh`

Latest clean-scope check:

- `bash scripts/list_native_workspace_bundle.sh --full --status`
- Result: empty output for the workspace bundle scope

Latest dirty-tree split tooling checks:

- `bash scripts/print_dirty_tree_split_matrix.sh --commands`
- `pytest src/yuantus/meta_engine/tests/test_ci_contracts_dirty_tree_split_matrix.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py -q`
- Result: split matrix and helper entrypoints are green

## Dirty-Tree Safety Note

The branch still has unrelated dirty-tree domains outside the landed native
workspace bundle. To keep reviewer scope narrow, the cleanup path is now
explicitly tool-driven instead of ad hoc:

- `subcontracting`
- `docs-parallel`
- `cross-domain-services`
- `migrations`
- `strict-gate`
- `delivery-pack`

Single-entry overview:

- `docs/DIRTY_TREE_SPLIT_MATRIX_20260409.md`
- `scripts/print_dirty_tree_split_matrix.sh`

Rule:

- do **not** `git add .`
- use the domain-specific split helpers / execution cards instead
- reviewer focus for PR #155 should remain on the already-pushed PLM workspace
  bundle, not on unrelated dirty-tree domains

## Non-goals

- No Wave 2 pact work
- No metasheet adapter changes in this bundle
- No generic relationship-graph abstraction
- No CI hard-gating of external-server Playwright beyond current local/operator entrypoints
