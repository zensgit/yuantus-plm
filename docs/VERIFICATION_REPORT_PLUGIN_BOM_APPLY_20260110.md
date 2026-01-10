# Plugin BOM Apply Verification Report

- Date: 2026-01-10 17:35:51 
- Base URL: http://127.0.0.1:7915
- Tenant/Org: tenant-1 / org-1

## Target Relationship

- Relationship ID: 382e37b3-baa4-48be-8534-c7c147556f6e
- Parent ID: 2e00c102-56a7-4b91-a017-4e605c4904ea
- Child ID: 3c821227-e10e-4c54-9aa3-fe145f18d02b
- Original Quantity: 1.0

## Apply Update

- Status: 200
- Response: {"ok": true, "results": [{"op": "update", "result": {"id": "382e37b3-baa4-48be-8534-c7c147556f6e", "type": "Part BOM", "status": "updated"}}]}
- Quantity after apply (DB): 2.0

## Revert Update

- Status: 200
- Response: {"ok": true, "results": [{"op": "update", "result": {"id": "382e37b3-baa4-48be-8534-c7c147556f6e", "type": "Part BOM", "status": "updated"}}]}
- Quantity after revert (DB): 1.0

## Notes

- Applied and reverted via plugin apply endpoint; audit logs may have been recorded.