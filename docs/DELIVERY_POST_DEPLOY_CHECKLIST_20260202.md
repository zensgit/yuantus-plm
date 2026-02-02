# Post-Deployment Verification Checklist (2026-02-02)

## Service Health

- [ ] `docker ps` shows expected services
- [ ] No repeated crash loops in logs
- [ ] Basic health endpoints respond (if configured)

## Core Functions

- [ ] Login works
- [ ] Create/search basic items works
- [ ] File upload/download works

## Optional (if enabled)

- [ ] CAD preview endpoints accessible
- [ ] E-sign flow (reason → manifest → sign → verify)

## Data & Backup

- [ ] DB connectivity verified
- [ ] Backup script tested (optional)

## Sign-off

- Customer Representative: ____________________  Date: ____________
- Delivery Owner: _____________________________  Date: ____________
