# CAD Extractor Coverage Report (ling-jian)

## Run Info
- Time: `2025-12-26 00:33:59 +0800`
- Base URL: `http://127.0.0.1:7910`
- Extractor: `http://127.0.0.1:8200`
- Tenant/Org: `tenant-1` / `org-1`
- CAD Format Override: `CATIA`
- Directory: `/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian`
- Extensions: `catpart, catproduct`
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
| `Part1.CATPart` | `Part1.CATPart` | `df6d6c62-bd2d-4b02-b3aa-3681b556f2c0` | `CATIA` | cad_connector_id, cad_format, drawing_no, file_ext, file_name, file_size_bytes, part_number |
| `Part2.CATPart` | `Part2.CATPart` | `49491e9f-4288-4709-b915-02dab42266f4` | `CATIA` | cad_connector_id, cad_format, drawing_no, file_ext, file_name, file_size_bytes, part_number |
| `Part3.CATPart` | `Part3.CATPart` | `b91d7981-243a-46d9-9fa0-368d77f5dc31` | `CATIA` | cad_connector_id, cad_format, drawing_no, file_ext, file_name, file_size_bytes, part_number |
| `Part4.CATPart` | `Part4.CATPart` | `361ebe75-2b76-4d0f-adac-c6039b4165d6` | `CATIA` | cad_connector_id, cad_format, drawing_no, file_ext, file_name, file_size_bytes, part_number |
| `Part5.CATPart` | `Part5.CATPart` | `84551a34-9740-459c-9468-8973ce4cae75` | `CATIA` | cad_connector_id, cad_format, drawing_no, file_ext, file_name, file_size_bytes, part_number |
| `Part6.CATPart` | `Part6.CATPart` | `96141ca1-6b73-4a11-849d-112ba9094584` | `CATIA` | cad_connector_id, cad_format, drawing_no, file_ext, file_name, file_size_bytes, part_number |
