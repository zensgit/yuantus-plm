# C14 Approvals Export Ops-Report Bootstrap Verification

## Touched Files
- `src/yuantus/meta_engine/approvals/service.py`
- `src/yuantus/meta_engine/web/approvals_router.py`
- `src/yuantus/meta_engine/tests/test_approvals_service.py`
- `src/yuantus/meta_engine/tests/test_approvals_router.py`

## Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/approvals/service.py \
  src/yuantus/meta_engine/web/approvals_router.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py
```

## Results
- `py_compile`: passed
- approvals targeted pack:
  - included in combined `C14/C15` regression
  - no contract failures observed

## Notes
- `/requests/export` placed before `/{request_id}`
- router contract validated for `json` / `csv` / `markdown`
