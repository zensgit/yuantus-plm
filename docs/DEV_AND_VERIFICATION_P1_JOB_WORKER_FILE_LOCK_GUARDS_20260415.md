# P1 Job Worker File Lock Guards

Date: 2026-04-15

## Scope
- Guard the async CAD derived-file binding path so `JobWorker` no longer mutates `VersionFile` through a foreign version lock.
- Make `VersionFileService.attach_file(...)` enforce version-level lock preconditions for new associations when an acting user is supplied.

## Changes
- `src/yuantus/meta_engine/version/file_service.py`
  - `attach_file(...)` now rejects new writes when:
    - the version is released
    - the version is checked out by another user
- `src/yuantus/meta_engine/services/job_worker.py`
  - derived-file post-processing now passes `job.created_by_id` into `attach_file(...)`
- Tests
  - extended `src/yuantus/meta_engine/tests/test_version_file_checkout_service.py`
  - extended `src/yuantus/meta_engine/tests/test_cad_checkin_transaction.py`

## Verification
- `PYTHONPATH=src python3 -m pytest -q src/yuantus/meta_engine/tests/test_version_file_checkout_service.py src/yuantus/meta_engine/tests/test_cad_checkin_transaction.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py`
- `PYTHONPATH=src python3 -m py_compile src/yuantus/meta_engine/version/file_service.py src/yuantus/meta_engine/services/job_worker.py src/yuantus/meta_engine/tests/test_version_file_checkout_service.py src/yuantus/meta_engine/tests/test_cad_checkin_transaction.py`

## Observed Result
- `21 passed, 1 warning`
- `py_compile` passed
