# Local Regression Verification (2026-01-24 21:40 +0800)

## 范围

- Relationship ItemType Expand
- RelationshipType Seeding
- Relationship Legacy Usage
- Where-Used Line Schema
- UI Where-Used (TestClient)
- UI Product Summary (TestClient)
- UI Docs ECO Summary (TestClient)

## 执行命令

```bash
LOCAL_TESTCLIENT=1 bash scripts/verify_all_local.sh \
  http://127.0.0.1:7910 tenant-1 org-1 \
  | tee docs/VERIFY_ALL_LOCAL_20260124_2140.log
```

## 结果摘要

- PASS: 7
- FAIL: 0
- SKIP: 0

## 日志

- `docs/VERIFY_ALL_LOCAL_20260124_2140.log`
