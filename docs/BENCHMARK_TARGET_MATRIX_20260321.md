# Yuantus Benchmark Target Matrix

## Purpose

This document fixes a practical alignment problem in the repository: different
areas of Yuantus do not benchmark against the same external product.

The matrix below defines which benchmark target is authoritative for each work
area, which references are secondary only, and how future parallel development
should choose the right baseline.

## Executive Summary

- Product-level parity target: `Aras Innovator`
- Current `meta_engine` parallel bootstrap baseline: `Odoo18 PLM`
- CAD / file / connector experience target: `DocDoku`
- Industry-reference-only set: `Teamcenter`, `Windchill`, `ENOVIA`, `ERPNext`, `FreeCAD`

## Matrix

| Work Area | Primary Benchmark | Repository Evidence | What It Means |
| --- | --- | --- | --- |
| Product roadmap / capability parity / phase planning | `Aras Innovator` | `docs/DEVELOPMENT_ROADMAP_ARAS_PARITY.md`, `docs/ARAS_PARITY_SCORECARD.md` | When discussing overall PLM capability parity, roadmap completion, and "parity-to-surpass" language, use Aras as the authoritative benchmark. |
| Current greenfield `meta_engine` bootstrap batch (`box`, `document_sync`, `cutted_parts`) | `Odoo18 PLM` | `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`, `docs/DESIGN_ODOO18_PLM_PARALLEL_EXECUTION.md`, `docs/VERIFICATION_ODOO18_PLM_PARALLEL_EXECUTION.md` | For `C17+` parallel increments and their staging verification, the intended scope baseline is Odoo18 PLM-style modular capability expansion. |
| CAD file vault / preview / geometry / conversion / connector contracts | `DocDoku` | `docs/DESIGN_DOCDOKU_ALIGNMENT_20260129.md`, `docs/DESIGN_CAD_CONNECTOR_PLUGIN_SPEC_20260127.md`, `src/yuantus/meta_engine/models/file.py`, `src/yuantus/meta_engine/web/file_router.py` | File storage patterns, conversion microservice contracts, viewer outputs, and connector behavior should align to DocDoku-style expectations first. |
| Enterprise migration vocabulary / long-horizon architecture comparison | `Teamcenter`, `Windchill`, `ENOVIA` | `docs/DEVELOPMENT_PLAN.md` and migration-oriented notes | These are comparison inputs for architecture and migration framing, not the day-to-day delivery target for the current parallel batches. |
| Implementation pattern borrowing only | `ERPNext`, `FreeCAD` | `docs/REFERENCE_NOTES.md`, CAD conversion code comments | These are source-pattern references and should not be treated as primary benchmark products. |

## Usage Rules

### 1. When the question is "What is Yuantus trying to match overall?"
Use `Aras Innovator`.

This applies to:
- roadmap phases
- parity scorecards
- executive status reports
- "already at parity / beyond parity" claims

### 2. When the question is "What is the current `meta_engine` parallel batch building against?"
Use `Odoo18 PLM`.

This applies to:
- `C17` through the current greenfield bootstrap line
- module-scoped analytics / export / report / read-model helpers
- staging batch design and verification discussions

### 3. When the question is "What should CAD / file / connector behavior feel like?"
Use `DocDoku`.

This applies to:
- preview and geometry contracts
- CAD manifest / metadata / BOM extraction
- connector capability exposure
- conversion microservice shape

### 4. Do not mix reference classes in requirement statements
Examples of bad requirement phrasing:
- "Make `cutted_parts` Aras-compatible" when the actual scope is Odoo18-style read-model expansion
- "Make file preview match Odoo" when the repository explicitly aligns file/CAD handling with DocDoku
- "Use Teamcenter as the current sprint baseline" when it is only serving as a broad industry comparison

## Current Mapping For Active Areas

| Active Area | Recommended Benchmark |
| --- | --- |
| `box` analytics / custody / dwell / occupancy extensions | `Odoo18 PLM` |
| `document_sync` reconciliation / lineage / freshness / lag / skew extensions | `Odoo18 PLM` |
| `cutted_parts` cost / alerts / cadence / saturation extensions | `Odoo18 PLM` |
| CAD connector host / conversion pipeline / file viewer outputs | `DocDoku` |
| delivery roadmap and parity reporting | `Aras Innovator` |

## Decision Rule For Future Parallel Work

Before starting a new module or batch, record the benchmark target explicitly:

1. `Aras Innovator` if the work changes product-level parity positioning
2. `Odoo18 PLM` if the work extends the current `meta_engine` parallel capability line
3. `DocDoku` if the work changes CAD/file preview, conversion, or connector contracts

If more than one benchmark appears relevant, choose one primary benchmark and
list the others only as secondary references. Do not leave benchmark scope
implicit.

## Notes

- The repository already contains explicit evidence for all three primary
  benchmark lines; this document only consolidates them.
- The `cutted_parts benchmark / quote` naming in `C31` is a domain feature name,
  not a competitor benchmark signal.
