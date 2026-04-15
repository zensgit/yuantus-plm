# P1 Job Worker Projection Lock Guards

## Scope
- Prevent background CAD derived-file binding from mutating version/item projections when a target version still has foreign file locks.
- Carry acting-user context into `sync_version_files_to_item(...)` for current-version projection writes.

## Code Changes
- `src/yuantus/meta_engine/services/job_worker.py`
  - Before binding a derived file, check `get_blocking_file_locks(version_id, user_id=job.created_by_id)`.
  - Skip bind/project for versions that still have foreign file locks.
  - Pass `user_id=job.created_by_id` into `sync_version_files_to_item(...)`.
- `src/yuantus/meta_engine/version/file_service.py`
  - `sync_version_files_to_item(...)` now accepts optional `user_id`.
  - When `user_id` is provided, it rejects:
    - released versions
    - versions checked out by another user
    - versions with foreign file locks
- `src/yuantus/meta_engine/tests/test_cad_checkin_transaction.py`
  - Added worker regression for “skip derived-file bind when foreign file locks exist”.
  - Updated current-version projection expectation to include `user_id`.
- `src/yuantus/meta_engine/tests/test_version_file_checkout_service.py`
  - Added service regression for `sync_version_files_to_item(...)` rejecting foreign file locks.
- `docs/DELIVERY_DOC_INDEX.md`
  - Added this delivery document entry.

## Verification
- `PYTHONPATH=src python3 -m pytest -q src/yuantus/meta_engine/tests/test_cad_checkin_transaction.py src/yuantus/meta_engine/tests/test_version_file_checkout_service.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py`
- `PYTHONPATH=src python3 -m py_compile src/yuantus/meta_engine/services/job_worker.py src/yuantus/meta_engine/version/file_service.py src/yuantus/meta_engine/tests/test_cad_checkin_transaction.py src/yuantus/meta_engine/tests/test_version_file_checkout_service.py`

## Result
- Background CAD derived-file binding no longer projects into a version/item surface when that version still has foreign file locks.
- Current-version projection writes now use the same acting-user lock contract as the rest of the version/file mutation path.
