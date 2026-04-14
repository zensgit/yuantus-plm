# P1 - CAD Legacy Conversion Queue Audit

Date: 2026-04-14

## Problem

The clean-mainline CAD queue is now mostly converged on `meta_conversion_jobs`,
but legacy `cad_conversion_jobs` still exists in two forms:

- compatibility reads
- code references that may still block a safe delete window

Without a repeatable audit, we cannot answer:

1. whether the legacy queue is actually drained
2. whether the remaining rows are anomalous
3. whether production code still references the legacy path

## Design Goal

Add an audit-first tool that:

- does not mutate data
- works in tenant-aware deployments
- emits evidence files for review
- combines:
  - database row audit
  - code-reference scan

## Scope

- `scripts/audit_legacy_cad_conversion_jobs.py`
- `src/yuantus/meta_engine/tests/test_audit_legacy_cad_conversion_jobs_script.py`
- `docs/RUNBOOK_CAD_LEGACY_CONVERSION_QUEUE_AUDIT.md`

## Chosen Contract

### 1. Audit-only CLI

The script remains read-only.

Supported flags:

- `--tenant`
- `--org`
- `--limit`
- `--detail-limit`
- `--json-out`
- `--out-dir`
- `--repo-root`

### 2. Evidence pack

When `--out-dir` is provided, the script writes:

- `summary.json`
- `jobs.jsonl`
- `pending.jsonl`
- `anomalies.jsonl`
- `samples.json`
- `code_references.jsonl`

### 3. Readiness contract

The script reports:

- `legacy_queue_drain_complete`
- `legacy_dual_read_zero_rows`
- `code_reference_count`
- `code_reference_counts_by_scope`
- `delete_window_ready`

`delete_window_ready` is intentionally strict:

- no active legacy jobs
- zero legacy rows
- zero production code references

## Why This Slice

- It is the smallest safe step before deleting dual-read fallback.
- It gives one operator artifact instead of ad hoc grep + SQL.
- It does not force a migration decision before evidence exists.

## Deferred

- soft-rename or hard-drop of `cad_conversion_jobs`
- production caller telemetry
- deletion migration itself
