# External Signal Collection

Date: 2026-04-22

## 1. Goal

Record the currently available external or operational signal for choosing the next development track.

This is not a feature request document and does not expand scope into MES, sales, procurement, or UI work.

## 2. Available Signal

| Question | Available signal | Conclusion |
| --- | --- | --- |
| Does BOM router decomposition affect a current delivery timeline? | No blocking delivery timeline was provided in the current conversation. The codebase still shows `bom_router.py` as a large hotspot. | Proceed with a taskbook first; implementation should be bounded and reversible. |
| Is there a real adopter ready to run scheduler in production? | No pilot owner, production-like pilot environment, or operations commitment was provided. | Do not start production scheduler rehearsal yet. Use the decision gate to choose rehearsal or default-off maintenance. |
| Is CAD backend/profile customer-side selection sufficient? | CAD backend/profile work and shared-dev smoke records are complete for current backend scope. No new customer request was provided. | Treat CAD profile as stable for now; do not start another CAD profile feature by default. |
| What is the next customer-visible value? | No new customer-facing request was provided. Existing engineering evidence points to BOM maintainability and decomposition as the next low-risk track. | Prioritize BOM router decomposition taskbook; defer UI until a clear pull signal exists. |

## 3. Collection Methods Used

- Current repository state after PR #366.
- Existing closeout and next-cycle planning documents.
- Prior shared-dev and scheduler delivery records already indexed in `docs/DELIVERY_DOC_INDEX.md`.
- No new live customer interview, telemetry export, or 142 bootstrap was performed.

## 4. Decision

Proceed with:

1. `docs/DEVELOPMENT_CLAUDE_TASK_BOM_ROUTER_DECOMPOSITION_20260422.md`
2. BOM compare split as the first implementation slice after taskbook review.

Do not proceed with:

- scheduler production rehearsal,
- UI feature work,
- CAD profile expansion,
- shared-dev first-run bootstrap,
- MES / sales / procurement expansion.

These require explicit external pull signal before activation.

## 5. Open Signals To Collect Later

- Named scheduler pilot owner.
- Shared-dev or production-like pilot environment for scheduler.
- Operations owner for scheduler monitoring and rollback.
- Customer request for BOM UI, CAD viewer, approval UI, or CAD backend profile expansion.
- Delivery timeline that requires BOM router work to pause.

## 6. Verification

Documentation-only change. Required verification:

```bash
git diff --check

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```
