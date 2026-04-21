# DEV_AND_VERIFICATION_SHARED_DEV_142_READONLY_REFREEZE_PROPOSAL_20260421

## Context

- Date: 2026-04-21
- Base branch: `main` at `5160c52e203a66d18ba30958c5b7bea20987e2a8`
- Goal: turn the accepted shared-dev 142 stable readonly candidate into a formal baseline-switch proposal pack without mutating the tracked baseline automatically

## Change

Added a formal refreeze proposal flow that:

1. delegates source capture to `run_p2_shared_dev_142_refreeze_candidate.sh`
2. requires a green stable candidate
3. materializes a proposal bundle under `proposal/<proposed-label>/`
4. writes:
   - `REFREEZE_PROPOSAL.md`
   - `refreeze_proposal.json`
5. keeps the current official tracked baseline untouched

New scripts:

- `scripts/run_p2_shared_dev_142_refreeze_proposal.sh`
- `scripts/render_p2_shared_dev_142_refreeze_proposal.py`
- `scripts/print_p2_shared_dev_142_refreeze_proposal_commands.sh`

New doc:

- `docs/P2_SHARED_DEV_142_READONLY_REFREEZE_PROPOSAL_CHECKLIST.md`

Selector / discoverability updates:

- `scripts/run_p2_shared_dev_142_entrypoint.sh`
  - `refreeze-proposal`
  - `print-refreeze-proposal-commands`
- `README.md`
- `docs/P2_ONE_PAGE_DEV_GUIDE.md`
- `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`
- `docs/P2_SHARED_DEV_142_READONLY_REFREEZE_CANDIDATE_CHECKLIST.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DELIVERY_DOC_INDEX.md`

## Local Verification

```bash
bash -n scripts/run_p2_shared_dev_142_refreeze_proposal.sh
bash -n scripts/print_p2_shared_dev_142_refreeze_proposal_commands.sh
python3 -m py_compile scripts/render_p2_shared_dev_142_refreeze_proposal.py

python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_wrapper.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_readme_runbook_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py
```

## Real Shared-dev 142 Verification

Executed from the clean worktree:

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode refreeze-proposal
```

Real runtime summary to be filled after execution:

- `SUMMARY_HTTP_STATUS=200`
- `CANDIDATE_EXIT_STATUS=0`
- `PROPOSAL_READY=1`
- `PROPOSAL_DECISION_KIND=proposal-ready`
- `PROPOSED_LABEL=shared-dev-142-readonly-20260421`

Real result directory:

- `tmp/p2-shared-dev-142-refreeze-proposal-20260421-080742/`

Key artifacts:

- `tmp/p2-shared-dev-142-refreeze-proposal-20260421-080742/candidate-preview/current/OBSERVATION_RESULT.md`
- `tmp/p2-shared-dev-142-refreeze-proposal-20260421-080742/candidate-preview/STABLE_READONLY_CANDIDATE.md`
- `tmp/p2-shared-dev-142-refreeze-proposal-20260421-080742/REFREEZE_PROPOSAL.md`
- `tmp/p2-shared-dev-142-refreeze-proposal-20260421-080742/refreeze_proposal.json`
- `tmp/p2-shared-dev-142-refreeze-proposal-20260421-080742/proposal/shared-dev-142-readonly-20260421/OBSERVATION_RESULT.md`
- `tmp/p2-shared-dev-142-refreeze-proposal-20260421-080742/proposal/shared-dev-142-readonly-20260421/OBSERVATION_EVAL.md`
- `tmp/p2-shared-dev-142-refreeze-proposal-20260421-080742.tar.gz`

Observed proposal decision:

- excluded pending approval:
  - `af1a2dc4-7d73-4d1d-aabb-acdde37abea8`
  - `eco-specialist`
  - `approval_deadline=2026-04-21T09:34:33.658929`
- current official counts:
  - `items=5 / pending=1 / overdue=4 / escalated=1 / anomalies=3`
- proposed candidate counts:
  - `items=4 / pending=0 / overdue=4 / escalated=1 / anomalies=3`

## Conclusion

This follow-up still does not auto-switch the official readonly baseline.

It produces the formal proposal pack that a later baseline-switch PR can review:

- candidate preview evidence
- proposed tracked baseline artifact directory
- explicit update targets
