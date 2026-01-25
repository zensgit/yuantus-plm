# Full Regression Verification (2026-01-24 22:44 +0800)

## 范围

- scripts/verify_all.sh 全量回归（HTTP + Docker 运行环境）
- 开启标志：`RUN_UI_AGG=1 RUN_OPS_S8=1 RUN_TENANT_PROVISIONING=1`

## 执行命令

```bash
RUN_UI_AGG=1 RUN_OPS_S8=1 RUN_TENANT_PROVISIONING=1 \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 \
  | tee docs/VERIFY_ALL_HTTP_20260124_224416.log
```

## 结果摘要

- PASS: 44
- FAIL: 0
- SKIP: 8

## 日志

- `docs/VERIFY_ALL_HTTP_20260124_224416.log`
