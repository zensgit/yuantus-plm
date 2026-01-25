# CADGF Preview Online Design (2026-01-25)

## Goal
Enable CAD preview (DWG/DXF) with CADGF router + CADGF conversion pipeline in a multi-tenant setup.

## Architecture Notes
- API runs in Docker (Postgres + MinIO).
- CADGF router runs on host (macOS) because CADGF binaries are host-specific.
- For CADGF conversion jobs, use a host worker (macOS) so it can execute CADGF CLI and DWG->DXF conversion.
- API builds cad_viewer_url from `CADGF_ROUTER_PUBLIC_BASE_URL` so the UI can open the CADGF web viewer.

## Data Flow
1. Client uploads DWG/DXF to API (S3/MinIO storage).
2. API enqueues `cad_geometry` job in `meta_conversion_jobs`.
3. Host worker pulls job, downloads from S3, converts DWG->DXF (ODA), runs CADGF conversion, uploads artifacts.
4. API returns `cad_viewer_url` pointing to CADGF router + manifest rewrite.

## Required Environment (Host Worker)
- DB and tenancy
  - `YUANTUS_TENANCY_MODE=db-per-tenant-org`
  - `YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
  - `YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}`
  - `YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`
- S3/MinIO
  - `YUANTUS_STORAGE_TYPE=s3`
  - `YUANTUS_S3_ENDPOINT_URL=http://127.0.0.1:59000`
  - `YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://127.0.0.1:59000`
  - `YUANTUS_S3_BUCKET_NAME=yuantus`
  - `YUANTUS_S3_ACCESS_KEY_ID=minioadmin`
  - `YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin`
- CADGF
  - `YUANTUS_CADGF_ROOT=/Users/huazhou/Downloads/Github/CADGameFusion`
  - `YUANTUS_CADGF_CONVERT_CLI=/Users/huazhou/Downloads/Github/CADGameFusion/build_vcpkg/tools/convert_cli`
  - `YUANTUS_CADGF_DXF_PLUGIN_PATH=/Users/huazhou/Downloads/Github/CADGameFusion/build_vcpkg/plugins/libcadgf_dxf_importer_plugin.dylib`
  - `YUANTUS_DWG_CONVERTER_BIN=/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter`

## API Container Settings
- `YUANTUS_CADGF_ROUTER_BASE_URL=http://host.docker.internal:9000`
- `YUANTUS_CADGF_ROUTER_PUBLIC_BASE_URL=http://localhost:9000`

## Operational Steps
1. Stop container worker to avoid picking jobs without CADGF binaries:
   - `docker compose stop worker`
2. Start CADGF router (host):
   - `python3 -u /Users/huazhou/Downloads/Github/CADGameFusion/tools/plm_router_service.py --host 127.0.0.1 --port 9000 ...`
3. Start host worker:
   - `.venv/bin/yuantus worker --poll-interval 2 --tenant tenant-1 --org org-1`
4. Run verification script with DWG or DXF:
   - `BASE_URL=http://127.0.0.1:7910 SAMPLE_FILE=/path/to/file.dwg scripts/verify_cad_preview_online.sh`
5. Stop host worker/router and restart container worker.

## Constraints
- Container worker cannot execute macOS CADGF binaries; use host worker for CADGF conversions.
- DWG requires ODAFileConverter via `YUANTUS_DWG_CONVERTER_BIN`.
