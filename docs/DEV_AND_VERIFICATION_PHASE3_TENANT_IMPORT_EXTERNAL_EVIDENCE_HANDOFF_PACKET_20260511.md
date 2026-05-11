# Dev & Verification - Phase 3 Tenant Import External Evidence Handoff Packet

Date: 2026-05-11

## 1. Summary

Added a post-P6 operator handoff packet for the remaining P3.4 external
evidence gate.

This is a documentation and contract slice. It does not start Phase 5, does not
connect to a database, does not synthesize P3.4 evidence, and does not authorize
runtime cutover.

## 2. Files Changed

- `docs/PHASE3_TENANT_IMPORT_EXTERNAL_EVIDENCE_HANDOFF_PACKET_20260511.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_EXTERNAL_EVIDENCE_HANDOFF_PACKET_20260511.md`
- `src/yuantus/meta_engine/tests/test_p3_4_external_evidence_handoff_packet_contracts.py`
- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The new packet gives an operator a single current handoff point after Phase 4
and Phase 6 closed. It restates the active boundary:

- P3.4 is blocked until real operator-run non-production PostgreSQL rehearsal
  evidence exists and is accepted.
- Phase 5 provisioning/backup remains blocked by that evidence gate.
- Synthetic drill output and local command-path rehearsal remain rejected as
  completion evidence.
- `Ready for cutover: false` remains mandatory.

The packet references the canonical runbook instead of duplicating every
command path. It includes only the shortest approved path: repo-external env
file, env-file precheck, full-closeout wrapper, then evidence review.

## 4. Contract Coverage

The new contract pins four invariants:

1. The packet and this verification MD are indexed.
2. The packet is operator-action only and keeps Phase 5/P3.4 blocked.
3. The operator sequence stays ordered as env-template -> env precheck ->
   full-closeout -> evidence review.
4. The packet rejects synthetic evidence, plaintext secrets, and cutover-ready
   artifacts.

The contract is wired into the CI `contracts` job so future edits cannot weaken
the post-P6 handoff boundary silently.

## 5. Non-Goals

- No runtime code changes.
- No script behavior changes.
- No database connection.
- No real DSN, password, or token in tracked files.
- No production cutover.
- No Phase 5 implementation.
- No CAD plugin changes.

## 6. Verification Commands

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_p3_4_external_evidence_handoff_packet_contracts.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_p3_4_external_evidence_handoff_packet_contracts.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_p3_4_external_evidence_handoff_packet_contracts.py \
  src/yuantus/meta_engine/tests/test_next_cycle_post_p6_plan_gate_contracts.py \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m py_compile \
  src/yuantus/meta_engine/tests/test_p3_4_external_evidence_handoff_packet_contracts.py

git diff --check
```

## 7. Verification Results

- New handoff-packet contract: 4 passed.
- CI list-order + new handoff-packet contract: 5 passed.
- Focused suite (handoff packet + post-P6 gate + P3 stop-gate + doc-index
  trio): 23 passed.
- `py_compile` on the new contract: passed.
- `git diff --check`: clean.

## 8. Reviewer Checklist

- Confirm no runtime, migration, script, or CAD files changed.
- Confirm no real DSN or secret appears in tracked files.
- Confirm the packet keeps Phase 5 blocked until P3.4 evidence is accepted.
- Confirm synthetic drill output is explicitly rejected as real evidence.
- Confirm the delivery-doc index entries are alphabetically sorted.
