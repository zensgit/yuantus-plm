# P1 CAD Commit Sequence Prep

Date: 2026-04-14

## Goal

Prepare the clean mainline worktree for actual commits by producing an explicit
commit sequence and verifying that all current changed files are covered by it.

## Scope

Touched files:

- `scripts/print_p1_cad_commit_sequence_commands.sh`
- `docs/RUNBOOK_P1_CAD_COMMIT_SEQUENCE_20260414.md`
- `docs/DEV_AND_VERIFICATION_P1_CAD_COMMIT_SEQUENCE_PREP_20260414.md`
- `docs/DELIVERY_DOC_INDEX.md`

## What changed

### 1. Added a commit-sequence command generator

New helper:

```text
scripts/print_p1_cad_commit_sequence_commands.sh
```

It prints four suggested slices:

1. `baseline-switch-docs`
2. `cad-runtime-mainline`
3. `cad-legacy-cleanup`
4. `docs-index-and-commit-prep`

### 2. Added coverage validation

The script inspects the current `git status --porcelain` set and compares it
against the union of all slice file lists.

If any changed file is not assigned to a slice:

- it prints the uncovered paths
- exits non-zero

### 3. Added an operator runbook

`docs/RUNBOOK_P1_CAD_COMMIT_SEQUENCE_20260414.md` explains:

- why `DELIVERY_DOC_INDEX.md` is deferred to the last slice
- which files belong to which thematic slice
- how to use the script safely before staging

## Verification

### Shell syntax check

```bash
bash -n scripts/print_p1_cad_commit_sequence_commands.sh
```

Observed:

- passed

### Command generator smoke

```bash
bash scripts/print_p1_cad_commit_sequence_commands.sh | sed -n '1,120p'
```

Observed:

- script printed all four slice command blocks
- suggested commit messages were present
- coverage footer reported `uncovered_files=0`

### Current coverage result

Observed from the generator:

- all current changed files in the clean mainline worktree are assigned
- no additional manual slice is required before committing

## Outcome

This slice does not change product behavior. It makes the current CAD/mainline
worktree commit-ready by turning a large uncommitted batch into an explicit,
verifiable commit sequence.

## Claude Code CLI

This round did call `Claude Code CLI` as a read-only sidecar.

Observed:

- CLI is logged in
- short prompt guidance supported using one final closeout doc instead of
  rewriting all historical slice docs

Core implementation and verification still remained local.
