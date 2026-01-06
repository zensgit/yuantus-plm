# CADGF Preview Stage 2 - Online E2E Validation (2026-01-05)

## Scope
- Validate CADGF preview E2E (DXF) with router + worker running.
- Validate DWG pre-processing with converter configured.

## Environment
- BASE_URL: http://127.0.0.1:7910
- TENANT/ORG: tenant-1 / org-1
- Auth: admin/admin
- CADGF root: /Users/huazhou/Downloads/Github/CADGameFusion
- CADGF DXF plugin: /Users/huazhou/Downloads/Github/CADGameFusion/build_vcpkg/plugins/libcadgf_dxf_importer_plugin.dylib
- DWG converter: /Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter
- Router: http://127.0.0.1:9000 (healthy)
- Worker: `yuantus worker --tenant tenant-1 --org org-1 --poll-interval 1`

## Run A (DXF)
- Sample: /Users/huazhou/Downloads/Github/dedupcad/tests/fixtures/mixed.dxf
- login_ok: yes
- upload_ok: yes
- conversion_ok: yes
- viewer_load: yes
- manifest_rewrite: yes

## Run B (DWG, converter configured)
- Sample: local DWG (path omitted; 3 samples tried)
- conversion_status: failed
- conversion_error: CADGF conversion failed (1): glTF export failed: no mesh data

## Run C (DWG, additional sample)
- Sample: /Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/蜗杆与箱体/改箱体右盖123.dwg
- conversion_status: failed
- conversion_error: CADGF conversion failed (1): glTF export failed: no mesh data

## Run D (DWG, line glTF fallback)
- Sample: /Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/蜗杆与箱体/改箱体右盖123.dwg
- login_ok: yes
- upload_ok: yes
- conversion_ok: yes
- viewer_load: yes
- manifest_rewrite: yes
- artifacts: mesh_gltf + mesh_bin + document_json (default emit excludes mesh_metadata)

## Run E (DWG, closed profile sample)
- Sample: /Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/蜗杆与箱体/2004阶梯轴71.dwg
- login_ok: yes
- upload_ok: yes
- conversion_ok: yes
- viewer_load: yes
- manifest_rewrite: yes
- artifacts: mesh_gltf + mesh_bin + document_json (default emit excludes mesh_metadata)

## Run F (DXF, emit meta)
- Sample: /Users/huazhou/Downloads/Github/dedupcad/tests/fixtures/mixed.dxf
- Method: plm_convert.py --emit json,gltf,meta (manual conversion)
- mesh_metadata.json: present

## Run G (DXF, online preview with metadata)
- Sample: /tmp/mixed_meta_test.dxf (mixed.dxf with comment injected to avoid dedupe)
- login_ok: yes
- upload_ok: yes
- conversion_ok: yes
- viewer_load: yes
- manifest_rewrite: yes
- manifest includes: mesh_metadata

## Run H (DWG, online preview with metadata)
- Sample: /Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/1200型风送式喷雾机/1200型风送式喷雾机.dwg
- login_ok: yes
- upload_ok: yes
- conversion_ok: yes
- viewer_load: yes
- manifest_rewrite: yes
- manifest includes: mesh_metadata
- cad_metadata_path: cadgf/84/848008e3-ff97-41a8-9d26-8a6f83694cdd/mesh_metadata.json

## Run I (DWG, online preview with metadata)
- Sample: /Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/40张机械零件CAD图纸/11001床身装配图.dwg
- login_ok: yes
- upload_ok: yes
- conversion_ok: yes
- viewer_load: yes
- manifest_rewrite: yes
- manifest includes: mesh_metadata
- cad_metadata_path: cadgf/52/525f05ac-be17-46ab-a8e9-b118d29d7dc9/mesh_metadata.json

## Result
- Status: PASS (DXF + DWG line fallback + DWG metadata in online flow)

## DWG Candidate Scan
- Report: /Users/huazhou/Downloads/Github/Yuantus/docs/dwg_triangle_candidates_20260105.md
- Summary: 100 DWG files triangulate (mesh_metadata present); 21 conversions timed out.

## Run J (DXF, online preview with EXPECT_METADATA=1)
- Sample: /tmp/mixed_meta_test.dxf
- EXPECT_METADATA: 1
- metadata_present: yes

## Run K (DWG, online preview with EXPECT_METADATA=1)
- Sample: /Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/1200型风送式喷雾机/1200型风送式喷雾机.dwg
- EXPECT_METADATA: 1
- metadata_present: yes

## Follow-ups
- DWG metadata path validated for two candidate files; continue expanding coverage as needed.
