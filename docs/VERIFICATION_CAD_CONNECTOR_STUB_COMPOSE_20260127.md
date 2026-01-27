# CAD Connector Stub Compose Verification

## Steps
1. `docker compose -f docker-compose.cad-connector.yml up -d --build`
2. `curl http://127.0.0.1:8300/health`

## Expected
- `{"ok": true, "service": "cad-connector"}`
