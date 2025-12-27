# YuantusPLM Private Backup/Restore Runbook

This runbook covers private deployment backups for Postgres + MinIO using the
Docker Compose stack provided in this repo.

## Scope

- Postgres logical backups (`pg_dump` custom format)
- MinIO bucket mirror backups (`mc mirror`)
- Restore into the same environment or into isolated targets

## Prerequisites

- Docker Desktop running
- `docker compose` available
- YuantusPLM compose stack running (`yuantusplm` project)

## Scripts

- `scripts/backup_private.sh`
- `scripts/restore_private.sh`
- `scripts/verify_backup_restore.sh`
- `scripts/cleanup_private_restore.sh`
- `scripts/verify_cleanup_restore.sh`

## Environment Variables

Postgres:

- `PROJECT` (default: `yuantusplm`)
- `PG_USER` (default: `yuantus`)
- `PG_PASSWORD` (default: `yuantus`)
- `PG_DATABASES` (optional, comma-separated)
- `PG_DATABASE_PREFIX` (default: `yuantus`)
- `SKIP_POSTGRES` (optional, non-empty to skip)

MinIO:

- `MINIO_ENDPOINT` (default: `http://minio:9000`)
- `MINIO_ACCESS_KEY` (default: `minioadmin`)
- `MINIO_SECRET_KEY` (default: `minioadmin`)
- `MINIO_BUCKET` (default: `yuantus`)
- `SKIP_MINIO` (optional, non-empty to skip)

Restore controls:

- `BACKUP_DIR` (required for restore)
- `CONFIRM` (must be `yes` to run restore)
- `RESTORE_DB_SUFFIX` (optional, restore to new DB names)
- `RESTORE_DROP` (optional, drop DBs before restore)
- `RESTORE_BUCKET` (optional, restore to a new bucket)

## Backup

```bash
BACKUP_DIR=./backups/yuantus_$(date +%Y%m%d_%H%M%S) \
  bash scripts/backup_private.sh
```

Outputs:

- `BACKUP_DIR/postgres/*.dump`
- `BACKUP_DIR/minio/<bucket>/...`
- `BACKUP_DIR/backup_meta.txt`

## Restore (same DB and bucket)

WARNING: this can overwrite data.

```bash
BACKUP_DIR=./backups/yuantus_20251222_141353 \
CONFIRM=yes \
  bash scripts/restore_private.sh
```

## Restore (isolated targets, safe)

Restore into new DB names and a new bucket to avoid touching live data:

```bash
BACKUP_DIR=./backups/yuantus_20251222_141353 \
RESTORE_DB_SUFFIX=_restore_test \
RESTORE_BUCKET=yuantus-restore-test \
CONFIRM=yes \
  bash scripts/restore_private.sh
```

## Verification

```bash
bash scripts/verify_backup_restore.sh
```

## Cleanup Verification

```bash
bash scripts/verify_cleanup_restore.sh
```

## Cleanup (restore artifacts)

After verification, you can remove the temporary restore DBs/buckets:

```bash
CONFIRM=yes DB_LIST=yuantus_restore_1700000000 \\
RESTORE_BUCKET=yuantus-restore-test-1700000000 \\
  bash scripts/cleanup_private_restore.sh
```

## Troubleshooting

- If `docker compose` cannot access the daemon, restart Docker Desktop.
- If Postgres dumps are empty, check database prefix and user/password.
- If MinIO mirror fails, verify bucket name and endpoint.

## Scheduled Backups

See `docs/RUNBOOK_SCHEDULED_BACKUP.md` for cron examples and rotation.
