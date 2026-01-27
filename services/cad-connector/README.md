# Yuantus CAD Connector Stub (Microservice)

DocDoku-style conversion microservice stub for CAD connectors. It returns
normalized artifacts (geometry + preview + attributes) for integration testing.

## Endpoints

- `GET /health`
- `GET /api/v1/health`
- `GET /capabilities`
- `POST /convert` or `POST /api/v1/convert`
- `GET /jobs/{job_id}` (async mode)
- `GET /artifacts/{id}/mesh.gltf`
- `GET /artifacts/{id}/mesh.bin`
- `GET /artifacts/{id}/preview.png`

## Environment

- `CAD_CONNECTOR_AUTH_MODE` = `disabled`|`optional`|`required` (default: `disabled`)
- `CAD_CONNECTOR_SERVICE_TOKEN` = token used for bearer auth
- `CAD_CONNECTOR_HASH_ALG` = optional hash algorithm (e.g. `sha256`)

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8300
```

## Docker

```bash
docker build -t yuantus-cad-connector .
docker run --rm -p 8300:8300 yuantus-cad-connector
```

## Test request

```bash
curl -X POST http://127.0.0.1:8300/convert \
  -F "file=@/path/to/sample.step" \
  -F "mode=all" \
  -F "format=STEP"
```

## Yuantus integration (future)

Use this stub to validate connector contracts. For production connectors, replace
this service with real NX/Creo/SW/CATIA converters that implement the same API.
