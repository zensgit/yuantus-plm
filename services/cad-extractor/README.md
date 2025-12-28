# Yuantus CAD Extractor (Microservice)

Lightweight CAD attribute extractor service for YuantusPLM.

## Endpoints

- `GET /health`
- `GET /api/v1/health`
- `POST /api/v1/extract`
  - multipart form:
    - `file` (required)
    - `cad_format` (optional)
    - `cad_connector_id` (optional)
  - response:
    - `{ "ok": true, "attributes": { ... }, "warnings": [] }`

Notes:
- Filename heuristic extracts `part_number`, `description`, and `revision` when possible.
  - Example: `J2824002-06-Head-Assembly-v2.dwg` -> `part_number=J2824002-06`, `description=Head-Assembly`, `revision=v2`.

## Environment

- `CAD_EXTRACTOR_AUTH_MODE` = `disabled`|`optional`|`required` (default: `disabled`)
- `CAD_EXTRACTOR_SERVICE_TOKEN` = token used for bearer auth
- `CAD_EXTRACTOR_MAX_UPLOAD_MB` = max upload size in MB (default: `200`)
- `CAD_EXTRACTOR_HASH_ALG` = optional hash algorithm (e.g. `sha256`)

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8200
```

## Docker

```bash
docker build -t yuantus-cad-extractor .
docker run --rm -p 8200:8200 yuantus-cad-extractor
```

## Test request

```bash
curl -X POST http://127.0.0.1:8200/api/v1/extract \
  -F "file=@/path/to/sample.dwg" \
  -F "cad_format=DWG"
```

## Yuantus integration

Set these in Yuantus:

```bash
export YUANTUS_CAD_EXTRACTOR_BASE_URL="http://localhost:8200"
export YUANTUS_CAD_EXTRACTOR_MODE="required"
# Optional auth
export YUANTUS_CAD_EXTRACTOR_SERVICE_TOKEN="your-token"
```

In docker compose (API/Worker in containers), use:

```bash
export YUANTUS_CAD_EXTRACTOR_BASE_URL="http://cad-extractor:8200"
```
