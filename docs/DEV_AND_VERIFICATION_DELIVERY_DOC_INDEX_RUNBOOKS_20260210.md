# Dev & Verification Report - Delivery Doc Index (Ops Runbooks + Link Contract) (2026-02-10)

This change improves discoverability of ops runbooks in the delivery documentation index, and adds a small unit test to prevent stale/missing links in `docs/DELIVERY_DOC_INDEX.md`.

## Changes

- `docs/DELIVERY_DOC_INDEX.md`
  - Added key ops runbooks and jobs diagnostics docs to the `Ops & Deployment` section:
    - Runtime
    - Backup/restore
    - Scheduled backup
    - Jobs diagnostics + error codes
    - Relationship item migration
- `src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - New test: validates all backticked repo paths referenced by `docs/DELIVERY_DOC_INDEX.md` exist in the repo.

## Verification

Targeted pytest:

```bash
pytest -q src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

