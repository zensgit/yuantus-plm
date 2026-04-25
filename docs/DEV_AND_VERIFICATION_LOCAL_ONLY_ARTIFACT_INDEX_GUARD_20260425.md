# Local-Only Artifact Index Guard - Development And Verification

Date: 2026-04-25

## 1. Goal

Prevent machine-local artifacts from being promoted into the delivery document
index. The current worktree intentionally contains `.claude/` and
`local-dev-env/`, but those directories are local execution state and must not
become indexed delivery artifacts.

This change is test-only plus documentation. It does not alter runtime code,
router behavior, CI workflow behavior, or verifier behavior.

## 2. Design

`src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py` already
validates backticked repo paths in `docs/DELIVERY_DOC_INDEX.md`. The new guard
adds a focused assertion that the index text does not contain:

- `.claude/`
- `local-dev-env/`

The check is intentionally narrow. It does not ban mentions in development
records; it only prevents these directories from becoming delivery-index
entries.

## 3. Verification

Commands:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```

Results:

- delivery doc index references: 2 passed
- doc index contracts: 4 passed
- diff whitespace: clean

## 4. Non-Goals

- No cleanup or deletion of `.claude/`.
- No cleanup or deletion of `local-dev-env/`.
- No change to delivery package generation.
- No new ignore rules.
- No commit or push.
