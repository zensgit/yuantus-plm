# CADGF Preview Sample Matrix

Date: 2026-01-09

## Sources
- `docs/verification-cadgf-preview-stage2-20260105.md`
- `docs/dwg_triangle_candidates_20260105.md`

## Summary
- DWG scanned: 387
- Triangle candidates: 100
- Failures: 21 (convert_cli errors + timeouts)
- Timeouts: ODA 45s, convert_cli 30s

## Coverage (High-level)
- DXF: validated online preview and metadata generation.
- DWG: validated ODA -> DXF -> CADGF conversion with metadata for multiple
  samples (see Stage 2 report).

## Failure Classes (from DWG scan)
- Unsupported DXF entities (import_to_document failed)
- glTF export produced no geometry
- Conversion timeouts

## Notes
- Full candidate and failure lists are maintained in
  `docs/dwg_triangle_candidates_20260105.md`.
- Online validation samples and metadata paths are recorded in
  `docs/verification-cadgf-preview-stage2-20260105.md`.
