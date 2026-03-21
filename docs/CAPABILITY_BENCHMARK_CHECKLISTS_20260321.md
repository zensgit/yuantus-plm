# Yuantus Capability Benchmark Checklists

## Purpose

This document turns the benchmark decision from
`docs/BENCHMARK_TARGET_MATRIX_20260321.md` into execution checklists for the
active work areas most likely to continue under parallel development.

It is intended to answer two practical questions:

1. which benchmark target applies to each active domain
2. what capability evidence and acceptance checks should be reviewed before the
   next parallel batch expands that domain again

## Active Domain Summary

| Domain | Primary Benchmark | Current Repository State |
| --- | --- | --- |
| `box` | `Odoo18 PLM` | Bootstrap through `C44` exists and is codex-stack-verified |
| `document_sync` | `Odoo18 PLM` | Bootstrap through `C45` exists and is codex-stack-verified |
| `cutted_parts` | `Odoo18 PLM` | Bootstrap through `C46` exists on `feature/codex-c44c45c46-staging` |
| `file-cad` | `DocDoku` | CAD/file preview, connector, conversion, and viewer contracts are already aligned by design docs and implementation patterns |

## Box Checklist

### Benchmark Target
`Odoo18 PLM`

### Repository Anchors
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_PARALLEL_C17_PLM_BOX_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C20_PLM_BOX_ANALYTICS_EXPORT_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C23_PLM_BOX_OPS_REPORT_TRANSITIONS_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C26_PLM_BOX_RECONCILIATION_AUDIT_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C29_PLM_BOX_CAPACITY_COMPLIANCE_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C32_PLM_BOX_POLICY_EXCEPTIONS_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C35_PLM_BOX_RESERVATIONS_TRACEABILITY_BOOTSTRAP_20260320.md`
- `docs/DESIGN_PARALLEL_C38_PLM_BOX_ALLOCATION_CUSTODY_BOOTSTRAP_20260320.md`
- `docs/DESIGN_PARALLEL_C41_PLM_BOX_OCCUPANCY_TURNOVER_BOOTSTRAP_20260320.md`
- `docs/DESIGN_PARALLEL_C44_PLM_BOX_DWELL_AGING_BOOTSTRAP_20260320.md`

### Delivered Capability Line
- [x] bootstrap CRUD and box state/report foundation
- [x] analytics and export helpers
- [x] ops report and state transitions
- [x] reconciliation and audit views
- [x] capacity and compliance summaries
- [x] policy and exception reporting
- [x] reservations and traceability reads
- [x] allocation and custody views
- [x] occupancy and turnover reporting
- [x] dwell and aging reporting

### Next Benchmark Checks
- [ ] verify box lifecycle semantics remain consistent with the Odoo18-style stock/location workflow expected by this parallel batch
- [ ] verify export/read-model coverage exists for operations, audit, custody, occupancy, and aging scenarios before adding new write paths
- [ ] verify future `box` increments stay read-side/report-side unless a new benchmark decision explicitly authorizes orchestration changes

## Document Sync Checklist

### Benchmark Target
`Odoo18 PLM`

### Repository Anchors
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_PARALLEL_C18_DOCUMENT_SYNC_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C21_DOCUMENT_SYNC_ANALYTICS_EXPORT_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C24_DOCUMENT_SYNC_RECONCILIATION_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C27_DOCUMENT_SYNC_REPLAY_AUDIT_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C30_DOCUMENT_SYNC_DRIFT_SNAPSHOTS_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C33_DOCUMENT_SYNC_BASELINE_LINEAGE_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C36_DOCUMENT_SYNC_CHECKPOINTS_RETENTION_BOOTSTRAP_20260320.md`
- `docs/DESIGN_PARALLEL_C39_DOCUMENT_SYNC_FRESHNESS_WATERMARKS_BOOTSTRAP_20260320.md`
- `docs/DESIGN_PARALLEL_C42_DOCUMENT_SYNC_LAG_BACKLOG_BOOTSTRAP_20260320.md`
- `docs/DESIGN_PARALLEL_C45_DOCUMENT_SYNC_SKEW_GAPS_BOOTSTRAP_20260320.md`

### Delivered Capability Line
- [x] bootstrap CRUD and synchronization base
- [x] analytics and export helpers
- [x] reconciliation helpers
- [x] replay and audit helpers
- [x] drift and snapshot helpers
- [x] baseline and lineage helpers
- [x] checkpoints and retention helpers
- [x] freshness and watermark helpers
- [x] lag and backlog helpers
- [x] skew and gap helpers

### Next Benchmark Checks
- [ ] verify future sync increments continue to express operational visibility and gap detection rather than hidden cross-domain write orchestration
- [ ] verify the current read/export surfaces cover freshness, replay, lineage, retention, and lag before introducing new sync state machines
- [ ] verify skew/gap evidence remains easy to surface in staging regressions and delivery demos

## Cutted Parts Checklist

### Benchmark Target
`Odoo18 PLM`

### Repository Anchors
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_PARALLEL_C19_CUTTED_PARTS_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C22_CUTTED_PARTS_ANALYTICS_EXPORT_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C25_CUTTED_PARTS_COST_UTILIZATION_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C28_CUTTED_PARTS_TEMPLATES_SCENARIOS_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C31_CUTTED_PARTS_BENCHMARK_QUOTE_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C34_CUTTED_PARTS_VARIANCE_RECOMMENDATIONS_BOOTSTRAP_20260319.md`
- `docs/DESIGN_PARALLEL_C37_CUTTED_PARTS_THRESHOLDS_ENVELOPES_BOOTSTRAP_20260320.md`
- `docs/DESIGN_PARALLEL_C40_CUTTED_PARTS_ALERTS_OUTLIERS_BOOTSTRAP_20260320.md`
- `docs/DESIGN_PARALLEL_C43_CUTTED_PARTS_THROUGHPUT_CADENCE_BOOTSTRAP_20260320.md`
- `docs/DESIGN_PARALLEL_C46_CUTTED_PARTS_SATURATION_BOTTLENECKS_BOOTSTRAP_20260320.md`

### Delivered Capability Line
- [x] bootstrap plan/material/cut foundation
- [x] analytics and export helpers
- [x] cost and utilization helpers
- [x] templates and scenarios
- [x] benchmark and quote helpers
- [x] variance and recommendation helpers
- [x] thresholds and envelope checks
- [x] alerts and outlier helpers
- [x] throughput and cadence helpers
- [x] saturation and bottleneck helpers

### Next Benchmark Checks
- [ ] verify future `cutted_parts` increments stay aligned to Odoo18-style manufacturing visibility rather than product-level Aras parity language
- [ ] verify quote/variance/threshold/alert/cadence/saturation surfaces remain exportable before adding new optimization flows
- [ ] verify naming stays unambiguous: `benchmark / quote` here is a domain feature, not a competitor target

## File-CAD Checklist

### Benchmark Target
`DocDoku`

### Repository Anchors
- `docs/DESIGN_DOCDOKU_ALIGNMENT_20260129.md`
- `docs/DESIGN_CAD_CONNECTOR_PLUGIN_SPEC_20260127.md`
- `docs/DESIGN_CAD_3D_CONNECTOR_PIPELINE_20260127.md`
- `src/yuantus/meta_engine/models/file.py`
- `src/yuantus/meta_engine/web/file_router.py`
- `src/yuantus/meta_engine/services/cad_converter_service.py`

### Delivered Capability Line
- [x] DocDoku-style vault path and generated-file storage patterns
- [x] preview and geometry endpoints
- [x] CAD manifest, CAD document, and CAD metadata payloads
- [x] CAD BOM extraction endpoints
- [x] connector list and capabilities exposure
- [x] conversion/import job entrypoints
- [x] connector microservice contract and conversion pipeline design

### Next Benchmark Checks
- [ ] verify connector capability exposure remains aligned with the DocDoku-style contract documented for UI autodiscovery
- [ ] verify file storage, generated artifacts, and geometry outputs keep matching the intended DocDoku-style viewer flow
- [ ] verify any future CAD UX requirement is benchmarked against `DocDoku` first, not the Odoo18 parallel batch baseline

## Cross-Domain Decision Checks

Use this quick gate before starting the next parallel increment:

- [ ] has the domain chosen one primary benchmark target only
- [ ] do the new requirements cite the correct benchmark class (`Aras`, `Odoo18 PLM`, or `DocDoku`)
- [ ] is the work staying inside the current allowed pattern for that benchmark line
- [ ] are the relevant plan/design/verification docs already linked before implementation starts
- [ ] is the increment adding evidence that can be carried into staging verification, not just implementation detail

## Recommended Next Step

If future parallel work continues immediately, create one short child checklist per
domain increment and attach it to the next `Cxx` design doc before code starts.
