# CAD Extractor Coverage Report (ug)

## Run Info
- Time: `2025-12-26 00:33:54 +0800`
- Base URL: `http://127.0.0.1:7910`
- Extractor: `http://127.0.0.1:8200`
- Tenant/Org: `tenant-1` / `org-1`
- CAD Format Override: `NX`
- Directory: `/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/比较杂的收藏/ug`
- Files: `4`

## Target Field Coverage

| Field | Present | Coverage |
| --- | --- | --- |
| `part_number` | 4/4 | 100.0% |
| `part_name` | 1/4 | 25.0% |
| `material` | 0/4 | 0.0% |
| `weight` | 0/4 | 0.0% |
| `revision` | 0/4 | 0.0% |
| `drawing_no` | 3/4 | 75.0% |
| `author` | 0/4 | 0.0% |
| `created_at` | 0/4 | 0.0% |

## Extracted Key Distribution (Non-empty)

| Key | Files |
| --- | --- |
| `cad_connector_id` | 4 |
| `cad_format` | 4 |
| `file_ext` | 4 |
| `file_name` | 4 |
| `file_size_bytes` | 4 |
| `part_number` | 4 |
| `drawing_no` | 3 |
| `part_name` | 1 |

## Per-file Summary

| File | Upload Name | File ID | CAD Format | Keys |
| --- | --- | --- | --- | --- |
| `jian1.prt` | `jian1.prt` | `a3c9432c-d10e-4fda-a81f-675d6a9fd0e1` | `NX` | cad_connector_id, cad_format, drawing_no, file_ext, file_name, file_size_bytes, part_number |
| `jian2.prt` | `jian2.prt` | `996d865f-3282-434e-b9a4-05cb57187791` | `NX` | cad_connector_id, cad_format, drawing_no, file_ext, file_name, file_size_bytes, part_number |
| `jian3.prt` | `jian3.prt` | `d30f41b8-1430-4021-9c73-d3312bf3ae92` | `NX` | cad_connector_id, cad_format, drawing_no, file_ext, file_name, file_size_bytes, part_number |
| `peihejian.prt` | `peihejian.prt` | `1dfbd48e-0496-452f-b38f-60b3c762886e` | `NX` | cad_connector_id, cad_format, file_ext, file_name, file_size_bytes, part_name, part_number |
