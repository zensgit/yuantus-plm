# CAD Extractor Coverage Report (ling-jian)

## Run Info
- Time: `2025-12-26 00:34:05 +0800`
- Base URL: `http://127.0.0.1:7910`
- Extractor: `http://127.0.0.1:8200`
- Tenant/Org: `tenant-1` / `org-1`
- CAD Format Override: `NX`
- Directory: `/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian`
- Extensions: `prt, asm`
- Files: `6`

## Target Field Coverage

| Field | Present | Coverage |
| --- | --- | --- |
| `part_number` | 6/6 | 100.0% |
| `part_name` | 0/6 | 0.0% |
| `material` | 0/6 | 0.0% |
| `weight` | 0/6 | 0.0% |
| `revision` | 0/6 | 0.0% |
| `drawing_no` | 6/6 | 100.0% |
| `author` | 0/6 | 0.0% |
| `created_at` | 0/6 | 0.0% |

## Extracted Key Distribution (Non-empty)

| Key | Files |
| --- | --- |
| `cad_connector_id` | 6 |
| `cad_format` | 6 |
| `drawing_no` | 6 |
| `file_ext` | 6 |
| `file_name` | 6 |
| `file_size_bytes` | 6 |
| `part_number` | 6 |

## Per-file Summary

| File | Upload Name | File ID | CAD Format | Keys |
| --- | --- | --- | --- | --- |
| `Part1_catpart.prt` | `Part1_catpart.prt` | `6ba291bb-5b0b-4a6d-92fe-3a7fd9e4b386` | `NX` | cad_connector_id, cad_format, drawing_no, file_ext, file_name, file_size_bytes, part_number |
| `Part2_catpart.prt` | `Part2_catpart.prt` | `07a4f713-e776-4ea9-b1f9-22b8074d69e1` | `NX` | cad_connector_id, cad_format, drawing_no, file_ext, file_name, file_size_bytes, part_number |
| `Part3_catpart.prt` | `Part3_catpart.prt` | `83af911a-3cb7-402d-a6c7-eae129f97474` | `NX` | cad_connector_id, cad_format, drawing_no, file_ext, file_name, file_size_bytes, part_number |
| `Part4_catpart.prt` | `Part4_catpart.prt` | `50cf8d64-5e15-4996-9ca4-29adc52e2d52` | `NX` | cad_connector_id, cad_format, drawing_no, file_ext, file_name, file_size_bytes, part_number |
| `Part5_catpart.prt` | `Part5_catpart.prt` | `018d3943-5e39-4c6f-a259-8c715fd95901` | `NX` | cad_connector_id, cad_format, drawing_no, file_ext, file_name, file_size_bytes, part_number |
| `Part6_catpart.prt` | `Part6_catpart.prt` | `ff6cbd9b-2541-477d-be6e-8afc8540f120` | `NX` | cad_connector_id, cad_format, drawing_no, file_ext, file_name, file_size_bytes, part_number |
