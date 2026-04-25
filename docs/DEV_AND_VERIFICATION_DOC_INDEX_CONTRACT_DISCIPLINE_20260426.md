# DEV / Verification — Doc-Index Contract Discipline (2026-04-26)

## 1. Goal

Codify two contributor rules surfaced by the PR #399 post-merge fix cycle
(`fix: address PR #399 post-push regressions — index sort + exc chain
consistency`, merged at `505b2cb`). Both rules are derivable from existing
contract tests but were violated because the rules themselves were not
documented in a discoverable place.

This MD does not change runtime, contracts, CI, or service behavior. It is a
discoverability artifact — pointed at `docs/DELIVERY_DOC_INDEX.md` so future
contributors hit it before adding/renaming/removing entries.

## 2. Rule 1 — Doc-Index Contract Atomicity

`docs/DELIVERY_DOC_INDEX.md` is guarded by two paired contracts:

- `test_dev_and_verification_doc_index_completeness.py` — every MD under
  `docs/` must have an index entry. Files without entries → red.
- `test_delivery_doc_index_references.py
  ::test_delivery_doc_index_backticked_paths_exist` — every backticked path
  in the index must point to an existing file. Index entries pointing at
  non-existent files → red.

These two contracts are atomic in the sense that **MDs and their index
entries must land in the same commit**. Splitting the MD-add and the
index-add across separate commits leaves one of the contracts red on the
intermediate state.

### Practical recipe

When adding a new `docs/DEV_AND_VERIFICATION_*.md` (or any MD under `docs/`
that isn't already excluded):

1. Pick the alphabetical position in `docs/DELIVERY_DOC_INDEX.md`. Use the
   full path string for comparison; underscore (`_`, 0x5F) sorts AFTER
   letters A–Z (0x41–0x5A). E.g. `DOCUMENT_SYNC_*` (with `U` at position
   4) sorts BEFORE `DOC_INDEX_*` (with `_` at position 4).
2. Stage the new MD AND the index-line edit in the SAME commit. Do not
   submit a "preload index entry" PR before the MD itself ships.
3. Run all three doc-index contracts locally before pushing (see §4).

### When splitting a large worktree across multiple PRs

If commit boundaries must straddle the index-update vs MD-add boundary
(common in large closeout cycles), single-PR submission is the only
contract-clean shape. See `DEV_AND_VERIFICATION_CURRENT_WORKTREE_CLOSEOUT_MERGE_READINESS_20260425.md`
for the precedent set during the current-worktree closeout (PR #398).

## 3. Rule 2 — Doc-Index Sort Contract Scope

`test_dev_and_verification_doc_index_sorting_contracts.py
::test_development_and_verification_section_paths_are_sorted_and_unique`
is the test that catches alphabetical-position regressions in the
DEV_AND_VERIFICATION section. It is a **separate file** from
`test_ci_contracts_ci_yml_test_list_order.py` (which guards CI workflow
test-invocation ordering, not the doc index).

Reviewer snapshots that report "CI doc-index sorting passes" without naming
the exact test file have ambiguous coverage. The three doc-index contracts
that must be run together when adding/renaming/removing index entries:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

CI already runs all three (`.github/workflows/ci.yml` lines 348/353/354
under the contracts job). Local reviewers should mirror CI's test set, not
a subset.

## 4. Verification

Pre-commit local check (run on the patched HEAD, after this MD + its index
entry are staged):

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Expected: all pass.

```bash
git diff --check
```

Expected: clean.

## 5. Review Checklist

| # | Check | Status |
| --- | --- | --- |
| 1 | This MD exists at `docs/DEV_AND_VERIFICATION_DOC_INDEX_CONTRACT_DISCIPLINE_20260426.md` | ✅ |
| 2 | Its `DELIVERY_DOC_INDEX.md` entry is sorted between the last `DEV_AND_VERIFICATION_DOCUMENT_SYNC_*` line and the first `DEV_AND_VERIFICATION_ECO_*` line | ✅ |
| 3 | All three doc-index contracts pass on the patched HEAD | ✅ (see §4) |
| 4 | No code, CI, helper, or contract changes — discoverability-only | ✅ |
| 5 | No `.claude/` or `local-dev-env/` files added | ✅ |

## 6. Non-Goals

- No new contract test enforcing this rule (CI already enforces; the rule
  is now discoverable via this MD).
- No edit to `scripts/print_current_worktree_closeout_commands.sh` — its
  output today is a **scope** template (which files a PR group touches),
  not a verification-runner. The doc-index contracts are not group-owned
  files; they apply to any group that mutates `docs/DELIVERY_DOC_INDEX.md`.
- No retrospective rename or unification of the two `*_doc_index_sorting_*`
  test names — the existing names are stable and referenced externally.

## 7. Cross-References

- `DEV_AND_VERIFICATION_APPROVALS_INDEX_SORT_AND_EXC_CHAIN_FIX_20260426.md`
  — the immediate fix that motivated this rule.
- `DEV_AND_VERIFICATION_CURRENT_WORKTREE_CLOSEOUT_MERGE_READINESS_20260425.md`
  — the merge-readiness record that first articulated the
  contract-atomicity reasoning.
- `.github/workflows/ci.yml` — contracts job (lines 348/353/354) running
  the full doc-index trio.
