# Where-Used Line Schema Verification (HTTP) (2026-01-24 22:36 +0800)

## 环境

- 方式：HTTP 调用（docker compose api）
- 目的：确认 `/api/v1/bom/where-used/schema` 可用并返回完整字段元信息

## 执行命令

```bash
bash scripts/verify_where_used_schema.sh http://127.0.0.1:7910 tenant-1 org-1 \
  | tee docs/VERIFY_WHERE_USED_SCHEMA_HTTP_20260124_223656.log
```

## 结果摘要

- `verify_where_used_schema.sh`：`ALL CHECKS PASSED`

## 日志

- `docs/VERIFY_WHERE_USED_SCHEMA_HTTP_20260124_223656.log`
