# Day 27 - Document Lifecycle (Controlled Release)

## Scope
- Seed Document ItemType with lifecycle map and transitions.
- Enforce version_lock on AML update/delete and file attach/detach.
- Auto-init version on Released state before release.

## Verification

Command:

```bash
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_SCHEMA_MODE=migrations \
  bash scripts/verify_document_lifecycle.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL CHECKS PASSED
Document: cba51d5c-6337-4c03-b86f-c8a66a1947ca
```
