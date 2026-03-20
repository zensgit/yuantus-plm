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
- `f46ff5e` `Merge branch 'feature/codex-stack-c17c18c19' into main`
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
- Final merge into `main` has been executed
- No blocking post-merge defect found on the merged target branch
- Remaining work is:
  - short stabilization monitoring on `main`
  - defer any new Claude branch creation until the stabilization window is accepted

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

## Actual Main Merge
- target branch:
  - `main`
- actual merge commit:
  - `f46ff5e`
- result:
  - `feature/codex-stack-c17c18c19` merged into `main` without manual conflict resolution
- post-merge regression on `main`:
  - expanded stack script:
    - `305 passed, 103 warnings in 17.86s`
  - broader merge-prep pack:
    - `112 passed, 283 deselected, 63 warnings in 46.91s`
  - note:
    - `pytest` emitted one cache warning due to `No space left on device` while writing `.pytest_cache`
    - test execution itself completed successfully

## Final Regression Refresh
- expanded stack script rerun:
  - `305 passed, 103 warnings in 121.86s`
- greenfield targeted pack:
  - `87 passed, 29 warnings`
- greenfield light cross-pack:
  - `87 passed, 74 warnings`
- actual merged-`main` post-merge checks:
  - expanded stack script:
    - `305 passed, 103 warnings in 17.86s`
  - broader merge-prep pack:
    - `112 passed, 283 deselected, 63 warnings in 46.91s`

## Stabilization Refresh
- cache/worktree cleanup:
  - removed `__pycache__` and `.pytest_cache` from clean Codex worktrees
  - removed superseded rehearsal and integration worktrees
  - restored free space to roughly `4.3Gi`
- post-cleanup reruns on merged `main`:
  - expanded stack script:
    - `305 passed, 103 warnings in 13.98s`
  - broader merge-prep pack:
    - `112 passed, 283 deselected, 62 warnings in 17.06s`
  - note:
    - the prior `.pytest_cache` `No space left on device` warning did not recur

## Merge Checklist
- completed:
  - confirmed target branch `main`
  - merged source branch `feature/codex-stack-c17c18c19`
  - reviewed hotspot files first:
    - `src/yuantus/api/app.py`
    - `contracts/claude_allowed_paths.json`
    - `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
    - `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
    - `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md`
    - `docs/DELIVERY_DOC_INDEX.md`
    - `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`
  - reran `scripts/verify_odoo18_plm_stack.sh full`
  - reran the broader merge-prep pytest pack
- follow-up:
  - monitor disk pressure because `.pytest_cache` write emitted `No space left on device`
  - hold new Claude branches until stabilization is accepted

## Claude Parallel Policy
- expanded candidate stack is now frozen except merge-prep and review work
- `C17-C19` are complete and already integrated into the greenfield candidate stack
- post-merge stabilization on `main` has been accepted
- new Claude work, if reopened, should use the next greenfield batch only:
  - `C20`
  - `C21`
  - `C22`
- next greenfield base:
  - `feature/claude-greenfield-base-2`

## Next Candidate Stack: C20-C21-C22
- candidate branch:
  - `feature/codex-stack-c20c21c22`
- base relation:
  - fast-forward from `main` commit `dd4b72a`
- integrated commits:
  - `e85d046` `feat(c20): add box analytics and export endpoints`
  - `b45e7a4` `feat(c21): add document sync analytics and export endpoints`
  - `68e3dbb` `feat(c22): add cutted-parts analytics and export endpoints`
  - `084141e` `docs(stack): record c20 c21 candidate verification`
  - `4bb81d3` `docs(stack): add c19 cross-regression to c20 c21 candidate`
  - `280c8b6` `docs(verification): refresh c20 c21 c22 batch status`
- candidate verification:
  - targeted `C20+C21` pack:
    - `83 passed, 33 warnings in 9.00s`
  - greenfield cross-regression with `C19`:
    - `118 passed, 43 warnings in 31.73s`
  - greenfield cross-regression with `C20+C21+C22`:
    - `133 passed, 49 warnings in 3.32s`
  - unified stack script on candidate branch:
    - `351 passed, 123 warnings in 28.77s`
- current gate:
  - `C20/C21/C22` are all now candidate-stack verified
  - next step is merge-prep / rehearsal for this full greenfield second-stage batch

## Actual Main Fast-Forward: C20-C21-C22
- target branch:
  - `main`
- source branch:
  - `feature/codex-stack-c20c21c22`
- fast-forward result:
  - `main` advanced from `dd4b72a` to `aebdc09`
- post-merge unified stack regression:
  - `351 passed, 123 warnings in 30.86s`

## Next Greenfield Planning
- stabilization for `C20/C21/C22` has been accepted on `main`
- next Claude base:
  - `feature/claude-greenfield-base-3`
- next greenfield batch:
  - `C23`
  - `C24`
  - `C25`
- this planning step does not reopen active merge-prep on `main`; it only prepares isolated task boundaries

## Resolved Candidate Stack: C23-C24-C25
- source staging branch:
  - `feature/codex-c23c24c25-staging`
- main fast-forward lineage:
  - `ee2292d` -> `88abb79`
- integrated commits:
  - `585d5f3` `feat(c23): add box ops report and transition summary endpoints`
  - `7ab31dc` `feat(c24): add document sync reconciliation and conflict resolution endpoints`
  - `b2fec86` `feat(cutted-parts): add cost and utilization analytics (C25)`
- staging verification before merge:
  - combined targeted regression:
    - `178 passed, 66 warnings in 3.62s`
  - unified stack script on staging branch:
    - `396 passed, 140 warnings in 15.87s`
- post-merge verification on `main`:
  - unified stack rerun:
    - `396 passed, 140 warnings in 11.78s`
  - broader regression rerun:
    - `249 passed, 122 warnings in 9.26s`
- resolution:
  - `C23/C24/C25` are now merged on `main`
  - no new post-merge functional regression was observed

## Next Claude Base: C26-C28
- next Claude base:
  - `feature/claude-greenfield-base-4`
- next greenfield batch:
  - `C26`
  - `C27`
  - `C28`
- this planning step does not reopen active merge-prep on `main`; it only prepares isolated fourth-stage task boundaries

## Next Candidate Stack: C26-C27-C28
- candidate branch:
  - `feature/codex-c26c27c28-staging`
- base relation:
  - fast-forward from `main` commit `d068476`
- integrated commits:
  - `37e81be` `feat(box): add reconciliation/audit analytics (C26)`
  - `f828406` `feat(document-sync): add replay/audit analytics (C27)`
  - `fabc2b5` `feat(cutted-parts): add C28 templates/scenarios bootstrap`
- candidate verification:
  - combined targeted regression:
    - `222 passed, 82 warnings in 3.75s`
  - unified stack script on staging branch:
    - `440 passed, 156 warnings in 13.91s`
- current gate:
  - `C26/C27/C28` are now staging-verified
  - next step is merge-prep / rehearsal for this full fourth-stage greenfield batch

## Merge Rehearsal: C26-C27-C28
- rehearsal branch:
  - `feature/codex-merge-rehearsal-c26c27c28`
- rehearsal action:
  - `main` branch state at `d068476`
  - fast-forwarded to candidate stack commit `019e874`
- rehearsal verification:
  - unified stack script on rehearsal branch:
    - `440 passed, 156 warnings in 13.61s`
- resolution:
  - rehearsal passed without manual conflict resolution
  - candidate stack is ready for actual main fast-forward if accepted

## Actual Main Fast-Forward: C26-C27-C28
- source staging branch:
  - `feature/codex-c26c27c28-staging`
- main fast-forward lineage:
  - `d068476` -> `129e773`
- post-merge verification on `main`:
  - unified stack rerun:
    - `440 passed, 156 warnings in 13.96s`
- resolution:
  - `C26/C27/C28` are now merged on `main`
  - no new post-merge functional regression was observed

## Main Stabilization: C26-C27-C28
- stabilization reruns on `main`:
  - targeted greenfield pack:
    - `222 passed, 82 warnings in 2.12s`
  - unified stack full:
    - `440 passed, 156 warnings in 12.63s`
- stabilization status:
  - accepted

## Next Claude Base: C29-C31
- next Claude base:
  - `feature/claude-greenfield-base-5`
- next greenfield batch:
  - `C29`
  - `C30`
  - `C31`
- this planning step does not reopen active merge-prep on `main`; it only prepares isolated fifth-stage task boundaries

## Next Candidate Stack: C29-C30-C31
- candidate branch:
  - `feature/codex-c29c30c31-staging`
- base relation:
  - fast-forward from `main` commit `c620f94`
- integrated commits:
  - `31e59bb` `feat(box): add C29 capacity/compliance bootstrap`
  - `6fcf9be` `feat(document-sync): add C30 drift/snapshots bootstrap`
  - `4f2e54b` `feat(cutted-parts): add C31 benchmark/quote bootstrap`
- candidate verification:
  - combined targeted regression:
    - `267 passed, 98 warnings in 3.61s`
  - unified stack script on staging branch:
    - `485 passed, 172 warnings in 14.77s`
- current gate:
  - `C29/C30/C31` are now staging-verified
- rehearsal branch:
  - `feature/codex-merge-rehearsal-c29c30c31`
- rehearsal action:
  - fast-forwarded `main` baseline `c620f94` to candidate commit `64bfae3`
- rehearsal verification:
  - unified stack script on rehearsal branch:
    - `485 passed, 172 warnings in 15.85s`
  - rehearsal passed without manual conflict resolution
- next step:
  - actual fast-forward into `main` completed
- main fast-forward:
  - `c620f94` -> `5feeb4a`
- post-merge verification on `main`:
  - targeted greenfield rerun:
    - `267 passed, 98 warnings in 2.74s`
  - unified stack full:
    - `485 passed, 172 warnings in 12.59s`

## Next Claude Base: C32-C34
- next Claude base:
  - `feature/claude-greenfield-base-6`
- next greenfield batch:
  - `C32`
  - `C33`
  - `C34`
- this planning step does not reopen active merge-prep on `main`; it only prepares isolated sixth-stage task boundaries

## Next Candidate Stack: C32-C33-C34
- candidate branch:
  - `feature/codex-c32c33c34-staging`
- base relation:
  - fast-forward from `main` commit `5babffa`
- integrated commits:
  - `80c2e7e` `feat(box): add C32 policy/exceptions bootstrap`
  - `c0d3e06` `feat(document-sync): add C33 baseline/lineage bootstrap`
  - `7b50ea2` `feat(cutted-parts): add C34 variance/recommendations analytics`
- candidate verification:
  - combined targeted regression:
    - `314 passed, 114 warnings in 3.32s`
  - unified stack script on staging branch:
    - `532 passed, 188 warnings in 12.93s`
- current gate:
  - `C32/C33/C34` are now staging-verified
- rehearsal branch:
  - `feature/codex-merge-rehearsal-c32c33c34`
- rehearsal action:
  - fast-forwarded `main` baseline `5babffa` to candidate commit `0f6e2ee`
- rehearsal verification:
  - unified stack script on rehearsal branch:
    - `532 passed, 188 warnings in 15.72s`
  - rehearsal passed without manual conflict resolution
- next step:
  - actual fast-forward into `main` completed
- main fast-forward:
  - `5babffa` -> `45dc112`
- post-merge verification on `main`:
  - targeted greenfield rerun:
    - `314 passed, 114 warnings in 3.61s`
  - unified stack full:
    - `532 passed, 188 warnings in 13.07s`
- stabilization status:
  - accepted

## Next Claude Base: C35-C37
- next Claude base:
  - `feature/claude-greenfield-base-7`
- next greenfield batch:
  - `C35`
  - `C36`
  - `C37`
- this planning step does not reopen active merge-prep on `main`; it only prepares isolated seventh-stage task boundaries

## Next Candidate Stack: C35-C36-C37
- candidate branch:
  - `feature/codex-c35c36c37-staging`
- base relation:
  - fast-forward from `main` commit `d9fa6e7`
- integrated commits:
  - `bff4ec6` `feat(box): add C35 reservations/traceability analytics`
  - `576b975` `feat(document-sync): add C36 checkpoints/retention analytics`
  - `f15ad29` `feat(cutted-parts): add C37 thresholds / envelopes bootstrap`
- candidate verification:
  - combined targeted regression:
    - `364 passed, 130 warnings in 8.36s`
  - unified stack script on staging branch:
    - `582 passed, 204 warnings in 13.39s`
- current gate:
  - `C35/C36/C37` are now staging-verified
- rehearsal branch:
  - `feature/codex-merge-rehearsal-c35c36c37`
- rehearsal action:
  - fast-forwarded `main` baseline `d9fa6e7` to candidate commit `97b1492`
- rehearsal verification:
  - unified stack script on rehearsal branch:
    - `582 passed, 204 warnings in 19.00s`
  - rehearsal passed without manual conflict resolution
- next step:
  - actual fast-forward into `main` if we accept this seventh-stage batch
- main fast-forward:
  - `d9fa6e7` -> `d9abd0c`
- post-merge verification on `main`:
  - targeted greenfield rerun:
    - `364 passed, 130 warnings in 3.71s`
  - unified stack full:
    - `582 passed, 204 warnings in 13.67s`
- stabilization status:
  - accepted

## Next Claude Base: C38-C40
- next Claude base:
  - `feature/claude-greenfield-base-8`
- next greenfield batch:
  - `C38`
  - `C39`
  - `C40`
- this planning step does not reopen active merge-prep on `main`; it only prepares isolated eighth-stage task boundaries

## Next Candidate Stack: C38-C39-C40
- candidate branch:
  - `feature/codex-c38c39c40-staging`
- base relation:
  - fast-forward from `main` commit `5ef27df`
- integrated commits:
  - `1cb1ec1` `feat(box): add C38 allocation / custody bootstrap`
  - `a1658c2` `feat(document-sync): add C39 freshness / watermarks bootstrap`
  - `d789b72` `feat(cutted-parts): add C40 alerts / outliers bootstrap`
- candidate verification:
  - combined targeted regression:
    - `417 passed, 146 warnings in 7.52s`
  - unified stack script on staging branch:
    - `635 passed, 220 warnings in 14.02s`
- current gate:
  - `C38/C39/C40` are now staging-verified
- rehearsal branch:
  - `feature/codex-merge-rehearsal-c38c39c40`
- rehearsal action:
  - fast-forwarded `main` baseline `5ef27df` to candidate commit `7205a1b`
- rehearsal verification:
  - unified stack script on rehearsal branch:
    - `635 passed, 220 warnings in 16.36s`
  - rehearsal passed without manual conflict resolution
- actual main fast-forward:
  - `5ef27df` -> `d70d102`
- post-merge verification:
  - combined targeted regression:
    - `417 passed, 146 warnings in 3.54s`
  - unified stack script on `main`:
    - `635 passed, 220 warnings in 14.89s`
- current gate:
  - `C38/C39/C40` are now merged on `main`
- stabilization rerun:
  - combined targeted regression:
    - `417 passed, 146 warnings in 5.57s`
  - unified stack script on `main`:
    - `635 passed, 220 warnings in 13.73s`
- stabilization status:
  - accepted

## Next Claude Base: C41-C43
- next Claude base:
  - `feature/claude-greenfield-base-9`
- next greenfield batch:
  - `C41`
  - `C42`
  - `C43`
- this planning step does not reopen active merge-prep on `main`; it only prepares isolated ninth-stage task boundaries

## Next Candidate Stack: C41-C42
- candidate branch:
  - `feature/codex-c41c42-staging`
- base relation:
  - fast-forward from `main` commit `88820f2`
- integrated commits:
  - `f8c9753` `feat(box): add C41 occupancy / turnover bootstrap`
  - `31b98ab` `feat(document-sync): add C42 lag / backlog bootstrap`
- candidate verification:
  - combined targeted regression:
    - `291 passed, 110 warnings in 3.37s`
  - unified stack script on staging branch:
    - `667 passed, 231 warnings in 13.47s`
- current gate:
  - `C41/C42` are now staging-verified
  - `C43` remains pending by design
