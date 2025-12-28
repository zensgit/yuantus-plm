# Day 40 - Coverage Refresh (CAD Extractor)

## Scope
- Refresh extractor coverage reports with filename fallback improvements.

## Verification - Coverage Reports

Command:

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200'
export CLI='.venv/bin/yuantus'

PY=.venv/bin/python
$PY scripts/collect_cad_extractor_coverage.py --base-url http://127.0.0.1:7910 --tenant tenant-1 --org org-1 --cad-format AUTOCAD --dir "/Users/huazhou/Downloads/训练图纸/训练图纸" --extensions dwg --output docs/CAD_EXTRACTOR_COVERAGE_TRAINING_DWG.md
$PY scripts/collect_cad_extractor_coverage.py --base-url http://127.0.0.1:7910 --tenant tenant-1 --org org-1 --cad-format NX --dir "/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/比较杂的收藏/ug" --output docs/CAD_EXTRACTOR_COVERAGE_UG.md
$PY scripts/collect_cad_extractor_coverage.py --base-url http://127.0.0.1:7910 --tenant tenant-1 --org org-1 --cad-format CREO --dir "/Users/huazhou/Downloads/JCB1" --output docs/CAD_EXTRACTOR_COVERAGE_JCB1.md
$PY scripts/collect_cad_extractor_coverage.py --base-url http://127.0.0.1:7910 --tenant tenant-1 --org org-1 --cad-format CATIA --dir "/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian" --extensions catpart,catproduct --output docs/CAD_EXTRACTOR_COVERAGE_LINGJIAN_CATIA.md
$PY scripts/collect_cad_extractor_coverage.py --base-url http://127.0.0.1:7910 --tenant tenant-1 --org org-1 --cad-format STEP --dir "/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian" --extensions step,stp --output docs/CAD_EXTRACTOR_COVERAGE_LINGJIAN_STEP.md
$PY scripts/collect_cad_extractor_coverage.py --base-url http://127.0.0.1:7910 --tenant tenant-1 --org org-1 --cad-format IGES --dir "/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian" --extensions iges,igs --output docs/CAD_EXTRACTOR_COVERAGE_LINGJIAN_IGES.md
$PY scripts/collect_cad_extractor_coverage.py --base-url http://127.0.0.1:7910 --tenant tenant-1 --org org-1 --cad-format NX --dir "/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian" --extensions prt,asm --output docs/CAD_EXTRACTOR_COVERAGE_LINGJIAN_PRT.md
```

Result:

```text
Coverage reports updated
```
