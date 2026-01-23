# Relationship -> Item Phase 3 Verification (2026-01-23 21:55 +0800)

## 环境

- 基地址：`http://127.0.0.1:7910`
- 平台管理员：`platform-admin` @ `platform`
- 运行模式：`db-per-tenant-org`

## 验证命令

```bash
API=http://127.0.0.1:7910/api/v1
TOKEN=$(curl -s -X POST "$API/auth/login" \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"platform","username":"platform-admin","password":"platform-admin"}' \
  | .venv/bin/python -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))')

# 1) 初始阻断计数
curl -s "$API/admin/relationship-writes?window_seconds=86400&recent_limit=20&warn_threshold=1" \
  -H "Authorization: Bearer $TOKEN" -H 'x-tenant-id: platform'

# 2) 模拟一次写入阻断
curl -s -X POST "$API/admin/relationship-writes/simulate?operation=insert&warn_threshold=1" \
  -H "Authorization: Bearer $TOKEN" -H 'x-tenant-id: platform'

# 3) 再次查询
curl -s "$API/admin/relationship-writes?window_seconds=86400&recent_limit=20&warn_threshold=1" \
  -H "Authorization: Bearer $TOKEN" -H 'x-tenant-id: platform'
```

## 结果摘要

- 初始 `blocked=0`
- 模拟后 `blocked=1` 且 `warn=true`
- 阻断计数可读、可告警

## 日志

- `docs/RELATIONSHIP_WRITE_BLOCKS_20260123_215530.log`
