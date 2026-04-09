# Dirty Tree Domain Inventory

Date: `2026-04-09`
Branch: `feature/claude-c43-cutted-parts-throughput`

## Purpose

This note is a read-only scope audit for the current dirty working tree. It is
separate from the already-pushed PLM workspace bundle and should be used to
avoid accidental PR scope creep.

Helper commands:

```bash
bash scripts/print_dirty_tree_domain_commands.sh --list-domains
bash scripts/print_dirty_tree_domain_commands.sh --recommended-order
bash scripts/print_dirty_tree_domain_commands.sh --domain subcontracting --status
bash scripts/print_dirty_tree_domain_commands.sh --domain subcontracting --commit-plan
```

Execution order reference:
`docs/DIRTY_TREE_SPLIT_ORDER_20260409.md`

## Current dirty tree summary

From `git status --short` and Claude Code read-only sidecar:

- `503` dirty files total
  - `51` tracked-modified
  - `452` untracked
- `441` paths under `docs/`
- `54` paths under `src/`
- `4` paths under `migrations/`
- `3` paths under `scripts/`
- `1` top-level file: `CONTRIBUTING.md`

From `git diff --stat`:

- `51 files changed`
- `79,205 insertions`
- `455 deletions`

## Domain grouping

### 1. Subcontracting expansion

Largest scope by far. Key files:

- `src/yuantus/meta_engine/subcontracting/service.py`
- `src/yuantus/meta_engine/web/subcontracting_router.py`
- `src/yuantus/meta_engine/tests/test_subcontracting_router.py`
- `src/yuantus/meta_engine/tests/test_subcontracting_service.py`
- `src/yuantus/meta_engine/subcontracting/models.py`
- `src/yuantus/meta_engine/subcontracting/entry_contract.py`

Top-line diff stats:

- `subcontracting/service.py`: `+33,623 / -152`
- `test_subcontracting_router.py`: `+15,961 / -7`
- `web/subcontracting_router.py`: `+11,608 / -49`
- `test_subcontracting_service.py`: `+11,061 / -3`

This is the largest accidental-scope risk on the branch.

Claude sidecar conclusion:

- `subcontracting` accounts for roughly `72,000+` lines of the current dirty
  tree and is the clearest source of accidental PR scope creep.

### 2. Parallel documents / verification doc pack

The `docs/` tree is dominated by two prefixed families:

- `205` files: `DESIGN_PARALLEL_*`
- `205` files: `DEV_AND_VERIFICATION_PARALLEL_*`

These are mostly delivery/audit/readout artifacts and should not be mixed into
the current PLM workspace or pact review path unless intentionally bundled.

### 3. Approvals / ECO / document sync / parallel tasks

Cross-domain model, service, router, and test changes exist in:

- `src/yuantus/meta_engine/approvals/*`
- `src/yuantus/meta_engine/document_sync/*`
- `src/yuantus/meta_engine/services/eco_service.py`
- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `src/yuantus/meta_engine/web/approvals_router.py`
- `src/yuantus/meta_engine/web/document_sync_router.py`
- `src/yuantus/meta_engine/web/eco_router.py`
- `src/yuantus/meta_engine/web/file_router.py`
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`

These files are much smaller than the subcontracting block, but they expand the
review surface across unrelated product areas.

### 4. Migration + strict-gate support changes

Additional dirty paths exist in:

- `migrations/versions/*.py` (`4` files)
- `scripts/run_playwright_strict_gate.sh`
- `scripts/strict_gate.sh`
- `scripts/strict_gate_report.sh`
- `src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_playwright_runner.py`

These are operationally important, but they are still outside the native PLM
workspace scope.

### 5. Delivery package / handoff docs

Modified delivery files include:

- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DELIVERY_EXTERNAL_HANDOFF_GUIDE_20260203.md`
- `docs/DELIVERY_EXTERNAL_VERIFY_COMMANDS_20260203.md`
- `docs/DELIVERY_PACKAGE_HASHES_20260203.md`
- `docs/DELIVERY_PACKAGE_MANIFEST_20260203.txt`
- `docs/DELIVERY_PACKAGE_NOTE_20260203.md`
- `CONTRIBUTING.md`

These should be reviewed as a separate packaging / handoff bundle.

## Recommended next step

Safest path:

1. Do **not** widen the current PR scope.
2. Treat the dirty tree as a separate staging area from the already-pushed PLM
   workspace + pact work.
3. Split the next cleanup by domain, starting with `subcontracting`.
4. If temporary parking is needed, do it intentionally and outside the current
   reviewer path.

## Claude sidecar recommendation

Read-only Claude Code audit agrees with the local counts:

- do **not** `git add .`
- isolate branch-topic work first
- split `subcontracting` into its own branch or staging scope
- treat the `DEV_AND_VERIFICATION_*` document bulk as a separate doc pack, not
  part of the current review path

## Clean reviewer path

For the current branch review, prefer committed history only:

- Pact / provider verifier commits
- Native PLM workspace bundle commits
- Reviewer / helper / discoverability commits

Ignore the dirty tree unless the next task is explicitly “domain cleanup”.
