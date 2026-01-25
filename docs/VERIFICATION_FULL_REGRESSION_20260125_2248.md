# Full Regression Verification (2026-01-25 22:48 +0800)

## Command
```
RUN_CADGF_PREVIEW_ONLINE=1 \
BASE_URL=http://127.0.0.1:7910 \
scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 \
  | tee docs/VERIFY_ALL_HTTP_20260125_2245.log
```

## Result Summary
- PASS: 36
- FAIL: 0
- SKIP: 16
- Overall: ALL TESTS PASSED

## Notes
- CADGF 在线预览已启用（launchd router + host worker）。
- 部分 UI/外部服务相关用例按既定开关跳过。
