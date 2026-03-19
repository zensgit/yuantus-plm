# Odoo18 PLM Unified Stack Merge Prep

## Branch
- `feature/codex-stack-c17c18c19`

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
- `C17`
- `C18`
- `C19`

## Latest Commits
- `c9b4729` `docs(stack): finalize c17 c18 c19 merge prep baseline`
- `1d49413` `docs(stack): record c17 c18 c19 combined integration regression`
- `2f98e1b` `docs(c19): record codex integration verification`
- `ea7af53` `feat(c19): bootstrap cutted-parts domain with materials, plans, and cuts`
- `457170c` `docs(stack): record c17 c18 combined integration regression`

## Merge Hotspots
- `src/yuantus/api/app.py`
- `contracts/claude_allowed_paths.json`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`

## Regression Baselines
- expanded unified stack script:
  - `305 passed, 103 warnings in 121.86s`
- greenfield candidate targeted pack:
  - `87 passed, 29 warnings`
- greenfield candidate light cross-pack:
  - `87 passed, 74 warnings`

## Current Assessment
- No blocking integration defect found on the expanded candidate stack
- Remaining work is:
  - execute the final merge when release timing is approved
  - perform post-merge regression on the target branch

## Merge Rehearsal
- prior rehearsal branch:
  - `feature/codex-merge-rehearsal-stack`
- prior rehearsal merge commit:
  - `b307d19`
- prior result:
  - pre-greenfield unified stack merged into `main` without manual conflict resolution
- current expanded candidate stack rehearsal:
  - branch:
    - `feature/codex-merge-rehearsal-c17c18c19`
  - merge commit:
    - `7db4fc6`
  - result:
    - expanded candidate stack merges into `main` without manual conflict resolution
    - expanded stack script also passes on the rehearsal branch:
      - `305 passed, 103 warnings in 20.43s`

## Final Regression Refresh
- expanded stack script rerun:
  - `305 passed, 103 warnings in 121.86s`
- greenfield targeted pack:
  - `87 passed, 29 warnings`
- greenfield light cross-pack:
  - `87 passed, 74 warnings`

## Merge Checklist
- confirm target branch is still `main`
- merge source branch `feature/codex-stack-c17c18c19`
- review hotspot files first:
  - `src/yuantus/api/app.py`
  - `contracts/claude_allowed_paths.json`
  - `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
  - `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
  - `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
  - `docs/DELIVERY_DOC_INDEX.md`
  - `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`
- rerun before final merge:
  - `PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc scripts/verify_odoo18_plm_stack.sh full`
- recommended post-merge regression:
  - rerun `scripts/verify_odoo18_plm_stack.sh full`
  - rerun the broader merge-prep pytest pack

## Claude Parallel Policy
- expanded candidate stack is now frozen except merge-prep and review work
- `C17-C19` are complete and already integrated into the greenfield candidate stack
- do not open new Claude feature branches until:
  - expanded stack merge rehearsal is complete
  - final regression is stable
  - the final merge is either executed or explicitly deferred
