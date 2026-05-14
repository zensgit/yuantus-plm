# Dev & Verification - Claude Code Public Docs Discipline

Date: 2026-05-14

## 1. Summary

Aligned the public Claude Code entrypoint docs with the helper/runbook
discipline now enforced by #558 and #559.

This is docs/contracts only. It does not start Phase 5, synthesize P3.4
evidence, or change runtime behavior.

## 2. Files Changed

- `README.md`
- `docs/VERIFICATION.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `src/yuantus/meta_engine/tests/test_ci_contracts_claude_code_parallel_helper.py`
- `docs/DEV_AND_VERIFICATION_CLAUDE_CODE_PUBLIC_DOCS_DISCIPLINE_20260514.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The helper scripts and runbook already enforce the safe Claude Code discipline:

- read-only/reviewer mode uses `claude -p --no-session-persistence --tools ""`
- Claude Code output is advisory
- write-mode worktree usage requires explicit user authorization
- `.claude/` and `local-dev-env/` must not be committed

This PR propagates those rules to the public docs that developers are likely to
read first: `README.md`, `docs/VERIFICATION.md`, and the delivery scripts
index.

## 4. Claude Code Assist

Claude Code was used read-only to evaluate the next safe slice. It recommended
documenting helper contracts before any Phase 5/P3.4 work. It did not edit
files.

## 5. Non-Goals

- No runtime code changes.
- No helper script behavior changes.
- No Phase 5 implementation.
- No P3.4 evidence synthesis or cutover enablement.
- No new Claude Code helper script.

## 6. Verification Commands

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_claude_code_parallel_helper.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_claude_code_assist_discipline.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py

git diff --check
```

## 7. Verification Results

- Focused contract suite:
  - Claude Code parallel helper contract
  - Claude Code assist discipline contract
  - doc-index trio
  - CI list-order contract
  - Result: `10 passed`.
- `git diff --check`: clean.

## 8. Review Checklist

- Confirm this PR is docs/contracts only.
- Confirm README and VERIFICATION mention read-only default and advisory-only
  Claude Code output.
- Confirm public docs mention `claude -p --no-session-persistence --tools ""`.
- Confirm write-mode worktree usage still requires explicit user authorization.
- Confirm no `.claude/` or `local-dev-env/` files are staged.

This file is indexed as
`docs/DEV_AND_VERIFICATION_CLAUDE_CODE_PUBLIC_DOCS_DISCIPLINE_20260514.md`.
