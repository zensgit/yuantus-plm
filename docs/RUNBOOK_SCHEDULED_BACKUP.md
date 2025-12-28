# YuantusPLM Scheduled Backup Runbook

This runbook shows how to run periodic backups and rotation for a private
YuantusPLM deployment.

## Scripts

- `scripts/backup_scheduled.sh`
- `scripts/backup_rotate.sh`
- `scripts/backup_private.sh`

## Environment Variables

- `BACKUP_ROOT` (default: `./backups`)
- `KEEP` (default: `7`) number of backups to keep
- `ARCHIVE` (optional, any value to enable tar.gz archive)

Other variables are inherited by `scripts/backup_private.sh` (DB/MinIO settings).

## Manual Run

```bash
BACKUP_ROOT=./backups KEEP=7 \
  bash scripts/backup_scheduled.sh
```

With archive:

```bash
BACKUP_ROOT=./backups KEEP=7 ARCHIVE=1 \
  bash scripts/backup_scheduled.sh
```

## Cron Example

Daily backup at 2:30 AM:

```cron
30 2 * * * cd /opt/yuantus && BACKUP_ROOT=/opt/yuantus/backups KEEP=14 ARCHIVE=1 bash scripts/backup_scheduled.sh >> /opt/yuantus/backups/backup.log 2>&1
```

## Rotation Only

```bash
BACKUP_ROOT=./backups KEEP=7 \
  bash scripts/backup_rotate.sh
```

## Verification

```bash
bash scripts/verify_backup_rotation.sh
```
