# Plugin E2E Verification Report

- Date: 2026-01-10 17:05:10 
- Base URL: http://127.0.0.1:7910
- Tenant/Org: tenant-1 / org-1

## Plugin Discovery

- Status: 200
- Plugins: yuantus-demo, yuantus-pack-and-go, yuantus-bom-compare

## BOM Compare (summarized)

- Status: 200
- Summary: {"added": 1, "removed": 1, "modified": 0, "unchanged": 0}
- Differences: 2

## BOM Apply (no-op)

- Status: 200
- ok: True | results: 0

## Pack-and-Go (sync)

- Status: 200
- Zip size: 733 bytes
- Manifest: {"root_item_id": "4a826410-120b-40b3-8e8a-b246f56fdb05", "file_count": 1, "total_bytes": 84, "missing_files": 0}