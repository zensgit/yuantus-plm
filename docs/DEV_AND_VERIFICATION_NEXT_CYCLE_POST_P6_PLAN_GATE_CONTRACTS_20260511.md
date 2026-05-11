# Dev & Verification — Next-Cycle Post-P6 Plan-Gate Contracts

Date: 2026-05-11

## 1. Summary

Added CI-backed contracts for the post-P6 planning gate.

This is a guardrail PR. It does not start Phase 5, does not synthesize P3.4
operator evidence, and does not touch CAD plugin work. Its purpose is to keep
future continuation runs from accidentally treating "continue" as authorization
to start a blocked local implementation.

## 2. Files Changed

- `src/yuantus/meta_engine/tests/test_next_cycle_post_p6_plan_gate_contracts.py`
- `.github/workflows/ci.yml`
- `docs/DEV_AND_VERIFICATION_NEXT_CYCLE_POST_P6_PLAN_GATE_CONTRACTS_20260511.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The new contract pins five invariants:

1. Phase 4 and Phase 6 are marked complete after #499 and #503.
2. Phase 5 is explicitly blocked by accepted P3.4 external evidence.
3. Stale "Phase 4 P4.1 is next" and "Phase 6 is trigger-gated" language does
   not reappear.
4. `RUNBOOK_TENANT_MIGRATIONS_20260427.md` still exposes the six-part P3.4
   cutover stop gate.
5. This gate MD is indexed and the contract itself is wired into the CI
   `contracts` job.

## 4. Why This Exists

After #504, the six-phase plan is effectively stopped on an external evidence
gate:

- Phase 4 is complete.
- Phase 6 is complete.
- Phase 5 is not locally safe to start because it depends on accepted P3.4
  operator-run non-production PostgreSQL rehearsal evidence.

A docs-only status refresh is useful, but it can drift. This contract turns the
operating rule into a test failure if future edits weaken the gate.

## 5. Non-Goals

- No runtime code changes.
- No Phase 5 implementation.
- No P3.4 evidence synthesis.
- No database connection.
- No production cutover.
- No CAD plugin changes.
- No scheduler production rehearsal.

## 6. Verification Commands

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_next_cycle_post_p6_plan_gate_contracts.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_next_cycle_post_p6_plan_gate_contracts.py \
  src/yuantus/meta_engine/tests/test_phase6_circuit_breaker_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_phase4_search_closeout_contracts.py \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```

## 7. Verification Results

- New post-P6 plan-gate contract: 5 passed.
- Doc-index trio: 4 passed.
- Focused suite (post-P6 plan gate + Phase 6 closeout + Phase 4 closeout +
  P3 stop-gate + doc-index trio): 31 passed.
- `py_compile` on the new contract: passed.
- `git diff --check`: clean.

## 8. Reviewer Checklist

- Confirm the PR adds only planning-gate contracts/docs/CI wiring.
- Confirm Phase 5 remains blocked by P3.4 external evidence.
- Confirm no runtime code, migrations, scripts, or CAD plugin files changed.
- Confirm the delivery-doc index entry is alphabetically sorted.

This file is indexed as
`docs/DEV_AND_VERIFICATION_NEXT_CYCLE_POST_P6_PLAN_GATE_CONTRACTS_20260511.md`.
