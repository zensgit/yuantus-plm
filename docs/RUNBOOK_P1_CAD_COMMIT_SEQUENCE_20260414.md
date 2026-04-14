# Runbook: P1 CAD Commit Sequence

Date: 2026-04-14

## Goal

Take the clean mainline worktree's accumulated CAD/mainline changes and turn
them into a small sequence of reviewable commits without replaying old feature
branches.

This runbook assumes the active worktree is:

- `/Users/chouhua/Downloads/Github/Yuantus-worktrees/mainline-20260414-150835`

## Commit slicing rule

Use thematic slices, not file-by-file chronology:

1. baseline switch docs
2. CAD runtime mainline convergence
3. CAD legacy cleanup and schema removal
4. final docs/index/commit-prep glue

Why:

- `docs/DELIVERY_DOC_INDEX.md` spans multiple slices and is easier to land last
- runtime and legacy-removal code review better when separated
- historical transition docs should stay grouped with the code they explain

## Command generator

Use:

```bash
bash scripts/print_p1_cad_commit_sequence_commands.sh
```

The script prints:

- `git add -- ...` for each slice
- a suggested commit message
- a coverage footer proving every current changed file belongs to some slice

If coverage is incomplete, the script exits non-zero and lists uncovered files.

## Recommended slice contents

### 1. baseline-switch-docs

- baseline correction audit
- branch merge risk audit
- mainline switch planning/execution/preview docs
- PLM workspace manual replay plan
- mainline switch runbook and helper script

### 2. cad-runtime-mainline

- checkin queue binding
- checkin status
- file conversion summary/job queue/upload preview queue
- canonical queue runtime code and related tests

### 3. cad-legacy-cleanup

- legacy audit script
- legacy queue delete-window readiness docs
- legacy model removal
- table drop migration
- final closeout

### 4. docs-index-and-commit-prep

- `docs/DELIVERY_DOC_INDEX.md`
- this runbook
- commit prep verification doc
- commit command generator script

## Verification before each commit

- run the smallest focused tests for that slice
- avoid mixing unrelated hunks into `docs/DELIVERY_DOC_INDEX.md`
- keep `git diff --cached --stat` readable before committing

## Verification after the final slice

- run the audit script once more
- keep the final closeout doc as the current steady-state reference
