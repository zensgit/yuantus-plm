# Plugin Async Job Verification Report

- Date: 2026-01-10 17:20:41 
- Base URL: http://127.0.0.1:7915
- Tenant/Org: tenant-1 / org-1
- Worker runs: 1

## Plugin Discovery

- Status: 200
- Plugins: yuantus-demo, yuantus-pack-and-go, yuantus-bom-compare

## Pack-and-Go (async)

- Create status: 200
- Job id: 7b828417-be41-4282-8c03-3a48c2e3a351
- Status URL: http://127.0.0.1:7915/api/v1/plugins/pack-and-go/jobs/7b828417-be41-4282-8c03-3a48c2e3a351
- Initial status: {"id": "7b828417-be41-4282-8c03-3a48c2e3a351", "status": "pending", "task_type": "pack_and_go", "created_at": "2026-01-10T09:20:41.233751", "completed_at": null, "result": {}, "download_url": null}
- Final status: {"id": "7b828417-be41-4282-8c03-3a48c2e3a351", "status": "completed", "task_type": "pack_and_go", "created_at": "2026-01-10T09:20:41.233751", "completed_at": "2026-01-10T09:20:42.990226", "result": {"zip_name": "pack_and_go_HC-1767490220_20260110092042.zip", "file_count": 1, "total_bytes": 84}, "download_url": "http://127.0.0.1:7915/api/v1/plugins/pack-and-go/jobs/7b828417-be41-4282-8c03-3a48c2e3a351/download"}

## Download

- Download URL: http://127.0.0.1:7915/api/v1/plugins/pack-and-go/jobs/7b828417-be41-4282-8c03-3a48c2e3a351/download
- Download status: 200

## Manifest Summary

- Zip size: 734 bytes
- Manifest: {"root_item_id": "4a826410-120b-40b3-8e8a-b246f56fdb05", "file_count": 1, "total_bytes": 84, "missing_files": 0}