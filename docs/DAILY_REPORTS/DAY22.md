# Day 22 - MBOM Convert

## Scope
- Add EBOM → MBOM conversion API and verification.
- Update regression suite to include MBOM convert.

## Verification

Command:

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_mbom_convert.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL CHECKS PASSED
```

## Regression (db-per-tenant-org)

Command:

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
PASS: 22  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

## Regression (default env)

Command:

```bash
bash scripts/verify_all.sh
```

Result:

```text
PASS: 22  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```
