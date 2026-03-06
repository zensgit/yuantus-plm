# Parallel P3 Design: Ops Overview Checkout Gate/Trend + BOM by_find_refdes

Date: 2026-03-06

## Background

This iteration continues the parallel P3 branch with three additive tracks:

1. Extend ops overview with checkout-gate threshold snapshots.
2. Add doc-sync dead-letter trend signal and alert hint.
3. Add doc-sync direction dimensions (`push/pull`) in trends/failures/export.
4. Extend BOM compare mode for `find_num + refdes` use-cases.

The goal is to strengthen operational observability and keep BOM diff strategies aligned with engineering review workflows.

## Odoo18 Reference Mapping

- `references/odoo18-enterprise-main/addons/plm_document_multi_site/*`
  - Borrowed idea: expose sync-backlog policy state to operators, not just pass/fail.
- `references/odoo18-enterprise-main/addons/plm_compare_bom/*`
  - Borrowed idea: expose compare strategies for different comparison intents, including reference-oriented keys.

## Design Decisions

### 1) Ops overview checkout-gate snapshot

- Add optional thresholds/policy query knobs on ops overview APIs:
  - `doc_sync_checkout_gate_block_on_dead_letter_only`
  - `doc_sync_checkout_gate_max_pending_warn`
  - `doc_sync_checkout_gate_max_processing_warn`
  - `doc_sync_checkout_gate_max_failed_warn`
  - `doc_sync_checkout_gate_max_dead_letter_warn`
- Compute `doc_sync.checkout_gate` in summary:
  - `enabled`, `policy`, `thresholds`, `counts`
  - `threshold_hits`, `threshold_hits_total`, `is_blocking`
- Rule is strict and transparent: threshold hit when `count > threshold`.

### 2) Dead-letter trend snapshot and warning

- Add `doc_sync.dead_letter_trend` snapshot:
  - fixed daily buckets (`bucket_days=1`) over selected window
  - per-bucket totals + dead-letter totals + rate
  - aggregates: `first/latest/min/max/delta/nonzero`
- Add optional warn threshold:
  - `doc_sync_dead_letter_trend_delta_warn`
- Emit summary hint code:
  - `doc_sync_dead_letter_trend_up` when trend delta exceeds configured warn value.

### 3) Doc-sync direction dimensions in trends/failures/export

- For ops trends buckets, add per-bucket doc-sync direction counters:
  - `doc_sync.directions`
  - `doc_sync.dead_letter_directions`
- For trend aggregates/export, add direction totals:
  - `doc_sync_push_total`, `doc_sync_pull_total`
  - dead-letter direction totals for push/pull
- For doc-sync failure listing, add `direction` per row and `by_direction` summary.

### 4) Export + metrics wiring

- Carry new knobs and summary fields through:
  - `summary`, `alerts`, `export_summary`, `prometheus_metrics`
- Add Prometheus metrics:
  - `yuantus_parallel_doc_sync_checkout_gate_threshold_hits_total`
  - `yuantus_parallel_doc_sync_checkout_gate_blocking`
  - `yuantus_parallel_doc_sync_dead_letter_trend_delta`
  - per-status threshold hit/value/exceeded gauges
- Add export rows for new checkout-gate/trend fields.

### 5) BOM compare mode extension

- Add `by_find_refdes` compare mode:
  - `line_key=child_config_find_refdes`
  - relationship props: `quantity,uom,find_num,refdes`
- Add aliases:
  - `by_find_ref`, `find_refdes`, `find_ref`, `child_config_find_refdes`
- Keep existing modes unchanged and generate invalid-mode message from current mode registry.

### 6) Runtime/runbook examples

- Extend runtime and delivery API docs with gate-policy templates:
  - `strict` template
  - `tolerant` template
- Add troubleshooting focus on policy/threshold/blocking reason fields.

## Compatibility and Risks

- No schema migration.
- All new API fields are additive.
- Existing callers are unaffected if they do not pass new knobs.
- Main risk is client-side strict schema assumptions; mitigated by non-breaking additive response keys.
