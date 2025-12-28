# Day 20 - Tenant Provisioning + Quotas

## Scope
- Add tenant/org provisioning endpoints and quota APIs.
- Enforce quotas for users, orgs, files, and jobs.
- Add quota verification script and docs.

## Verification

Command:

```bash
YUANTUS_DATABASE_URL='sqlite:///./tmp_quota_meta.db' \
YUANTUS_IDENTITY_DATABASE_URL='sqlite:///./tmp_quota_identity.db' \
YUANTUS_STORAGE_TYPE='local' \
YUANTUS_LOCAL_STORAGE_PATH='./data/storage_quota_test' \
  bash scripts/verify_quotas.sh http://127.0.0.1:7911 tenant-1 org-1
```

Result:

```text
ALL CHECKS PASSED
```

## Multi-Tenancy Verification

Command:

```bash
MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_multitenancy.sh http://127.0.0.1:7910 tenant-1 tenant-2 org-1 org-2
```

Result:

```text
ALL CHECKS PASSED
```

## Multi-Tenancy Regression (db-per-tenant-org)

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
PASS: 20  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

## Regression

Command:

```bash
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
PASS: 18  FAIL: 0  SKIP: 2
ALL TESTS PASSED
```

## Audit Regression

Command:

```bash
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
PASS: 19  FAIL: 0  SKIP: 1
ALL TESTS PASSED
```

Additional Docker verification (7910):

```bash
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_quotas.sh http://127.0.0.1:7910 tenant-1 org-1
```

```text
ALL CHECKS PASSED
```
