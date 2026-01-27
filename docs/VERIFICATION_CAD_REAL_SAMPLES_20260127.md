==============================================
CAD Real Samples Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
DWG: /Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg
STEP: /Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/CNC.stp
PRT: /Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/model2.prt
CAD_EXTRACTOR_BASE_URL: http://localhost:8200
==============================================
OK: Seeded identity/meta
OK: Admin login

==> [DWG] Import + auto_create_part
OK: DWG imported (file_id=630a312a-628f-40b7-b5cc-5f317536aa5e, item_id=b9e86fee-4237-4b3a-a707-659008e44ead)
==> [DWG] Run cad_extract
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
OK: DWG cad_extract OK
==> [DWG] Run cad_preview
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
OK: DWG cad_preview OK
==> [DWG] Verify preview endpoint
OK: DWG preview endpoint HTTP 302
==> [DWG] Verify extracted attributes
OK: DWG attributes OK
==> [DWG] Verify auto-created Part
OK: DWG Part properties OK (item_number=J2824002-06)

==> [STEP] Import + auto_create_part
OK: STEP imported (file_id=fe94aaec-ddab-4bfd-af5f-5f991056bad1, item_id=e2319abc-d882-48ff-a84b-41d3da8afd79)
==> [STEP] Run cad_extract
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
OK: STEP cad_extract OK
==> [STEP] Run cad_preview
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
OK: STEP cad_preview OK
==> [STEP] Verify preview endpoint
OK: STEP preview endpoint HTTP 302
==> [STEP] Verify extracted attributes
OK: STEP attributes OK
==> [STEP] Verify auto-created Part
OK: STEP Part properties OK (item_number=CNC)

==> [PRT] Import + auto_create_part
OK: PRT imported (file_id=7298f196-062d-48df-be75-266b4375b44a, item_id=c1339c14-ba15-4e68-b9b6-d4705c9394a1)
==> [PRT] Run cad_extract
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
OK: PRT cad_extract OK
==> [PRT] Run cad_preview
cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh.
OK: PRT cad_preview OK
==> [PRT] Verify preview endpoint
OK: PRT preview endpoint HTTP 302
==> [PRT] Verify extracted attributes
OK: PRT attributes OK
==> [PRT] Verify auto-created Part
OK: PRT Part properties OK (item_number=model2)

==============================================
CAD Real Samples Verification Complete
==============================================
ALL CHECKS PASSED
