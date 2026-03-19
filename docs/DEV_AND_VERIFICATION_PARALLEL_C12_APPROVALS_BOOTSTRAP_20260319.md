# C12 – Approvals Bootstrap: Development & Verification

## Branch

`feature/claude-c12-approvals-bootstrap` (based on `main`)

## Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | `ApprovalCategory` and `ApprovalRequest` models with enums | PASS |
| 2 | State machine: draft→pending→approved/rejected/cancelled, rejected→pending resubmission | PASS |
| 3 | CRUD endpoints for categories and requests | PASS |
| 4 | Transition endpoint with validation error handling (400) | PASS |
| 5 | Summary endpoint with by_state/by_priority aggregation | PASS |
| 6 | 404 for missing request | PASS |
| 7 | Priority validation rejects invalid values | PASS |
| 8 | All tests pass | PASS |

## Test Results

```
20 passed in 1.15s

Service tests (13):
  TestApprovalCategories      – 2 passed
  TestApprovalRequests        – 9 passed
  TestApprovalSummary         – 2 passed

Router tests (7):
  test_category_crud                – PASS
  test_request_create_and_list      – PASS
  test_request_transition           – PASS
  test_request_get                  – PASS
  test_request_get_404              – PASS
  test_summary_endpoint             – PASS
  test_transition_validation_error  – PASS
```

## Key Design Decisions

1. **Entity-agnostic binding**: `entity_type` + `entity_id` columns allow any domain to attach approval workflows without schema changes.
2. **Resubmission path**: Rejected requests can transition back to pending, supporting iterative review cycles.
3. **Terminal states**: Approved and cancelled are terminal — no further transitions allowed.
4. **JSONB properties**: Extensible metadata column for domain-specific data without schema migration.
5. **Standalone test pattern**: Router tests use minimal FastAPI app to avoid dependency on `app.py`.

## Path Guard

Profile `C12` added to `contracts/claude_allowed_paths.json` covering all 6 source files.
