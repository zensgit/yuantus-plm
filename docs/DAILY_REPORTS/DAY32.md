# Day 32 - CAD Productionization (Connectors + Template + Extractor)

## Scope
- Add connector config reload API and inline config support.
- Add CAD sync template export/import endpoints.
- Enforce external CAD extractor mode and local temp handling.

## Verification - CAD Connectors Config

Command:

```bash
bash scripts/verify_cad_connectors_config.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL CHECKS PASSED
```

Notes:
- Demo File: abcb82e2-ac65-43e4-9bb7-8167a51b82b4

## Verification - CAD Sync Template

Command:

```bash
bash scripts/verify_cad_sync_template.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL CHECKS PASSED
```

Notes:
- Part: item_number/description marked cad_synced
- item_number cad_key=part_number

## Verification - CAD Extractor Stub

Command:

```bash
bash scripts/verify_cad_extractor_stub.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL CHECKS PASSED
```

Notes:
- File: c4bdee3c-5501-45ce-bccb-d22be2c0fc13
- Job: 05e2f7d3-05b3-4ac9-a4be-888680ef4fa8
- Warnings: cadquery not installed; boto3 Python 3.9 deprecation
