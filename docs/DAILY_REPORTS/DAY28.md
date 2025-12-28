# Day 28 - Full Regression (verify_all)

## Scope
- Run full regression suite after Document lifecycle rollout.

## Verification

Command:

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_SCHEMA_MODE=migrations \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
PASS: 22  FAIL: 0  SKIP: 2
ALL TESTS PASSED
```

Notes:
- SKIP: Audit Logs (audit_enabled=false)
- SKIP: Multi-Tenancy (tenancy_mode=single)
- Document: 8cd6fb88-b749-4b40-8ac4-0729563ec00d
