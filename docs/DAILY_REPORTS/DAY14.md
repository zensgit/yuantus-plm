# Day 14 - Baseline Snapshot + Regression

## Scope
- Rebuild docker images to load Baseline API and migration.
- Verify baseline snapshot/compare workflow against the dockerized API.
- Run the full regression suite including Baseline.

## Verification

Command:

```bash
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_SCHEMA_MODE=migrations \
  bash scripts/verify_baseline.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL CHECKS PASSED
```

Command:

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_SCHEMA_MODE=migrations \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
PASS: 17  FAIL: 0  SKIP: 2
ALL TESTS PASSED
```
