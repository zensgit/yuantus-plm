# Day 30 - Part Lifecycle + Full Regression

## Scope
- Run full regression with audit logs enabled in db-per-tenant-org mode.
- Validate new Part lifecycle behavior and Released lock enforcement.

## Verification

Command:

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_AUDIT_ENABLED=true \
YUANTUS_SCHEMA_MODE=migrations \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
PASS: 25  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

Notes:
- Document: 44646439-2d64-42a7-b074-6a7fb639359e
- Part (lifecycle): 9a69f018-2fe0-465c-be8b-c63cede0b105
- CAD File (S5-A): 9a7dad67-2ac2-46f1-bbb7-b3119f48c533

## Additional Verification

### BOM Compare (Field-Level Diff)

Command:

```bash
bash scripts/verify_bom_compare.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL CHECKS PASSED
```

Notes:
- Parent A: c249c7d0-74f1-49b9-992c-b2faa93c271f
- Parent B: 1882f18a-ebd9-4283-875f-f11794beca00
