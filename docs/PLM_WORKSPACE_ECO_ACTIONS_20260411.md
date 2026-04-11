# Native PLM Workspace ECO Actions (2026-04-11)

## Goal

Land native `approve` / `reject` actions for the focused ECO inside the Yuantus PLM workspace, without introducing a second workflow surface or a new backend route layer.

This closes the Phase 0 native workspace loop for the change tab:

1. open a Part in native workspace
2. load change governance
3. approve or reject the focused ECO in place
4. refresh governance, product context, and release readiness in the same screen

## Design

### Boundary

- Keep PLM workflow authority in Yuantus.
- Reuse existing ECO endpoints:
  - `POST /api/v1/eco/{eco_id}/approve`
  - `POST /api/v1/eco/{eco_id}/reject`
- Do not add new adapter-only routes.
- Do not fork a separate “change action” screen.

### UI behavior

Native workspace now renders action buttons in both governance entry points:

- `ECO Focus`
- `ECO Approvals`

The buttons are only enabled when:

- a focused ECO exists
- the workspace session already has a bearer token
- no other ECO action is currently pending

The reject path prompts for a mandatory reason before issuing the mutation.

### Refresh chain

After a successful approve/reject action, the workspace refreshes the minimum dependent surfaces in order:

1. product context, when the current object supports it
2. ECO governance
3. release readiness, when the current object supports it

This keeps the active object summary, governance rail, and readiness rail aligned after the mutation instead of requiring a manual reload.

### Status contract

Success status is explicit and user-facing:

- `ECO <id> approved. Current ECO state approved.`
- `ECO <id> rejected. Current ECO state progress.`

Partial refresh is still surfaced as an error state instead of being silently ignored.

## Files

Primary implementation:

- `src/yuantus/web/plm_workspace.html`

Playwright coverage:

- `playwright/tests/plm_workspace_eco_actions.spec.js`
- `scripts/verify_playwright_plm_workspace_eco_actions.sh`
- `scripts/verify_playwright_plm_workspace_all.sh`

Contract / scope wiring:

- `src/yuantus/meta_engine/tests/test_ci_contracts_native_workspace_bundle_scope.py`
- `src/yuantus/meta_engine/tests/test_ci_contracts_native_workspace_playwright_aggregate_wrapper.py`
- `src/yuantus/meta_engine/tests/test_ci_contracts_native_workspace_playwright_entrypoints.py`
- `src/yuantus/meta_engine/tests/test_ci_contracts_native_workspace_scope_script.py`
- `src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_ui_playwright_workspace_smokes.py`
- `src/yuantus/meta_engine/tests/test_delivery_scripts_index_native_workspace_playwright_contracts.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`

Operator/docs wiring:

- `package.json`
- `README.md`
- `docs/VERIFICATION.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `playwright/tests/README_plm_workspace.md`
- `scripts/list_native_workspace_bundle.sh`
- `scripts/verify_all.sh`

## Verification

### Python contract and scope tests

```bash
/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_ci_contracts_native_workspace_bundle_scope.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_native_workspace_playwright_aggregate_wrapper.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_native_workspace_playwright_entrypoints.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_native_workspace_scope_script.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_ui_playwright_workspace_smokes.py \
  src/yuantus/meta_engine/tests/test_delivery_scripts_index_native_workspace_playwright_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  -q
```

Result: `17 passed`

### Router sanity

```bash
/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/python -m pytest \
  src/yuantus/api/tests/test_plm_workspace_router.py -q
```

Result: `3 passed`

### Browser regression: ECO actions only

```bash
bash scripts/verify_playwright_plm_workspace_eco_actions.sh http://127.0.0.1:7910
```

Result: `2 passed`

Covered:

- approve focused ECO and refresh governance context
- reject focused ECO with reason and keep workspace state aligned

### Browser regression: native workspace aggregate

```bash
bash scripts/verify_playwright_plm_workspace_all.sh http://127.0.0.1:7910
```

Result:

- documents UI: `2 passed`
- demo resume: `5 passed`
- document handoff: `6 passed`
- ECO actions: `2 passed`

Total: `15 passed`

## Notes

- The first ECO-actions run hit a stale `:7910` server and failed on old status text. After clearing the reused listener and rerunning against the current worktree, the browser suite passed cleanly.
- Playwright used the repository’s existing temp-db pattern (`TENANCY_MODE=single` + seeded `admin/admin`) through `playwright.config.js`.
- This change intentionally stays inside the native workspace layer. It does not change Metasheet federation behavior or introduce new contract scope beyond the local Playwright/scope harness.
