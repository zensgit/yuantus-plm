# verify_all Regression Report (2026-01-05, Run B)

## Command
```
RUN_CADGF_PREVIEW_ONLINE=1 \
YUANTUS_CADGF_DEFAULT_EMIT=json,gltf,meta \
CADGF_PREVIEW_SAMPLE_FILE="$CADGF_PREVIEW_SAMPLE_FILE" \
scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Inputs
- BASE_URL: http://127.0.0.1:7910
- TENANT/ORG: tenant-1 / org-1
- CADGF_PREVIEW_SAMPLE_FILE (escaped JSON):
  "/Users/huazhou/Downloads/4000\u4f8bCAD\u53ca\u4e09\u7ef4\u673a\u68b0\u96f6\u4ef6\u7ec3\u4e60\u56fe\u7eb8/\u673a\u68b0CAD\u56fe\u7eb8/1200\u578b\u98ce\u9001\u5f0f\u55b7\u96fe\u673a/1200\u578b\u98ce\u9001\u5f0f\u55b7\u96fe\u673a.dwg"

## Summary
- PASS: 42
- FAIL: 0
- SKIP: 0

## CADGF Preview Online
- Script: scripts/verify_cad_preview_online.sh
- Report: /tmp/cadgf_preview_online_report.md
- Result: PASS
- EXPECT_METADATA: 1 (inferred from YUANTUS_CADGF_DEFAULT_EMIT)
- Manifest includes mesh_metadata: yes
- metadata_present: yes

## Notes
- Full log: /tmp/verify_all_full_20260105_161403.log
- CADGF preview manifest verified with rewrite=1 and includes mesh_metadata.
