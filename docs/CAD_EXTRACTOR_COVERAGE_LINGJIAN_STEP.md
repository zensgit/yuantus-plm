# CAD Extractor Coverage Report (ling-jian)

## Run Info
- Time: `2025-12-26 00:34:00 +0800`
- Base URL: `http://127.0.0.1:7910`
- Extractor: `http://127.0.0.1:8200`
- Tenant/Org: `tenant-1` / `org-1`
- CAD Format Override: `STEP`
- Directory: `/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian`
- Extensions: `step, stp`
- Files: `1`

## Target Field Coverage

| Field | Present | Coverage |
| --- | --- | --- |
| `part_number` | 1/1 | 100.0% |
| `part_name` | 0/1 | 0.0% |
| `material` | 0/1 | 0.0% |
| `weight` | 0/1 | 0.0% |
| `revision` | 0/1 | 0.0% |
| `drawing_no` | 1/1 | 100.0% |
| `author` | 0/1 | 0.0% |
| `created_at` | 0/1 | 0.0% |

## Extracted Key Distribution (Non-empty)

| Key | Files |
| --- | --- |
| `cad_connector_id` | 1 |
| `cad_format` | 1 |
| `drawing_no` | 1 |
| `file_ext` | 1 |
| `file_name` | 1 |
| `file_size_bytes` | 1 |
| `part_number` | 1 |

## Per-file Summary

| File | Upload Name | File ID | CAD Format | Keys |
| --- | --- | --- | --- | --- |
| `pat4.stp` | `pat4.stp` | `dcc2fbfe-ed64-46f0-a0cb-3c88f0679a81` | `STEP` | cad_connector_id, cad_format, drawing_no, file_ext, file_name, file_size_bytes, part_number |
