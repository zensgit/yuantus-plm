# Odoo18 PLM Unified Stack Merge Prep

## Branch
- `feature/codex-stack-c11c12`

## Included Contracts
- `C6`
- `P2-A`
- `C7`
- `C8`
- `C9`
- `C10`
- `C11`
- `C12`
- `C13`
- `C14`
- `C15`
- `C16`

## Latest Commits
- `4c1b49d` `docs(plan): prepare claude c17-c19 greenfield task batch`
- `a07ee36` `docs(stack): record merge prep regression and hotspot summary`
- `4152374` `feat(stack): integrate c16 into unified quality analytics stack`
- `afc9b19` `feat(c16): add quality SPC and analytics services`
- `a016201` `feat(stack): integrate c14 c15 and automate unified regression`

## Merge Hotspots
- `src/yuantus/api/app.py`
- `contracts/claude_allowed_paths.json`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DELIVERY_DOC_INDEX.md`

## Regression Baselines
- unified stack script:
  - `218 passed, 75 warnings`
- broader merge-prep pack:
  - `112 passed, 283 deselected, 62 warnings`

## Current Assessment
- No blocking integration defect found on the unified stack branch
- Remaining work is merge-prep and wider final regression, not new feature branches

## Merge Rehearsal
- rehearsal branch: `feature/codex-merge-rehearsal-stack`
- rehearsal merge commit: `b307d19`
- result:
  - unified stack merges into `main` without manual conflict resolution

## Final Regression Refresh
- unified stack script rerun:
  - `218 passed, 75 warnings in 12.43s`
- broader merge-prep pack rerun:
  - `112 passed, 283 deselected, 62 warnings in 15.07s`

## Merge Checklist
- confirm target branch is still `main`
- merge source branch `feature/codex-stack-c11c12`
- review hotspot files first:
  - `src/yuantus/api/app.py`
  - `contracts/claude_allowed_paths.json`
  - `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
  - `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
  - `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
  - `docs/DELIVERY_DOC_INDEX.md`
- rerun before final merge:
  - `PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc scripts/verify_odoo18_plm_stack.sh full`
- recommended post-merge regression:
  - rerun `scripts/verify_odoo18_plm_stack.sh full`
  - rerun the broader merge-prep pytest pack

## Claude Parallel Policy
- unified stack is now frozen except merge-prep and review work
- Claude may take only new greenfield tasks:
  - `C17` first
  - `C18` after `C17` stabilizes
  - `C19` last
