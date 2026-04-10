# Native PLM Workspace Playwright

This folder contains the checked-in browser regressions for the native
`/api/v1/plm-workspace` demo flows.

## Coverage

- `plm_workspace_documents_ui.spec.js`
  - locks `Document Boundary`
  - locks `Source Snapshot`
  - locks partial document degradation visibility
- `plm_workspace_demo_resume.spec.js`
  - locks `demo preset -> UI login -> automatic resume`
  - verifies change + documents hydration after login
- `plm_workspace_document_handoff.spec.js`
  - locks `Part -> AML related Document -> Return to Source Product`
  - locks `Part -> AML related Document -> Return to Source Detail`
  - locks `Part -> AML related Document -> Return to Source Documents`
  - locks `Part -> AML related Document -> Return to Source Change`
  - verifies document-tab stability plus source recovery and roundtrip document integrity

## Run Directly

From repo root:

```bash
npm run playwright:test:plm-workspace
```

Or run individual specs:

```bash
npm run playwright:test:plm-workspace:documents
npm run playwright:test:plm-workspace:resume
npm run playwright:test:plm-workspace:handoff
```

Or run the operator-facing aggregate wrapper:

```bash
bash scripts/verify_playwright_plm_workspace_all.sh http://127.0.0.1:7910
```

To print the exact bundle scope that should be reviewed/staged together:

```bash
bash scripts/list_native_workspace_bundle.sh
bash scripts/list_native_workspace_bundle.sh --full
bash scripts/list_native_workspace_bundle.sh --status
bash scripts/list_native_workspace_bundle.sh --full --git-add-cmd
bash scripts/list_native_workspace_bundle.sh --full --commit-plan
```

## Verify Wrappers

The shell wrappers under `scripts/` remain the operator-facing entrypoints:

- `scripts/verify_playwright_plm_workspace_documents_ui.sh`
- `scripts/verify_playwright_plm_workspace_demo_resume.sh`
- `scripts/verify_playwright_plm_workspace_document_handoff.sh`
- `scripts/verify_playwright_plm_workspace_all.sh`

Those wrappers are also wired into `scripts/verify_all.sh` under
`RUN_UI_PLAYWRIGHT=1`.

## Notes

- The specs use `channel: 'chrome'` because the local machine already has Chrome
  installed and this avoids Playwright browser bundle mismatches.
- The demo resume and handoff specs create their own fixture data through
  `playwright/tests/helpers/plmWorkspaceDemo.js`.
