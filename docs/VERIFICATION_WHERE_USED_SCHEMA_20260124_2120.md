# Where-Used Line Schema Verification (2026-01-24 21:20 +0800)

## 环境

- 方式：脚本验证（可使用 `LOCAL_TESTCLIENT=1`）
- 目的：确认 schema 字段完整、含严重度/规范化元信息

## 执行命令

```bash
bash scripts/verify_where_used_schema.sh http://127.0.0.1:7910 tenant-1 org-1
```

## 结果摘要

- `verify_where_used_schema.sh`：`ALL CHECKS PASSED`

## 日志

- `docs/VERIFY_WHERE_USED_SCHEMA_20260124_2120.log`
