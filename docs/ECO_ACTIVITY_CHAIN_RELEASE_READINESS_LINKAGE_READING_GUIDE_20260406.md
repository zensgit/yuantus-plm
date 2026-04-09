# ECO Activity Chain → Release Readiness Linkage — Reading Guide

## Date

2026-04-06

## Who this is for

An engineer or reviewer encountering the ECO activity chain → release readiness
linkage for the first time.

---

## Recommended Reading Paths

### Shortest path (2 docs, ~10 min)

1. **Final Summary** — what was done, linkage points, zero gaps
2. **Linkage Audit** — dual-layer architecture, what was found

### Full implementation path (4 docs, ~20 min)

1. Final Summary (design + verification)
2. Linkage Audit (design + verification)
3. Apply Diagnostics Activity Gate Rule (design + verification)

---

## Document Map by Topic

### 1. Final Summary

*Answers: "Is the linkage complete? What diagnostics rules exist?"*

| Doc | Path |
|-----|------|
| Final Summary Design | `docs/DESIGN_..._LINKAGE_FINAL_SUMMARY_20260406.md` |
| Final Summary Verification | `docs/DEV_AND_VERIFICATION_..._LINKAGE_FINAL_SUMMARY_20260406.md` |

### 2. Linkage Audit

*Answers: "What is the dual-layer architecture? What was missing?"*

| Doc | Path |
|-----|------|
| Audit Design | `docs/DESIGN_..._LINKAGE_AUDIT_20260406.md` |
| Audit Verification | `docs/DEV_AND_VERIFICATION_..._LINKAGE_AUDIT_20260406.md` |

### 3. Apply Diagnostics Activity Gate Rule

*Answers: "How was the gap fixed? What code changed?"*

| Doc | Path |
|-----|------|
| Design | `docs/DESIGN_..._APPLY_DIAGNOSTICS_ACTIVITY_GATE_RULE_20260406.md` |
| Verification | `docs/DEV_AND_VERIFICATION_..._ACTIVITY_GATE_RULE_20260406.md` |

### 4. Activity Gate Layer

*Answers: "How do ECOActivityGate, dependency chains, and blockers_for_eco work?"*

Covered in linkage audit §Activity Gate Model and §Activity Chain Service.
Key: `ECOActivityGate` has `depends_on_activity_ids` for dependency chains.
`blockers_for_eco()` returns non-terminal blocking activities. `_ensure_activity_gate_ready()`
raises ValueError when blockers exist.

### 5. Release Diagnostics Layer

*Answers: "How does the rule-based validation work?"*

Covered in linkage audit §Release Readiness Validation. Key:
`ECO_APPLY_RULES_DEFAULT` defines the rule sequence. Each rule maps to a
handler in `get_apply_diagnostics()` that produces `ValidationIssue` objects.
Response uses `ReleaseDiagnosticsResponse` contract.

### 6. Apply / Unsuspend Linkage Surfaces

*Answers: "Where are the diagnostics exposed? How does apply block?"*

| Surface | Endpoint | Diagnostics | Runtime gate |
|---------|---------|:-----------:|:------------:|
| Apply | `POST /eco/{id}/apply` | `GET /eco/{id}/apply-diagnostics` | `_ensure_activity_gate_ready` |
| Unsuspend | `POST /eco/{id}/unsuspend` | `GET /eco/{id}/unsuspend-diagnostics` | `_ensure_activity_gate_ready` |
| Move stage | `POST /eco/{id}/move-stage` | — | `_ensure_activity_gate_ready` |

### 7. Remaining Non-Goals / Guardrails

- **CONFLICT state rule**: Conflicts checked via `rebase_conflicts_absent`, not
  a dedicated state-level rule. Non-blocking.
- **Activity gate notifications**: No explicit notification on activity status
  changes. Only stage assignment has notifications. Non-blocking.
- **Compound activity expressions**: Not supported. Activities are simple
  sequential gates with dependency chains.

---

## Key Source Files

| File | Role |
|------|------|
| `eco_service.py` | `get_apply_diagnostics`, `action_apply`, `_ensure_activity_gate_ready` |
| `release_validation.py` | `ECO_APPLY_RULES_DEFAULT` ruleset |
| `parallel_tasks_service.py` | `ECOActivityValidationService`, `blockers_for_eco` |
| `eco_router.py` | `/apply-diagnostics`, `/apply`, `/unsuspend-diagnostics` endpoints |

## Note on `...` abbreviations

Paths use `..._` to abbreviate `PARALLEL_ECO_ACTIVITY_CHAIN_RELEASE_READINESS`.
Full filenames in `docs/DELIVERY_DOC_INDEX.md`.
