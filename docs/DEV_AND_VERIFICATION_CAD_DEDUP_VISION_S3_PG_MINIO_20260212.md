# CAD Dedup Vision: S3 + Postgres + MinIO End-to-End Verification (2026-02-12)

## Goal

- Add an explicit switch to index 2D drawings into Dedup Vision during `POST /api/v1/cad/import`.
- Ensure `cad_dedup_vision` persists the `cad_dedup` payload to S3 and it is readable via `GET /api/v1/file/{id}/cad_dedup` in S3 mode (`302 -> 200` via presigned URL).
- Provide a reproducible, scriptable verification run.

## Changes

- API: `POST /api/v1/cad/import`
  - New form field: `dedup_index: bool = Form(default=False, ...)`
  - Dedup job payload now includes: `"index": bool(dedup_index)`
- Worker task: `cad_dedup_vision`
  - Uses `payload["index"]` to optionally call Dedup Vision indexing (`/api/index/add`) after search.
  - Uses a stable upload filename (`FileContainer.filename` or `{id}.{ext}`) so Dedup Vision results remain readable and deterministic (`results[*].file_name`).
- Integration: `DedupVisionClient`
  - `search_sync(..., upload_filename: Optional[str] = None)`
  - `index_add_sync(..., upload_filename: Optional[str] = None)`
  - Multipart uploads use the provided filename instead of the temp basename.
- Added verification script:
  - `scripts/verify_cad_dedup_vision_s3.sh`
  - Generates two near-identical PNGs (different bytes), uploads baseline with `dedup_index=true`, uploads query with `dedup_index=false`, and asserts the query returns the baseline as a match.
  - Uses `curl -L` to follow S3 presigned redirects when reading back `/file/{id}/cad_dedup`.

## Verification

### Environment

Bring up Postgres + MinIO + API + Dedup Vision:

```bash
docker compose -f docker-compose.yml --profile dedup up -d postgres minio api dedup-vision
```

If you already had a running stack, rebuild API to ensure the latest code is in the container:

```bash
docker compose -f docker-compose.yml --profile dedup up -d --build --no-deps api
```

### Run

```bash
LOG=/tmp/verify_cad_dedup_vision_s3_20260212-174112.log
scripts/verify_cad_dedup_vision_s3.sh | tee "$LOG"
```

Result: PASS (`ALL CHECKS PASSED`)

Key IDs from the verified run:

- Dedup rule: `2057c992-d691-4145-a8dd-47e7745c454c`
- Baseline:
  - File: `a63b0d35-96a5-4c3d-af71-dbb375bf2b46`
  - Job: `4c409eca-865e-4bdc-9b85-3e8bd5e7adbc`
- Query:
  - File: `50897b9d-af95-4b91-a8b5-aa9ec9c641f0`
  - Job: `ab94f266-6e97-457b-b61f-84e830660c64`

Evidence:

- `/tmp/verify_cad_dedup_vision_s3_20260212-174112.log`

### Notes

- Under S3 storage, `GET /api/v1/file/{id}/cad_dedup` may return `302` to a presigned URL. The verification script uses `curl -L` (via `CURL_FOLLOW`) to follow redirects.

