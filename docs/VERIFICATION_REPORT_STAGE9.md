# Verification Report Stage 9

Date: 2026-01-19

## Summary

All Stage 1-4 verification runs completed on the existing multi-tenant compose stack.
Final full regression completed with PASS: 41, FAIL: 0, SKIP: 10.

## Environment

- Base URL: http://127.0.0.1:7910
- CAD extractor URL: http://127.0.0.1:8200
- S3 endpoint (MinIO): http://localhost:59000
- Storage: s3
- DB URL (tenant/org): postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus
- DB URL template: postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}
- Identity DB URL: postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg

## Runs

| Run ID | Script | Result | Log |
| --- | --- | --- | --- |
| CAD-CONNECTORS-CONFIG-20260119-2011 | scripts/verify_cad_connectors_config.sh | PASS | /tmp/verify_cad_connectors_config_s7.log |
| CAD-CONNECTORS-20260119-2013 | scripts/verify_cad_connectors.sh (RUN_REAL=1) | PASS | /tmp/verify_cad_connectors_s7.log |
| CAD-EXTRACTOR-EXTERNAL-20260119-2017 | scripts/verify_cad_extractor_external.sh | PASS | /tmp/verify_cad_extractor_external_s7.log |
| CAD-EXTRACTOR-SERVICE-20260119-2018 | scripts/verify_cad_extractor_service.sh | PASS | /tmp/verify_cad_extractor_service_s7.log |
| CAD-SYNC-TEMPLATE-20260119-2019 | scripts/verify_cad_sync_template.sh | PASS | /tmp/verify_cad_sync_template_s7.log |
| CAD-AUTO-PART-20260119-2019 | scripts/verify_cad_auto_part.sh | PASS | /tmp/verify_cad_auto_part_s7.log |
| DOCS-S2-20260119-2020 | scripts/verify_documents.sh | PASS | /tmp/verify_documents_s7.log |
| DOC-LIFECYCLE-20260119-2021 | scripts/verify_document_lifecycle.sh | PASS | /tmp/verify_document_lifecycle_s7.log |
| DOCS-APPROVAL-20260119-2022 | scripts/verify_docs_approval.sh | PASS | /tmp/verify_docs_approval_s7.log |
| DOCS-ECO-UI-20260119-2022 | scripts/verify_docs_eco_ui.sh | PASS | /tmp/verify_docs_eco_ui_s7.log |
| VERSION-FILES-20260119-2023 | scripts/verify_version_files.sh | PASS | /tmp/verify_version_files_s7.log |
| OPS-HARDENING-20260119-2024 | scripts/verify_ops_hardening.sh | PASS | /tmp/verify_ops_hardening_stage4.log |
| ALL-20260119-2037 | scripts/verify_all.sh (RUN_OPS_S8=1 RUN_UI_AGG=1) | PASS 41 / FAIL 0 / SKIP 10 | /tmp/verify_all_stage4_pass.log |

## Notes

- CAD connector tests used real HAOCHEN/ZHONGWANG samples.
- Full regression required S3 and CAD extractor endpoints to be reachable.
- Optional CAD ML vision checks remain skipped if the external service is not running.

## References

Detailed command lines and outputs are appended in `docs/VERIFICATION_RESULTS.md`.
