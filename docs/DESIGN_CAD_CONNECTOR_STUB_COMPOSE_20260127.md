# CAD Connector Stub (Compose Integration)

## Goal
Enable one-command startup of the DocDoku-style CAD connector stub alongside the PLM stack.

## Compose File
- `docker-compose.cad-connector.yml`

## Service
- `cad-connector`
- Port: `8300`
- Health: `GET /health`

## Usage
```bash
# Start connector only
 docker compose -f docker-compose.cad-connector.yml up -d --build

# Verify
 curl http://127.0.0.1:8300/health
```

## Full Regression
`script/run_full_regression.sh` now checks connector health via `CAD_CONNECTOR_BASE_URL`.
