# Dev & Verification Report - Export Bundles (Impact Summary + Release Readiness) (2026-02-07)

This delivery adds evidence-grade export bundles for two cross-domain PLM diagnostics endpoints:

- Impact summary (BOM where-used + baselines + e-sign summary)
- Release readiness (MBOM/Routing/Baseline diagnostics + e-sign manifest)

Goal: allow users to download a single `zip` that contains both machine-readable JSON and Excel-friendly CSV tables.

## API

### Impact Summary Export

- `GET /api/v1/impact/items/{item_id}/summary/export?export_format=zip|json`

Bundle contents (zip):

- `summary.json`
- `where_used.csv`
- `baselines.csv`
- `esign_signatures.csv`
- `esign_manifest.json`
- `README.txt`

### Release Readiness Export

- `GET /api/v1/release-readiness/items/{item_id}/export?export_format=zip|json`

Bundle contents (zip):

- `readiness.json`
- `resources.csv`
- `errors.csv`
- `warnings.csv`
- `esign_manifest.json`
- `README.txt`

## Implementation

- Impact router export: `src/yuantus/meta_engine/web/impact_router.py`
- Release readiness router export: `src/yuantus/meta_engine/web/release_readiness_router.py`
- Unit tests:
  - `src/yuantus/meta_engine/tests/test_impact_export_bundles.py`
  - `src/yuantus/meta_engine/tests/test_release_readiness_export_bundles.py`
- Non-DB allowlist update: `conftest.py`

## Verification

- Targeted pytest:
  - `./.venv/bin/pytest -q src/yuantus/meta_engine/tests/test_impact_export_bundles.py src/yuantus/meta_engine/tests/test_release_readiness_export_bundles.py`
- Strict gate (pytest non-DB + pytest DB + Playwright):
  - Evidence: `docs/DAILY_REPORTS/STRICT_GATE_20260207-205929.md` (PASS)

