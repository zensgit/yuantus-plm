# S8 Ops Monitoring Design (2026-01-29)

## Goal
Validate ops monitoring endpoints in a deployment with quota enforcement, audit logging, and reports summary metadata enabled.

## Scope
- Quota monitoring (org/user/file/job)
- Audit retention endpoints (list + prune)
- Reports summary metadata endpoint

## Preconditions
- `YUANTUS_QUOTA_MODE=enforce`
- `YUANTUS_AUDIT_ENABLED=true`
- Platform admin enabled for monitoring routes

## Verification Command
```bash
bash scripts/verify_ops_s8.sh http://127.0.0.1:7910 tenant-1 org-1 \
  | tee docs/VERIFICATION_OPS_S8_YYYYMMDD_HHMM.md
```

## Pass Criteria
All sections report `ALL CHECKS PASSED` and the final summary reports `S8 Ops Verification Complete`.
