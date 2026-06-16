# ECM Publish — P1D Transfer Receiver Adapter (Dev & Verification)

Date: 2026-06-16
Branch: `codex/ecm-p1d-transfer-adapter`
Follows: P1D retarget taskbook
`docs/DEVELOPMENT_ECM_PUBLISH_P1D_RETARGET_TRANSFER_RECEIVER_TASKBOOK_20260616.md`

## 1. Scope

This slice retargets the real ECM publication connector from the provisional CMIS
skeleton to Athena's Transfer Receiver surface:

- `AthenaTransferReceiverAdapter` sends released controlled files to
  `/api/v1/transfer/receiver/folders` and `/api/v1/transfer/receiver/documents`.
- `adapter_registry.resolve_adapter()` now resolves the Transfer Receiver adapter when
  `PUBLICATION_ECM_TARGET_SYSTEM` and an Athena base URL are configured and the row's
  `target_system` matches. The CMIS adapter remains only as an in-tree compliance
  reference; it is no longer resolved.
- `EcmPublicationOutboxWorker` now honors `ECM_PUBLISH_ENABLED` at dispatch time for the
  configured live ECM target. With the switch off, matching rows are not claimed.

No routes, no tables, and no live Athena I/O are added by this slice's tests.

## 2. Contract

The adapter follows the P1D retarget decisions:

- `sourceNodeId = uuid5(NAMESPACE_PLM, "item_id|version_id|file_id|file_role")`.
- `sourceRepositoryId = PUBLICATION_ECM_SOURCE_REPOSITORY_ID`.
- `sourceLastModifiedAt = released_at` as a stable LocalDateTime string. Null
  `released_at` fails closed unless
  `PUBLICATION_ECM_ALLOW_RELEASED_AT_SENTINEL=true`, in which case the fixed sentinel
  `1970-01-01T00:00:00` is used.
- `conflictPolicy` is sent explicitly, defaulting to `SKIP`.
- The worker send path reads bytes from `FileService.download_file(system_path, ...)`;
  enqueue remains byte-free.
- Successful `disposition` values
  `{CREATED, RENAMED, OVERWRITTEN, UNCHANGED, SKIPPED}` all mark the outbox row `sent`.
  The outbox properties now persist `athena_document_id` and
  `athena_disposition` in addition to the generic `remote_id`.

## 3. Settings

Production Transfer Receiver settings are:

- `PUBLICATION_ECM_TARGET_SYSTEM`
- `PUBLICATION_ECM_BASE_URL` (or `ATHENA_BASE_URL`)
- `PUBLICATION_ECM_TRANSFER_USER`
- `PUBLICATION_ECM_TRANSFER_SECRET`
- `PUBLICATION_ECM_ROOT_FOLDER_ID`
- `PUBLICATION_ECM_SOURCE_REPOSITORY_ID`
- `PUBLICATION_ECM_CONFLICT_POLICY`
- `PUBLICATION_ECM_TRANSFER_MAX_BYTES`
- `PUBLICATION_ECM_ALLOW_RELEASED_AT_SENTINEL`
- `PUBLICATION_ECM_TIMEOUT_SECONDS`

The existing CMIS-oriented `PUBLICATION_ECM_SERVICE_TOKEN`, `PUBLICATION_ECM_PATH`,
`PUBLICATION_ECM_REPOSITORY_ID`, `PUBLICATION_ECM_ROOT_FOLDER_PATH`, and
`PUBLICATION_ECM_OBJECT_TYPE_ID` fields remain declared for the compliance-reference
adapter only. They are not used by the resolver's Transfer Receiver path.

## 4. Error Semantics

- 2xx with a valid `{documentId, disposition}` response is success.
- 5xx, timeout/connection, `408`, `429`, `3xx`, and circuit-open are retryable
  `remote_error`.
- Receiver credential/scope failures (`401`/`403`), quota/request-shape/client errors
  (`400`/`404`/`409`/`422`), malformed success bodies, invalid disposition, and local
  contract failures are terminal `validation_error`.
- Storage read failure is `remote_error` because the file may become available on retry.

## 5. Verification

Local verification target:

```bash
unset YUANTUS_PYTEST_DB YUANTUS_TEST_DB PYTEST_DB
python -m pytest \
  src/yuantus/meta_engine/tests/test_ecm_transfer_receiver_adapter.py \
  src/yuantus/meta_engine/tests/test_ecm_cmis_adapter.py \
  src/yuantus/meta_engine/tests/test_ecm_publication_worker.py -q
```

Expected covered cases:

- Transfer payload identity folding, stable released-at watermark, sentinel fallback,
  required settings, `system_path`, and size cap.
- Folder ensure + multipart document upload request shape, Transfer Receiver custom
  headers, no bearer authorization header, explicit `SKIP`, and persisted Athena
  `documentId`/`disposition`.
- Success disposition matrix and retryable vs terminal failure classification.
- Resolver configured branch returns `AthenaTransferReceiverAdapter`, not CMIS.
- Worker dispatch kill-switch excludes the configured live ECM target from claim when
  `ECM_PUBLISH_ENABLED=false`.

## 6. Deferred

Live Phase 0 U1-U5 remains deferred until Athena endpoint, receiver registration,
root folder, and credential provisioning are available. The test suite uses mocked HTTP
only; it proves the PLM-side contract and state machine, not live Athena delivery.
