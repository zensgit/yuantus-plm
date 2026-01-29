# Development Report - Multi-Tenancy Ops Runbook

Date: 2026-01-29

## Goal

Provide a deployable, step-by-step operations runbook for db-per-tenant-org deployments
(start/stop, migrations, provisioning, backup/restore, health checks, and troubleshooting).

## Deliverable

- `docs/OPS_RUNBOOK_MT.md`

## Covered Sections

- Environment checklist
- Start/stop (compose)
- Migrations & bootstrap
- Tenant provisioning
- Backup/restore
- Monitoring & health
- Common issues
- Minimal verification checklist

## Notes

This runbook is designed for private deployments with PostgreSQL + MinIO.
