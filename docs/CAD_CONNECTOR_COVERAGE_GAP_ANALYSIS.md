# CAD Connector Coverage Gap Analysis (DWG Training Set)

This document summarizes the field-level gaps found in the DWG coverage reports and recommends next steps.

## Snapshot

- Source reports:
  - `docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_HAOCHEN.md`
  - `docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_ZHONGWANG.md`
- Dataset: `CAD_CONNECTOR_COVERAGE_DIR` (training DWG directory)
- Files: 110 DWG
- Mode: Offline (filename + key/value extraction)

## Coverage Summary

| Field | Haochen | Zhongwang | Notes |
| --- | --- | --- | --- |
| part_number | 100.0% | 100.0% | Strong; derived from filename patterns |
| part_name | 100.0% | 100.0% | Strong; derived from filename patterns |
| drawing_no | 100.0% | 100.0% | Strong; derived from filename patterns |
| revision | 99.1% | 99.1% | Missing for 1 file |
| material | 0.0% | 0.0% | Not captured offline |
| weight | 0.0% | 0.0% | Not captured offline |
| author | 0.0% | 0.0% | Not captured offline |
| created_at | 0.0% | 0.0% | Not captured offline |

## Primary Gaps

1) material / weight / author / created_at are missing across the dataset.
2) Offline extraction relies on filename and simple key/value text in file bytes, which does not expose title block metadata for binary DWG.

## Root Causes

- Offline mode does not parse DWG title blocks (no ODA/Teigha or equivalent).
- No OCR on preview images; therefore title block text is not recognized.
- Many drawings do not include material/weight in filenames.

## Recommendations (Prioritized)

1) Enable the CAD Extractor service for DWG with title-block parsing.
   - Integrate a DWG-capable parser (e.g., ODA/Teigha or a licensed DWG SDK).
   - Map title-block fields to `material`, `weight`, `author`, `created_at`.

2) Add OCR title-block extraction as a fallback.
   - Run OCR on the preview image in a defined title-block region.
   - Maintain per-template bounding boxes (configurable).

3) Extend filename parsing heuristics (low effort).
   - Detect material tokens: `Q235`, `304`, `316L`, `AL6061`, `45#`.
   - Detect weight tokens: `12.3kg`, `850g`, `1.2t`.

4) Support user override/import.
   - Allow CSV import to fill missing `material` and `weight`.
   - Persist overrides and mark them as user-provided.

5) Normalize materials and units.
   - Map aliases to canonical materials (e.g., `SS304 -> Stainless Steel 304`).
   - Normalize weight to kg.

## Suggested Validation Plan

- Re-run coverage in online mode with extractor enabled.
- Compare field coverage deltas (material/weight should increase materially).
- Track the metrics in `docs/VERIFICATION_RESULTS.md` after each improvement.

## Proposed Targets (Initial)

- material >= 60%
- weight >= 40%
- revision >= 99%
