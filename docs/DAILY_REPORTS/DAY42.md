# Day 42 - CAD 2D Auto-Detect (ZWCAD)

## Scope
- Strengthen connector auto-detection and verify ZWCAD token matching.

## Verification - CAD 2D Connectors

Command:

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_AUTH_MODE=required

bash scripts/verify_cad_connectors_2d.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL CHECKS PASSED
```

Notes:
- Auto-detect ZWCAD from signature token
