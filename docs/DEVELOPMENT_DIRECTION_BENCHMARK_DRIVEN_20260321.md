# Yuantus Benchmark-Driven Development Direction

## Purpose

This document turns the benchmark matrix into an execution direction.

The repository is already clear that `Aras Innovator`, `Odoo18 PLM`, and
`DocDoku` are not interchangeable targets. The practical problem is choosing
what each one should drive after `C44/C45/C46` stabilizes on `main`.

## Current State

- as of `2026-03-21`, `C44/C45/C46` has completed merge-prep, merged onto
  `main`, and passed the stabilization window
- `box`, `document_sync`, and `cutted_parts` have reached a stable Odoo18-style
  read-side/report/export line through `C46`
- benchmark ownership is now explicit:
  - `Aras Innovator` for product-level parity and acceptance language
  - `Odoo18 PLM` for the current `meta_engine` parallel increment line
  - `DocDoku` for `file-cad` contract and experience alignment

## Development Direction

### 1. Keep `Aras Innovator` as the product-level north star

Use `Aras` to answer product questions:

- are we covering the mechanical-industry closed loop
- are we moving the roadmap and scorecard forward
- can we demonstrate parity and differentiated evidence

Do not use `Aras` to justify random sprint scope expansion. The repository
already warns that "surpass Aras" language can cause requirement sprawl, and it
already narrows milestone acceptance back to the mechanical core loop:
`Part/BOM/Rev/ECO/Doc/CAD`.

This means the next Aras-facing work should be:

- stronger proof on the existing scorecard
- closed-loop demo evidence
- strict-gate, performance, and verification evidence

It should not be:

- new cross-domain hot-path rewrites
- broad competitor-driven feature shopping

Repository anchors:

- `docs/DEVELOPMENT_ROADMAP_ARAS_PARITY.md`
- `docs/ARAS_PARITY_SCORECARD.md`
- `docs/DEVELOPMENT_PLAN.md`

### 2. Keep `Odoo18 PLM` as the execution baseline for `meta_engine`

The active `meta_engine` batch has behaved well because it stayed inside one
pattern: isolated domain increments, mostly read-side/report/export/state
helpers, and no reopening of shared hot files.

That pattern should continue for `box`, `document_sync`, and `cutted_parts`.
The benchmark is not "copy Odoo"; the benchmark is "use Odoo18 PLM to choose
the next operations/manufacturing visibility gaps worth expressing inside
Yuantus".

Immediate rule:

- do not reopen multi-domain `Cxx` batching immediately after `C46`
- pick one bounded Odoo18-style increment first, then prove it with the same
  merge-prep and stabilization discipline

After that, the next Odoo-driven lane should prioritize one of two shapes only:

1. another isolated domain increment in `box`, `document_sync`, or
   `cutted_parts`, if it adds operational visibility, reporting, export, or
   state evidence
2. one isolated governance/control increment derived from the Odoo reference
   tracks, such as:
   - checkout gate strictness modes
   - breakage grouped counters
   - BOM compare mode switch

Those three items already appear as `P0` in the Odoo reference track notes and
fit the repo's preference for bounded, reviewable increments.

Repository anchors:

- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/DESIGN_PARALLEL_P3_ODOO18_REFERENCE_PARALLEL_TRACKS_20260306.md`
- `docs/BENCHMARK_CHILD_CHECKLIST_TEMPLATE_20260321.md`

### 3. Run `DocDoku` as a separate `file-cad` convergence lane

`DocDoku` should not drive core PLM business modeling. It should drive the
`file-cad` boundary: preview, geometry, metadata, BOM extraction, converter
selection, and connector capability discovery.

The most concrete near-term gap is already documented:

- design expects a consolidated `GET /api/v1/cad/capabilities` contract
- current code still exposes `GET /api/v1/file/supported-formats`

That mismatch is exactly the kind of contract convergence work that belongs on
the DocDoku lane. The optional `cad_bom` schema validation gap belongs on the
same lane.

This lane should keep the repository's existing boundary:

- core remains the source of truth for Item/BOM/Version/ECO/File relationships
- CAD conversion, geometry, preview, ML, and similar systems stay as derived
  data producers around the core

Repository anchors:

- `docs/DESIGN_DOCDOKU_ALIGNMENT_20260129.md`
- `docs/DESIGN_CAD_CONNECTOR_PLUGIN_SPEC_20260127.md`
- `docs/DEVELOPMENT_PLAN.md`
- `src/yuantus/meta_engine/web/file_router.py`

### 4. Use one primary benchmark per increment

Future increments should choose one benchmark only:

- `Aras` if the work changes product parity position or scorecard language
- `Odoo18 PLM` if the work extends the current `meta_engine` operating line
- `DocDoku` if the work changes CAD/file preview, conversion, or connector
  contracts

If more than one benchmark seems relevant, pick one primary benchmark and list
the others as secondary references only. Do not leave the benchmark implicit.

## Recommended Parallel Lanes

### Lane A: `file-cad` contract convergence

- canonicalize `GET /api/v1/cad/capabilities` as the autodiscovery contract
- add direct Python contract tests for the consolidated capabilities payload
- mark `GET /api/v1/file/supported-formats` as legacy/deprecated

### Lane B: Next Odoo-driven increment

- start as a single bounded increment, not another wide batch
- use the benchmark child checklist first
- default candidate order:
  - `checkout gate strictness modes`
  - `breakage grouped counters`
  - `BOM compare mode switch`

### Lane C: Aras-facing product proof

- refresh scorecard evidence after merges
- strengthen closed-loop demos and verification artifacts
- keep acceptance tied to the mechanical core loop

### Lane D: delivery and ops hardening

- keep upgrade/rollback/runbook artifacts current
- keep benchmark child checklist mandatory before new bounded increments
- preserve strict-gate, performance, and delivery evidence as first-class output

## Non-Directions

Do not do these:

- do not mix `Aras`, `Odoo18 PLM`, and `DocDoku` into a single requirement line
- do not reopen `src/yuantus/api/app.py` or other hot shared files for routine
  benchmark-driven increments
- do not pull CAD conversion concerns into core truth-source modeling
- do not directly reuse upstream reference code; keep only the design ideas and
  self-implemented contracts

## Conclusion

The practical development direction is:

- keep the next `meta_engine` wave on the Odoo18-style single-increment path
- run `file-cad` as a separate DocDoku contract-convergence track
- treat “surpass Aras” as an evidence problem, not a feature-sprawl problem
- measure overall product progress against Aras, not against day-to-day feature
  noise

## See Also

- `docs/DEVELOPMENT_STRATEGY_PARITY_TO_SURPASS_20260321.md`
- `docs/DELIVERY_PLAN_PARITY_TO_SURPASS_20260321.md`
