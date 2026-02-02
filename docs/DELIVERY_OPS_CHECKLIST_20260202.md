# Delivery Ops Checklist (2026-02-02)

## Before Start

- [ ] Verify package checksums
- [ ] Confirm env template copied and secrets set
- [ ] Ensure Docker/Compose installed

## After Start

- [ ] `docker ps` shows expected services
- [ ] Logs show no repeated crash loops
- [ ] Health endpoints respond (if enabled)

## Backups & Restore

- [ ] Backup script reviewed and configured
- [ ] Restore script reviewed and tested (optional)

## Security

- [ ] TLS certs placed under `certs/`
- [ ] Default credentials changed (if applicable)

## Sign-off

- Ops: ____________________  Date: ____________
- Delivery Owner: __________ Date: ____________
