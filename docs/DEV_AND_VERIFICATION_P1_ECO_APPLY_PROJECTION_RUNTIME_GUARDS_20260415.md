# P1 ECO Apply Projection Runtime Guards

Date: 2026-04-15

## Scope
- Keep `ECOService.action_apply(...)` runtime projection aligned with the file-lock contract already enforced by diagnostics.
- Ensure the final `VersionFile -> ItemFile` projection step runs with the acting user context instead of bypassing `sync_version_files_to_item(...)` runtime guards.

## Changes
- `src/yuantus/meta_engine/services/eco_service.py`
  - `action_apply(...)` now passes `user_id` into `VersionFileService.sync_version_files_to_item(...)`.
- `src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py`
  - Asserted that apply-time projection now carries `user_id`.
  - Added a runtime regression that forces `sync_version_files_to_item(...)` to raise a lock error and verifies `action_apply(...)` surfaces it as a `ValueError`.

## Verification
- `PYTHONPATH=src python3 -m pytest -q src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py`
- `PYTHONPATH=src python3 -m py_compile src/yuantus/meta_engine/services/eco_service.py src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py`

## Observed Result
- `29 passed, 1 warning`
- `py_compile` passed
- No full-repo regression was run locally for this slice
