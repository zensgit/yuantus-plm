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

## Non-goals

- No Wave 2 pact work
- No metasheet adapter changes in this bundle
- No generic relationship-graph abstraction
- No CI hard-gating of external-server Playwright beyond current local/operator entrypoints
