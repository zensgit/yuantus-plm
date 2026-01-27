# CAD 2D Real Connectors (Design)

## Goal
Validate real DWG connector overrides for Haochen/Zhongwang by uploading actual DWG files and verifying:
- Connector metadata
- Extracted attributes (part_number from filename)

## Inputs
- `CAD_SAMPLE_HAOCHEN_DWG`
- `CAD_SAMPLE_ZHONGWANG_DWG`

## Flow
1. Upload DWG with explicit connector override.
2. Run `cad_extract` job via worker (or direct fallback).
3. Validate metadata + extracted attributes.

## Storage
Use the same storage settings as the server (local or S3/MinIO).

## Verification
- Script: `scripts/verify_cad_connectors_real_2d.sh`
- Report: `docs/VERIFICATION_CAD_CONNECTORS_REAL_2D_20260127.md`
