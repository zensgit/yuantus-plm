# PR #155 Final Review Checklist

Date: `2026-04-09`
PR: `zensgit/yuantus-plm#155`
Branch: `feature/claude-c43-cutted-parts-throughput`

This is the shortest final review checklist for the native PLM workspace line.

## Must-Review Files

1. `src/yuantus/api/app.py`
2. `src/yuantus/api/middleware/auth_enforce.py`
3. `src/yuantus/api/routers/plm_workspace.py`
4. `src/yuantus/api/routers/workbench.py`
5. `src/yuantus/web/plm_workspace.html`
6. `playwright/tests/plm_workspace_documents_ui.spec.js`
7. `playwright/tests/plm_workspace_demo_resume.spec.js`
8. `playwright/tests/plm_workspace_document_handoff.spec.js`
9. `scripts/verify_all.sh`

If branch-hygiene context is needed after that:

10. `docs/PLM_WORKSPACE_REVIEWER_BRIEF_20260409.md`
11. `docs/DIRTY_TREE_SPLIT_MATRIX_20260409.md`
12. `scripts/print_dirty_tree_split_matrix.sh`

## Must-Run Commands

```bash
pytest src/yuantus/api/tests/test_plm_workspace_router.py src/yuantus/api/tests/test_workbench_router.py -q
bash scripts/verify_playwright_plm_workspace_documents_ui.sh http://127.0.0.1:7910
bash scripts/verify_playwright_plm_workspace_demo_resume.sh http://127.0.0.1:7910
bash scripts/verify_playwright_plm_workspace_document_handoff.sh http://127.0.0.1:7910
pytest src/yuantus/meta_engine/tests/test_ci_contracts_native_workspace_*.py -q
pytest src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py -q
bash scripts/list_native_workspace_bundle.sh --full --status
```

Expected clean-scope result:

- `bash scripts/list_native_workspace_bundle.sh --full --status`
- output should be empty for the workspace bundle scope

## Out-of-Scope

- Wave 2 pact work
- metasheet adapter changes
- generic relationship-graph abstraction
- unrelated dirty-tree domains:
  - `subcontracting`
  - `docs-parallel`
  - `cross-domain-services`
  - `migrations`
  - `strict-gate`
  - `delivery-pack`

## Sign-Off Criteria

- API routes and auth bypass wiring are coherent
- `plm_workspace.html` behavior matches the landed browser regressions
- all three workspace Playwright wrappers pass locally
- workspace bundle scope remains isolated
- reviewer is comfortable ignoring the split-matrix follow-up domains for this PR

## Follow-up Split Routing

- use `docs/SPLIT_PR_REVIEW_ORDER_20260409.md` for the shortest review order across
  `#155`, `#156`, `#157`, and `#158`
- use `docs/PR_TRIAGE_SUMMARY_20260409.md` for the one-page PR-level triage view
- use `docs/PR_REVIEWER_ASSIGNMENT_PLAN_20260409.md` for concern-based reviewer routing
- use `docs/PR_MERGE_READINESS_NOTE_20260409.md` for merge order and non-blocking rules
- use `docs/PR_CLOSE_DECISION_NOTE_20260409.md` for the final merge-vs-hold decision
