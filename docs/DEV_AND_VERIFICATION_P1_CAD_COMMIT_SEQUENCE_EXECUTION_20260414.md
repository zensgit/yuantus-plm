# P1 CAD Commit Sequence Execution

Date: 2026-04-14

## Goal

Record the actual execution of the prepared commit sequence in the clean
mainline worktree and verify that the resulting branch is in a reviewable
steady state.

Worktree:

- `/Users/chouhua/Downloads/Github/Yuantus-worktrees/mainline-20260414-150835`

Branch:

- `baseline/mainline-20260414-150835`

## Executed commit sequence

### 1. Baseline switch docs

- `97892ef` `docs: add mainline baseline switch audit and runbook`

### 2. CAD runtime mainline convergence

- `acd634a` `feat(plm): move cad checkin and file conversion runtime to canonical queue`

### 3. CAD legacy cleanup

- `8e1345b` `refactor(plm): remove legacy cad conversion queue runtime and add schema removal`

### 4. Docs/index/commit prep

- `64fdd22` `docs: add p1 cad closeout index and commit prep guidance`

## What was verified after the four commits

### 1. Working tree state

Immediately after the fourth commit:

- `git status --short` returned clean
- `git rev-list --left-right --count origin/main...HEAD` returned `0 4`

That means:

- no uncommitted residue remained
- the branch was exactly four commits ahead of `origin/main`

### 2. Focused post-commit regression

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_checkin_manager.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_transaction.py \
  src/yuantus/meta_engine/tests/test_cad_pipeline_version_binding.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_status_router.py \
  src/yuantus/meta_engine/tests/test_file_conversion_router_job_queue.py \
  src/yuantus/meta_engine/tests/test_file_conversion_summary_router.py \
  src/yuantus/meta_engine/tests/test_file_upload_preview_queue.py \
  src/yuantus/meta_engine/tests/test_cad_converter_service_queue_shim.py \
  src/yuantus/meta_engine/tests/test_audit_legacy_cad_conversion_jobs_script.py
```

Observed:

- `45 passed, 5 warnings`

Warnings were the same previously seen environment-level warnings:

- `urllib3/LibreSSL`
- Pydantic deprecation warnings in mocked router tests

### 3. Post-commit legacy audit

```bash
PYTHONPATH=src python3 scripts/audit_legacy_cad_conversion_jobs.py \
  --limit 20 \
  --detail-limit 5 \
  --out-dir /tmp/yuantus-cad-legacy-audit-post-commits \
  --json-out /tmp/yuantus-cad-legacy-audit-post-commits/report.json
```

Observed:

- `legacy_table_present = false`
- `job_count = 0`
- `code_reference_count = 18`
- `code_reference_counts_by_scope.production = 0`
- `blocking_production_reference_count = 0`
- `delete_window_ready = true`

## Outcome

The prepared four-slice commit sequence was executed successfully.

Resulting branch state:

- clean working tree after the sequence
- CAD runtime is on canonical queue paths
- legacy CAD queue runtime is removed
- schema-removal migration exists
- post-removal audit remains green

## Next step

This branch is ready for:

1. push
2. PR creation / review
3. optional broader regression outside the focused CAD slice

## Limits

- This round did not run full-repository regression
- Verification remained focused on the CAD queue/checkin/read-surface and
  legacy-audit slices

## Claude Code CLI

This round could call `Claude Code CLI`, but the actual commit execution and
verification stayed local because local git + targeted tests were more
deterministic for this step.
