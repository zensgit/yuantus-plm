# Day 59 Report

Date: 2025-12-27

## Scope
- Offline CAD 2D connector coverage reports for Haochen/Zhongwang on training DWG set.

## Work Completed
- Fixed report writer in `collect_cad_extractor_coverage.py` (offline output now persisted).
- Added `verify_cad_connector_coverage_2d.sh` and hooked optional coverage stage into `verify_all.sh`.
- Generated offline coverage reports for 110 DWG files using Haochen/Zhongwang connectors.

## Verification

Commands:
```
.venv/bin/python scripts/collect_cad_extractor_coverage.py \
  --offline \
  --cad-format HAOCHEN \
  --cad-connector-id haochencad \
  --dir /Users/huazhou/Downloads/训练图纸/训练图纸 \
  --extensions dwg \
  --report-title "CAD 2D Connector Coverage Report (Haochen, Offline)" \
  --output docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_HAOCHEN.md

.venv/bin/python scripts/collect_cad_extractor_coverage.py \
  --offline \
  --cad-format ZHONGWANG \
  --cad-connector-id zhongwangcad \
  --dir /Users/huazhou/Downloads/训练图纸/训练图纸 \
  --extensions dwg \
  --report-title "CAD 2D Connector Coverage Report (Zhongwang, Offline)" \
  --output docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_ZHONGWANG.md

CAD_CONNECTOR_COVERAGE_DIR=/Users/huazhou/Downloads/训练图纸/训练图纸 \
  bash scripts/verify_cad_connector_coverage_2d.sh | tee /tmp/verify_cad_connector_coverage_2d.log
```

Results:
- Haochen: 110 files, part_number/part_name/drawing_no 100%, revision 99.1%.
- Zhongwang: 110 files, part_number/part_name/drawing_no 100%, revision 99.1%.

Artifacts:
- docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_HAOCHEN.md
- docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_ZHONGWANG.md
- docs/VERIFICATION_RESULTS.md (runs appended)

Additional verification:
```
RUN_CAD_CONNECTOR_COVERAGE_2D=1 \
CAD_CONNECTOR_COVERAGE_DIR=/Users/huazhou/Downloads/训练图纸/训练图纸 \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_with_coverage.log
```

Results:
- PASS: 35
- FAIL: 0
- SKIP: 7

Artifacts:
- /tmp/verify_all_with_coverage.log
