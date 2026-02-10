# CI Contracts: README Runbooks Must Be Indexed In Delivery Doc Index (2026-02-10)

## Goals

- Prevent doc drift: anything listed under `README.md` `## Runbooks` must also appear in `docs/DELIVERY_DOC_INDEX.md`.
- Keep operator-facing documentation discoverable from both entry points (README + delivery package index).

## Changes

- Added `src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py`
  - extracts backticked paths from `README.md` `## Runbooks`
  - asserts each path is present (backticked) in `docs/DELIVERY_DOC_INDEX.md`
- Wired the new test into `.github/workflows/ci.yml` `contracts` job.
- Added this document to `docs/DELIVERY_DOC_INDEX.md`.

## Verification (Local)

Workflow YAML parse sanity:

```bash
python3 - <<'PY'
from pathlib import Path
import yaml

workflows = sorted(Path(".github/workflows").glob("*.y*ml"))
for wf in workflows:
    yaml.safe_load(wf.read_text(encoding="utf-8", errors="replace"))
print(f"workflow_yaml_ok={len(workflows)}")
PY
```

Result (2026-02-10): `workflow_yaml_ok=5`.

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_readme_runbook_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result (2026-02-10): `3 passed`.
