# P1 CAD Legacy Conversion Queue Audit

Date: 2026-04-14

## Goal

Prepare the deletion window for legacy `cad_conversion_jobs` without changing
runtime behavior.

This slice adds:

1. a repeatable audit CLI for legacy queue rows
2. a code-reference scan for remaining legacy usage
3. an operator runbook for evidence-pack generation

## Scope

Touched files:

- `scripts/audit_legacy_cad_conversion_jobs.py`
- `src/yuantus/meta_engine/tests/test_audit_legacy_cad_conversion_jobs_script.py`
- `docs/DESIGN_P1_CAD_LEGACY_CONVERSION_QUEUE_AUDIT_20260414.md`
- `docs/RUNBOOK_CAD_LEGACY_CONVERSION_QUEUE_AUDIT.md`

## What changed

### 1. Added an audit-only CLI

New script:

```text
scripts/audit_legacy_cad_conversion_jobs.py
```

It audits legacy queue rows and reports:

- counts by status
- counts by target format
- counts by operation type
- counts by anomaly flag
- `active_job_count`
- `legacy_queue_drain_complete`
- `legacy_dual_read_zero_rows`

### 2. Added code-reference scanning

The script now also scans the repo for Python references to the legacy queue,
including:

- `cad_conversion_jobs`
- `create_conversion_job(...)`
- `meta_engine.models.file import ConversionJob`
- legacy `query/get(ConversionJob)` only when `ConversionJob` is actually bound
  from `yuantus.meta_engine.models.file`

It classifies hits by scope:

- `production`
- `test`
- `script`
- `doc`

and reports:

- `code_reference_count`
- `code_reference_counts_by_scope`
- `code_reference_counts_by_kind`

### 3. Added strict delete-window readiness signal

The script emits:

- `delete_window_ready`

This is `true` only when:

- active legacy jobs are zero
- legacy row count is zero
- production code references are zero

### 4. Added evidence-pack output

When `--out-dir` is provided, the script writes:

- `summary.json`
- `jobs.jsonl`
- `pending.jsonl`
- `anomalies.jsonl`
- `samples.json`
- `code_references.jsonl`

## Verification

### Focused script tests

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_audit_legacy_cad_conversion_jobs_script.py \
  src/yuantus/meta_engine/tests/test_cad_converter_service_queue_shim.py
```

Observed:

- `7 passed`

### Syntax check

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  scripts/audit_legacy_cad_conversion_jobs.py \
  src/yuantus/meta_engine/tests/test_audit_legacy_cad_conversion_jobs_script.py
```

Observed:

- passed

### Script dry-run in clean mainline worktree

```bash
python3 scripts/audit_legacy_cad_conversion_jobs.py \
  --limit 20 \
  --detail-limit 5 \
  --out-dir /tmp/yuantus-cad-legacy-audit \
  --json-out /tmp/yuantus-cad-legacy-audit/report.json
```

Observed:

- command completed successfully
- evidence files were produced under `/tmp/yuantus-cad-legacy-audit`
- current summary showed:
  - `legacy_table_present = false`
  - `job_count = 0`
  - `code_reference_count = 23`
  - `code_reference_counts_by_scope.production = 1`
  - `blocking_production_reference_count = 0`
  - `delete_window_ready = true`

The remaining production references are non-blocking by contract:

- `src/yuantus/meta_engine/services/cad_converter_service.py`
  - deprecated shim method definition only

## Outcome

This slice now gives a repeatable, reviewable delete-window signal:

- how many legacy rows still exist
- whether any active/anomalous rows remain
- whether any blocking production code still references the legacy path

## Claude Code CLI

This round did call `Claude Code CLI` as a read-only sidecar.

Observed:

- CLI is authenticated
- short prompts returned successfully
- it recommended an audit-first slice before deletion, which matches the path
  implemented here

Core implementation and verification still remained local.
