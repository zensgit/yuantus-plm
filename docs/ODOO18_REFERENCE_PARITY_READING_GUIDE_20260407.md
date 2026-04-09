# Odoo18-Inspired Reference Parity — Reading Guide

## Date

2026-04-07

## Who this is for

An engineer or reviewer encountering the Odoo18-inspired reference parity
round for the first time. This is a **navigation** document — it points
at the per-line final summary + reading guide rather than duplicating
their content.

For the bottom-line "is the round done?" answer, read the Final Summary
first.

---

## Recommended Reading Paths

### Shortest path (2 docs, ~10 min)

1. **Final Summary (design)** — closure statement, sub-line roll-up,
   cross-cutting guardrails, non-goals / future-work bucket.
2. **Final Summary (verification)** — completion declarations in one
   place, per-line verification roll-up.

### Full implementation path (~75 min)

1. Final Summary (design + verification)
2. For each of the seven closed sub-lines, read its **own** final summary
   (design + verification) and reading guide. The per-line reading guides
   are themselves navigation docs into the audit / contract / probe /
   execute / coverage layers; you do not need to read every per-package
   doc unless you are working on that line specifically.

Suggested order matches the chronology in which the sub-lines closed:

1. Doc-sync checkout governance enhancement
2. Breakage helpdesk traceability enhancement
3. ECO BOM compare mode integration
4. Workflow custom action predicate upgrade
5. ECO suspension gate
6. ECO activity chain → release readiness linkage
7. Document sync mirror compatibility

---

## Document Map by Topic

### 1. Final Summary

*Answers: "Is the parity round closed? What guardrails apply across all sub-lines? What is intentionally out of scope?"*

| Doc | Path |
|-----|------|
| Final Summary Design | `docs/DESIGN_PARALLEL_ODOO18_REFERENCE_PARITY_FINAL_SUMMARY_20260407.md` |
| Final Summary Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_ODOO18_REFERENCE_PARITY_FINAL_SUMMARY_20260407.md` |

### 2. Doc-sync checkout governance enhancement

*Answers: "How does direction-scoped governance filter the doc-sync checkout surface?"*

| Doc | Path |
|-----|------|
| Final Summary Design | `docs/DESIGN_PARALLEL_DOC_SYNC_CHECKOUT_GOVERNANCE_ENHANCEMENT_FINAL_SUMMARY_20260404.md` |
| Final Summary Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_DOC_SYNC_CHECKOUT_GOVERNANCE_ENHANCEMENT_FINAL_SUMMARY_20260404.md` |
| Reading Guide | `docs/DOC_SYNC_CHECKOUT_GOVERNANCE_ENHANCEMENT_READING_GUIDE_20260404.md` |

### 3. Breakage helpdesk traceability enhancement

*Answers: "How does a breakage event resolve to a latest helpdesk ticket?"*

| Doc | Path |
|-----|------|
| Final Summary Design | `docs/DESIGN_PARALLEL_BREAKAGE_HELPDESK_TRACEABILITY_FINAL_SUMMARY_20260405.md` |
| Final Summary Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_BREAKAGE_HELPDESK_TRACEABILITY_FINAL_SUMMARY_20260405.md` |
| Reading Guide | `docs/BREAKAGE_HELPDESK_TRACEABILITY_READING_GUIDE_20260405.md` |

### 4. ECO BOM compare mode integration

*Answers: "How does the ECO surface present BOM compare results consistent with the standalone BOM compare contract?"*

| Doc | Path |
|-----|------|
| Final Summary Design | `docs/DESIGN_PARALLEL_ECO_BOM_COMPARE_MODE_INTEGRATION_FINAL_SUMMARY_20260405.md` |
| Final Summary Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_ECO_BOM_COMPARE_MODE_INTEGRATION_FINAL_SUMMARY_20260405.md` |
| Reading Guide | `docs/ECO_BOM_COMPARE_MODE_INTEGRATION_READING_GUIDE_20260405.md` |

### 5. Workflow custom action predicate upgrade

*Answers: "What predicates does the workflow custom action engine accept now? What is the backward-compat story?"*

| Doc | Path |
|-----|------|
| Final Summary Design | `docs/DESIGN_PARALLEL_WORKFLOW_CUSTOM_ACTION_PREDICATE_UPGRADE_FINAL_SUMMARY_20260406.md` |
| Final Summary Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_WORKFLOW_CUSTOM_ACTION_PREDICATE_UPGRADE_FINAL_SUMMARY_20260406.md` |
| Reading Guide | `docs/WORKFLOW_CUSTOM_ACTION_PREDICATE_UPGRADE_READING_GUIDE_20260406.md` |

### 6. ECO suspension gate

*Answers: "How does the ECO suspension gate participate in the apply / unsuspend / move-stage runtime gate, and how do its diagnostics line up?"*

| Doc | Path |
|-----|------|
| Final Summary Design | `docs/DESIGN_PARALLEL_ECO_SUSPENSION_GATE_FINAL_SUMMARY_20260406.md` |
| Final Summary Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_ECO_SUSPENSION_GATE_FINAL_SUMMARY_20260406.md` |
| Reading Guide | `docs/ECO_SUSPENSION_GATE_READING_GUIDE_20260406.md` |

### 7. ECO activity chain → release readiness linkage

*Answers: "How is the ECO activity gate linked into the release readiness diagnostics layer?"*

| Doc | Path |
|-----|------|
| Final Summary Design | `docs/DESIGN_PARALLEL_ECO_ACTIVITY_CHAIN_RELEASE_READINESS_LINKAGE_FINAL_SUMMARY_20260406.md` |
| Final Summary Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_ECO_ACTIVITY_CHAIN_RELEASE_READINESS_LINKAGE_FINAL_SUMMARY_20260406.md` |
| Reading Guide | `docs/ECO_ACTIVITY_CHAIN_RELEASE_READINESS_LINKAGE_READING_GUIDE_20260406.md` |

### 8. Document sync mirror compatibility

*Answers: "How does an operator stand up a BasicAuth outbound mirror to a peer document_sync deployment, end to end?"*

| Doc | Path |
|-----|------|
| Final Summary Design | `docs/DESIGN_PARALLEL_DOCUMENT_SYNC_MIRROR_COMPATIBILITY_FINAL_SUMMARY_20260407.md` |
| Final Summary Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_DOCUMENT_SYNC_MIRROR_COMPATIBILITY_FINAL_SUMMARY_20260407.md` |
| Reading Guide | `docs/DOCUMENT_SYNC_MIRROR_COMPATIBILITY_READING_GUIDE_20260407.md` |

### 9. Current Implemented Parity Scope

*Answers: "What can the platform actually do today as a result of this round?"*

Across the seven lines, the parity round added or hardened:

- **Governance / gating**: doc-sync checkout governance scoping, ECO
  suspension gate, ECO activity-chain → apply-diagnostics linkage.
- **Compare semantics**: ECO BOM compare mode integration into the ECO
  surface.
- **Predicate engine**: workflow custom action predicate upgrade
  (backward-compatible widening).
- **Traceability**: breakage → helpdesk latest-ticket linkage.
- **Outbound mirror**: document_sync site auth contract + BasicAuth
  outbound probe + read-through execute + job mapping.

Each line is independently shippable and independently reversible. No
line introduced a new database migration that the others depend on.

### 10. Non-goals / Future-work bucket

*Answers: "What is intentionally NOT in this round? What might a future audit pick up?"*

Covered in the Final Summary (design) under §Non-goals / Future-work
bucket. None of these are blockers for this closure package; they are
candidate audit topics for a future round:

- Mirror line beyond the minimal contract (board / export / readiness /
  batch / async / retry / additional auth schemes / per-document mirror
  records).
- ECO line beyond release readiness (CONFLICT-state rule, activity-status
  notifications, compound activity expressions).
- Workflow predicate line (visual builder, versioning / migration,
  predicate-debugger surface).
- BOM compare line (non-adjacent ECO revision compare, three-way merge UI).
- Helpdesk traceability line (bidirectional navigation, full helpdesk
  domain port).
- Doc-sync checkout governance line (per-direction policy scopes, policy
  diffs / changelogs).

---

## Cross-cutting guardrails (recap)

- Stable error mapping: every router surface added in this round maps
  service-layer `ValueError` to `HTTPException(400)` and never raises
  HTTP 500 from a foreseeable failure mode.
- No silent fabrication: where a contract had no data, the
  implementation deliberately avoided fabricating it.
- Minimal patches: every line was scoped to the smallest change that
  closed the audit-identified gap.
- Same five-document pattern per line (audit → design → verification →
  final summary → reading guide).

## Note on dates

The seven sub-lines span `20260403`–`20260407`. This closure package is
dated `20260407` and references each sub-line's authoritative final
summary date in the document map above. This guide does not introduce
any new conclusions of its own — it is purely a navigation layer over
the existing per-line docs.
