# C13 Subcontracting Bootstrap Verification

## Touched Files
- `src/yuantus/meta_engine/subcontracting/__init__.py`
- `src/yuantus/meta_engine/subcontracting/models.py`
- `src/yuantus/meta_engine/subcontracting/service.py`
- `src/yuantus/meta_engine/web/subcontracting_router.py`
- `src/yuantus/meta_engine/tests/test_subcontracting_service.py`
- `src/yuantus/meta_engine/tests/test_subcontracting_router.py`
- `src/yuantus/api/app.py`

## Verification Targets
- service lifecycle for create / vendor assign / issue / receipt / timeline
- router contract for create / list / detail / issue / receipt / timeline
- app registration

## Commands
```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/subcontracting/__init__.py \
  src/yuantus/meta_engine/subcontracting/models.py \
  src/yuantus/meta_engine/subcontracting/service.py \
  src/yuantus/meta_engine/web/subcontracting_router.py \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/tests/test_subcontracting_service.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_subcontracting_service.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_subcontracting_router.py \
  src/yuantus/meta_engine/tests/test_quality_router.py \
  src/yuantus/meta_engine/tests/test_maintenance_router.py \
  src/yuantus/meta_engine/tests/test_locale_router.py
```

```bash
git diff --check
```

## Results
- `py_compile`: passed
- subcontracting service/router pack:
  - `9 passed, 3 warnings`
- app router cross-pack:
  - `23 passed, 21 warnings`
- `git diff --check`: passed

## Warnings
- `starlette.formparsers` pending deprecation for `python_multipart`
- `httpx` `app=` shortcut deprecation in test client stack
