# CAD 3D Connector Plugin Verification (2026-01-27)

## Summary
Validated the connector **contract** (stub service) and **PLM 3D connector metadata** flow.

- Stub connector: **PASS**
- PLM 3D connector metadata: **PASS**

## Environment
- Base URL: `http://127.0.0.1:7910`
- Tenancy mode: `db-per-tenant-org`
- Tenant/Org: `tenant-1` / `org-1`

## 1) Connector Stub Contract
Command:
```bash
bash scripts/verify_cad_connector_stub.sh
```

Output:
```text
OK: Health check
OK: Capabilities
OK: Convert + artifacts

==============================================
CAD Connector Stub Verification Complete
==============================================
ALL CHECKS PASSED
```

## 2) PLM 3D Connector Metadata
Command:
```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' bash scripts/verify_cad_connectors_3d.sh http://127.0.0.1:7910 tenant-1 org-1
```

Output:
```text
==============================================
CAD 3D Connectors Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta

==> Login as admin
OK: Admin login

==> Create dummy 3D files
OK: Created files

==> Upload solidworks_part_1769519215.sldprt
OK: Uploaded file: 0fd4dfa5-a9bb-460a-a040-75ae1de8d6a6
Metadata OK
OK: Metadata verified (SOLIDWORKS)

==> Upload solidworks_asm_1769519215.sldasm
OK: Uploaded file: af2cdf05-d853-4a55-b5cc-5b5db37d7f15
Metadata OK
OK: Metadata verified (SOLIDWORKS)

==> Upload nx_1769519215.prt
OK: Uploaded file: 11a6a290-1c35-481f-9b06-7dd853fd017e
Metadata OK
OK: Metadata verified (NX)

==> Upload creo_1769519215.prt
OK: Uploaded file: 7642f23b-c92d-4286-a921-7f3efc87049a
Metadata OK
OK: Metadata verified (CREO)

==> Upload catia_1769519215.catpart
OK: Uploaded file: adc51ec6-235d-4e0f-bcf9-a77e6a2e8d7e
Metadata OK
OK: Metadata verified (CATIA)

==> Upload inventor_1769519215.ipt
OK: Uploaded file: dc31c63b-12bc-4c2c-97ee-8ed3e4ec1a7b
Metadata OK
OK: Metadata verified (INVENTOR)

==> Upload auto_1769519215.prt
OK: Uploaded file: 6fe8f60b-9188-422e-a535-830582dd78ed
Metadata OK
OK: Metadata verified (NX)

==> Cleanup
OK: Cleaned up temp files

==============================================
CAD 3D Connectors Verification Complete
==============================================
ALL CHECKS PASSED
```

## Result
ALL CHECKS PASSED
