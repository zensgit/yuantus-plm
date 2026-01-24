# Relationship -> Item Phase 3 Seeder Verification (2026-01-24 14:29 +0800)

## 环境

- 方式：本地脚本 + SQLite 内存库
- 目的：验证 legacy `RelationshipType` 仅在开关开启时播种

## 执行命令

```bash
scripts/verify_relationship_type_seeding.sh | tee docs/VERIFY_RELATIONSHIP_TYPE_SEEDING_20260124_1429.log
```

## 结果摘要

- legacy disabled：`RelationshipType=0`
- legacy enabled：`RelationshipType>=1`
- `Part BOM` ItemType 始终为 `is_relationship=true`

## 日志

- `docs/VERIFY_RELATIONSHIP_TYPE_SEEDING_20260124_1429.log`
