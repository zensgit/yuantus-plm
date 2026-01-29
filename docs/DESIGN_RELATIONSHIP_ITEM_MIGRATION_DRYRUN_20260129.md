# Relationship Item Migration Dry-Run Design (2026-01-29)

## Goal
Confirm whether legacy `meta_relationships` data exists in multi-tenant databases and whether migration is required before enforcing relationship-as-item only semantics.

## Scope
- db-per-tenant-org databases (tenant-1/org-1, tenant-1/org-2, tenant-2/org-1, tenant-2/org-2)
- platform tenant database (platform/platform)

## Method
Run the migration script in **dry-run** mode across tenant/org combinations. This reports counts and missing tables without writing data.

## Commands
```bash
PYTHONPATH=src .venv/bin/python scripts/migrate_relationship_items.py --tenant tenant-1 --org org-1 --dry-run
PYTHONPATH=src .venv/bin/python scripts/migrate_relationship_items.py --tenant tenant-1 --org org-2 --dry-run
PYTHONPATH=src .venv/bin/python scripts/migrate_relationship_items.py --tenant tenant-2 --org org-1 --dry-run
PYTHONPATH=src .venv/bin/python scripts/migrate_relationship_items.py --tenant tenant-2 --org org-2 --dry-run
PYTHONPATH=src .venv/bin/python scripts/migrate_relationship_items.py --tenant platform --org platform --dry-run
```

## Expected Outcomes
- If `meta_relationships` tables are empty or missing, migration is not required.
- If rows exist, proceed with a write migration and verification per `docs/RUNBOOK_RELATIONSHIP_ITEM_MIGRATION.md`.
