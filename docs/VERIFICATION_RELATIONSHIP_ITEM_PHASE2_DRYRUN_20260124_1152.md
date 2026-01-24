# Relationship -> Item Phase 2 Dry-Run (2026-01-24 11:52 +0800)

## 环境

- 模式：`db-per-tenant-org`
- 目标：`tenant-1 / org-1`

## 执行命令

```bash
PYTHONPATH=src .venv/bin/python scripts/migrate_relationship_items.py \
  --tenant tenant-1 --org org-1 --dry-run | tee docs/RELATIONSHIP_ITEM_PHASE2_DRYRUN_20260124_1152.log
PYTHONPATH=src .venv/bin/python scripts/migrate_relationship_items.py \
  --tenant tenant-1 --org org-2 --dry-run | tee docs/RELATIONSHIP_ITEM_PHASE2_DRYRUN_20260124_1152_tenant-1_org-2.log
PYTHONPATH=src .venv/bin/python scripts/migrate_relationship_items.py \
  --tenant tenant-2 --org org-1 --dry-run | tee docs/RELATIONSHIP_ITEM_PHASE2_DRYRUN_20260124_1152_tenant-2_org-1.log
PYTHONPATH=src .venv/bin/python scripts/migrate_relationship_items.py \
  --tenant tenant-2 --org org-2 --dry-run | tee docs/RELATIONSHIP_ITEM_PHASE2_DRYRUN_20260124_1152_tenant-2_org-2.log
```

## 结果摘要

tenant-1 / org-1:
- Relationships total: `0`
- existing_items: `0`
- missing_type/source/related: `0/0/0`
- migrated: `0` (dry-run)

tenant-1 / org-2:
- Relationships total: `0`
- existing_items: `0`
- missing_type/source/related: `0/0/0`
- migrated: `0` (dry-run)

tenant-2 / org-1:
- Relationships total: `0`
- existing_items: `0`
- missing_type/source/related: `0/0/0`
- migrated: `0` (dry-run)

tenant-2 / org-2:
- meta_relationships missing -> skipped

## 日志

- `docs/RELATIONSHIP_ITEM_PHASE2_DRYRUN_20260124_1152.log`
- `docs/RELATIONSHIP_ITEM_PHASE2_DRYRUN_20260124_1152_tenant-1_org-2.log`
- `docs/RELATIONSHIP_ITEM_PHASE2_DRYRUN_20260124_1152_tenant-2_org-1.log`
- `docs/RELATIONSHIP_ITEM_PHASE2_DRYRUN_20260124_1152_tenant-2_org-2.log`
