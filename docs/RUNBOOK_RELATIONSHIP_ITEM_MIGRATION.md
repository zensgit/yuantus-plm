# Runbook: Relationship -> Item Migration (Production)

目标：将 legacy `meta_relationships` 数据迁移到 `meta_items`，统一关系模型，并在迁移后确保系统只读兼容层可观测。

## 1. 适用范围

- 多租户：`db-per-tenant` 或 `db-per-tenant-org`
- 单租户：`single`
- 适用版本：已包含 `scripts/migrate_relationship_items.py` 且兼容层写入已硬阻断

## 2. 前置检查

- 确认服务版本包含迁移脚本与只读阻断
- 确认业务低峰窗口
- 确认 DBA/运维已完成备份策略

## 3. 备份

### 3.1 Postgres 备份（db-per-tenant-org）

```bash
# tenant/org DB 列表示例
DBS=("yuantus_mt_pg__tenant-1__org-1" "yuantus_mt_pg__tenant-1__org-2")

TS=$(date +%Y%m%d_%H%M%S)
DIR="/backups/rel-migration-${TS}"
mkdir -p "$DIR"

for db in "${DBS[@]}"; do
  pg_dump -U yuantus -d "$db" > "$DIR/${db}.sql"
  echo "OK: $db"
done
```

### 3.2 单库备份（single）

```bash
pg_dump -U yuantus -d yuantus > /backups/yuantus_${TS}.sql
```

## 4. Dry-run 预检

```bash
# db-per-tenant-org
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  python scripts/migrate_relationship_items.py --tenant <tenant> --org <org> --dry-run
```

检查输出：
- `Missing type/source/related` 必须为 0 或改用 `--allow-orphans`

## 5. 实际迁移

```bash
# db-per-tenant-org
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  python scripts/migrate_relationship_items.py --tenant <tenant> --org <org> --update-item-types
```

## 6. 验证

### 6.1 关系数量对齐

```sql
SELECT COUNT(*) FROM meta_relationships;
SELECT COUNT(*) FROM meta_items WHERE id IN (SELECT id FROM meta_relationships);
```

### 6.2 业务回归（推荐）

```bash
bash scripts/verify_bom_tree.sh http://127.0.0.1:7910 tenant-1 org-1
bash scripts/verify_where_used.sh http://127.0.0.1:7910 tenant-1 org-1
```

## 7. 回滚

若出现问题，可按备份恢复：

```bash
psql -U yuantus -d <db> < /backups/rel-migration-*/<db>.sql
```

或清理迁移写入：

```sql
DELETE FROM meta_items WHERE id IN (SELECT id FROM meta_relationships);
```

## 8. 注意事项

- 迁移为“追加写入”，不会删除 legacy 表。
- 兼容层写入已硬阻断；如需写入请改用 Item 关系。
- 迁移应按 tenant/org 分批执行并记录日志。
