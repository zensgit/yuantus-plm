# Full Regression Verification (2026-01-24 22:34 +0800)

## 范围

- scripts/verify_all.sh 全量回归（HTTP + Docker 运行环境）

## 执行命令

```bash
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 \
  | tee docs/VERIFY_ALL_HTTP_20260124_223403.log
```

## 结果摘要

- PASS: 35
- FAIL: 0
- SKIP: 17

## 日志

- `docs/VERIFY_ALL_HTTP_20260124_223403.log`
