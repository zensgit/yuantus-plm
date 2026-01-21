# Verification: CAD Mesh Stats Fallback (20260121)

## Goal
Ensure `GET /api/v1/cad/files/{file_id}/mesh-stats` returns HTTP 200 with `stats.available=false` when mesh metadata is missing (no 404), so UI can avoid error state.

## Environment
- API: http://127.0.0.1:7910
- Tenancy: db-per-tenant-org
- Schema: create_all

## Steps
1. Rebuild API container with updated mesh-stats fallback.
2. Login as admin and call `/cad/files/{file_id}/mesh-stats` for a CAD file that has no mesh metadata.

## Request
```bash
TOKEN=$(curl -s http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","org_id":"org-1","username":"admin","password":"admin"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))')

curl -s http://127.0.0.1:7910/api/v1/cad/files/630a312a-628f-40b7-b5cc-5f317536aa5e/mesh-stats \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' \
  -H 'x-org-id: org-1'
```

## Result
```json
{
  "file_id": "630a312a-628f-40b7-b5cc-5f317536aa5e",
  "stats": {
    "available": false,
    "reason": "CAD metadata not available"
  }
}
```

## Conclusion
Mesh-stats now returns HTTP 200 with an explicit `available=false` payload when metadata is missing.
