# Development And Verification: Odoo18 Workorder Version Lock Taskbook

## 1. Summary

This change adds an implementation taskbook for the highest-priority Odoo18 R2
gap: workorder document version locking.

It does not implement runtime behavior. The output is a bounded Claude Code
handoff document that turns the R2 analysis into an executable R1 implementation
slice.

## 2. Files

- `docs/DEVELOPMENT_CLAUDE_TASK_ODOO18_WORKORDER_VERSION_LOCK_20260515.md`
- `docs/DEV_AND_VERIFICATION_ODOO18_WORKORDER_VERSION_LOCK_TASKBOOK_20260515.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design Basis

The taskbook is grounded in the current code shape:

- `parallel_tasks_workorder_docs_router.py` owns the three workorder-doc routes.
- `WorkorderDocumentLink` stores routing, operation, and document item identity
  but no version pointer.
- `WorkorderDocumentPackService` already centralizes upsert, list, and export.
- `Operation.document_ids` exists but is not a version-lock mechanism.
- `ECOService.action_apply` already switches product current version and syncs
  version files, which is the narrowest possible apply-time projection point.

The taskbook chooses a narrow R1 instead of a broad MES domain:

- Add `document_version_id` lock metadata.
- Keep existing links backward compatible.
- Add export manifest/CSV lock metadata.
- Add opt-in export fail-closed behavior.
- Add only exact `document_item_id == ECO product_id` refresh semantics.

## 4. Claude Code Division

Claude Code is not needed for this docs-only taskbook PR.

Claude Code becomes useful after this taskbook is accepted, because the next
slice touches runtime code, migrations, ECO apply, and tests. That implementation
work is parallelizable from Codex review:

- Claude Code: implement R1 branch and write implementation DEV/verification MD.
- Codex: review diff, enforce scope, run focused verification, and block
  over-broad MES/quality/pack-and-go changes.

## 5. Scope Control

Included:

- Implementation-facing taskbook.
- Explicit public API additions.
- Data-model and migration requirements.
- Service, router, ECO, and migration test plan.
- Claude Code handoff rules.
- Delivery doc index entries.

Excluded:

- No runtime code.
- No database migration.
- No tenant baseline change.
- No route change.
- No CI workflow change.
- No production setting flip.
- No Phase unlock beyond the R1 taskbook.

## 6. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

```bash
git diff --check
```

## 7. Verification Results

| Check | Result |
|---|---|
| Doc-index trio | `4 passed in 0.04s` |
| `git diff --check` | clean |
| Runtime changes | none |
| Untracked local environment | `local-dev-env/` remains untracked and unstaged |

## 8. Review Checklist

- The taskbook is implementation-facing, not a runtime claim.
- The taskbook preserves backward compatibility by default.
- The taskbook requires version ownership validation.
- The taskbook keeps ECO projection exact and non-inferential.
- The taskbook names migration and tenant-baseline consequences.
- The taskbook explicitly excludes MES, quality, pack-and-go, and BOM archive
  scope.
