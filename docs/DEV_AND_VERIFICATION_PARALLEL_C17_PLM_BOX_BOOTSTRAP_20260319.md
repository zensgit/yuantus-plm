# C17 – PLM Box Bootstrap – Dev & Verification

## Status
- integrated_verified

## Branch
- Base: `feature/claude-greenfield-base`
- Branch: `feature/claude-c17-plm-box`
- Codex integration branch: `feature/codex-c17-box-integration`

## Scope
- `src/yuantus/meta_engine/box/`
- `src/yuantus/meta_engine/web/box_router.py`
- `src/yuantus/meta_engine/tests/test_box_*.py`

## Files Created

| File | Purpose |
|------|---------|
| `src/yuantus/meta_engine/box/__init__.py` | Package marker |
| `src/yuantus/meta_engine/box/models.py` | BoxItem + BoxContent + enums |
| `src/yuantus/meta_engine/box/service.py` | CRUD, state machine, contents, export |
| `src/yuantus/meta_engine/web/box_router.py` | 5 API endpoints |
| `src/yuantus/meta_engine/tests/test_box_service.py` | 12 service unit tests |
| `src/yuantus/meta_engine/tests/test_box_router.py` | 7 router integration tests |

## Test Coverage

### Service Tests (test_box_service.py) — 12 tests

| Test Class | Test |
|------------|------|
| TestBoxCRUD | test_create_box |
| TestBoxCRUD | test_get_box |
| TestBoxCRUD | test_list_with_filters |
| TestBoxCRUD | test_update_box |
| TestBoxCRUD | test_create_invalid_type |
| TestBoxState | test_draft_to_active |
| TestBoxState | test_active_to_archived |
| TestBoxState | test_invalid_transition |
| TestBoxState | test_archived_terminal |
| TestBoxContents | test_add_content |
| TestBoxContents | test_list_contents |
| TestBoxContents | test_remove_content |

### Router Tests (test_box_router.py) — 7 tests

| Test |
|------|
| test_create_item |
| test_list_items |
| test_get_item |
| test_get_contents |
| test_export_meta |
| test_not_found_404 |
| test_create_invalid_400 |

## Verification Steps

1. `pytest src/yuantus/meta_engine/tests/test_box_service.py -v`
2. `pytest src/yuantus/meta_engine/tests/test_box_router.py -v`
3. `bash scripts/check_allowed_paths.sh --mode staged`
4. `git diff --check`

## Codex Integration Verification

### Commands
1. `PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile src/yuantus/meta_engine/box/__init__.py src/yuantus/meta_engine/box/models.py src/yuantus/meta_engine/box/service.py src/yuantus/meta_engine/web/box_router.py src/yuantus/meta_engine/tests/test_box_service.py src/yuantus/meta_engine/tests/test_box_router.py`
2. `pytest -q src/yuantus/meta_engine/tests/test_box_service.py src/yuantus/meta_engine/tests/test_box_router.py`
3. `pytest -q src/yuantus/meta_engine/tests/test_file_viewer_readiness.py src/yuantus/meta_engine/tests/test_approvals_router.py src/yuantus/meta_engine/tests/test_subcontracting_router.py src/yuantus/meta_engine/tests/test_quality_analytics_router.py src/yuantus/meta_engine/tests/test_maintenance_router.py src/yuantus/meta_engine/tests/test_box_router.py`
4. `git diff --check`

### Results
- `py_compile`: passed
- targeted `C17` pack:
  - `19 passed, 8 warnings`
- light cross-pack regression:
  - `66 passed, 53 warnings`
- `git diff --check`: passed
