# CAD Real Samples Verification (Design)

## Goal
Validate the end-to-end CAD pipeline against **real** DWG/STEP/PRT samples, including:
- CAD import with `auto_create_part`
- Attribute extraction (`cad_extract`)
- 2D/3D preview generation (`cad_preview`)
- Part metadata mapping (item_number / name / revision)

## Covered Formats
- DWG (2D drawing)
- STEP (3D neutral)
- PRT (NX/Creo style part)

## Inputs
Default sample paths (overridable by env):
- `CAD_SAMPLE_DWG`
- `CAD_SAMPLE_STEP`
- `CAD_SAMPLE_PRT`

## Storage Mode
The verification must align with server storage:
- Local storage: default
- S3/MinIO: set
  - `YUANTUS_STORAGE_TYPE=s3`
  - `YUANTUS_S3_ENDPOINT_URL=http://localhost:59000`
  - `YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000`
  - `YUANTUS_S3_BUCKET_NAME=yuantus`
  - `YUANTUS_S3_ACCESS_KEY_ID=minioadmin`
  - `YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin`

## Flow (per sample)
1. Upload via `/api/v1/cad/import` with `auto_create_part=true`.
2. Run `cad_extract` to derive attributes.
3. Run `cad_preview` to generate preview artifacts.
4. Verify preview endpoint returns 302/200.
5. Validate extracted attributes and auto-created Part fields.

## Verification Script
- `scripts/verify_cad_real_samples.sh`

## Output
- Verification report: `docs/VERIFICATION_CAD_REAL_SAMPLES_20260127.md`

