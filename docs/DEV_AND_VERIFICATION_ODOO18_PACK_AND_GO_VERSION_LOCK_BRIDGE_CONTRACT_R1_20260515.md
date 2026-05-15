# Odoo18 Pack-and-Go Version-Lock Bridge Contract R1 — Development and Verification

Date: 2026-05-15

## 1. Goal

Implement R1 of the pack-and-go version-lock bridge contract taskbook
(`docs/DEVELOPMENT_CLAUDE_TASK_ODOO18_PACK_AND_GO_VERSION_LOCK_BRIDGE_CONTRACT_20260515.md`,
merged `9001707`), which is RFC #568 **Option C**: do not mainline the
pack-and-go plugin; add a small pure core contract that asserts a bundle
is version-pinned and owned, reusing the workorder version-lock R1
semantics (PR #565, `12456d3`).

R1 is **pure and default no-op**: a contract module + tests + this MD.
No route, no plugin edit, no schema, no DB reads, no flag. Nothing runs
unless a test (or a future, separately opted-in caller) invokes it.

## 2. Scope

### Added

- `src/yuantus/meta_engine/services/pack_and_go_version_lock_contract.py`
- `src/yuantus/meta_engine/tests/test_pack_and_go_version_lock_contract.py`
- `docs/DEV_AND_VERIFICATION_ODOO18_PACK_AND_GO_VERSION_LOCK_BRIDGE_CONTRACT_R1_20260515.md`

### Modified

- `docs/DELIVERY_DOC_INDEX.md` (one index line)

The plugin (`plugins/yuantus-pack-and-go/`), routers, ORM models,
workorder version-lock R1, and the consumption MES contract are
**unchanged**.

## 3. Contract

### 3.1 `BundleDocumentDescriptor` (Pydantic v2, frozen, `extra="forbid"`)

| Field | Type | Notes |
|---|---|---|
| `document_item_id` | `str` | stripped, non-empty (validator) |
| `document_version_id` | `str \| None` | absence ⇒ unlocked |
| `version_belongs_to_item` | `bool \| None` | explicit `False` ⇒ mismatched; `None` is not a mismatch |
| `version_is_current` | `bool \| None` | explicit `False` ⇒ stale; `None` is not stale |

Field names mirror the keys of R1
`WorkorderDocumentPackService.serialize_link` so a future DB resolver
can map 1:1; a drift test enforces this.

### 3.2 `BundleLockReport` (frozen dataclass)

`total, locked, unlocked, mismatched, stale, ok`.

- `locked = total - len(unlocked) - len(mismatched)` — exactly R1's
  `version_lock_summary`. A mismatched descriptor is **not** locked. A
  stale descriptor (locked & owned, not current) **still counts as
  locked** — stale is never subtracted.
- `ok = (not unlocked) and (not mismatched)`. Stale never affects `ok`.
- **Empty bundle is vacuously `ok=True`** (`total=0`, `locked=0`) by
  design — `ok` means "no version-lock violations found", not "work was
  done". A caller that must reject an empty bundle (e.g. a filter that
  produced zero documents) is responsible for that precondition before
  calling the contract; the contract intentionally does not conflate
  "empty" with "violation".

### 3.3 Functions

- `evaluate_bundle_version_locks(descriptors) -> BundleLockReport` —
  pure, no DB/I-O, **never raises**, takes **no enforcement flag**
  (`require_locked` was rejected in review as semantically inert since
  `ok` is fully determined by `unlocked`/`mismatched`).
- `assert_bundle_version_locks(descriptors) -> None` — thin enforcement
  wrapper: returns `None` when `ok`, else raises `ValueError` listing the
  offending unlocked + mismatched item ids. Stale-only bundles do not
  raise.

Classification precedence mirrors R1 `export_pack`: no version →
`unlocked` (mismatch not also checked); version present but
`version_belongs_to_item is False` → `mismatched`; locked & owned but
`version_is_current is False` → `stale`.

## 4. Test Matrix

`src/yuantus/meta_engine/tests/test_pack_and_go_version_lock_contract.py`
(test groups; counts are a point-in-time snapshot and grow as cases are
added):

- **Descriptor validation**: empty id rejected, id stripped, frozen +
  `extra=forbid`.
- **Classification**: all-locked ok; missing version → unlocked;
  foreign version → mismatched; stale counts as locked & does not fail
  the gate; unlocked-precedence-over-mismatch; mismatch-precedence-over-
  stale; `belongs=None`/`current=None` are not violations; empty bundle
  trivially ok.
- **`locked` arithmetic** explicitly asserted for a mixed bundle
  (`locked == total - len(unlocked) - len(mismatched)`).
- **Report/raise split**: `evaluate` signature is exactly
  `(descriptors)` (no flag) and never raises; `assert` returns `None`
  when ok, raises listing offending ids otherwise, and does not raise on
  stale-only.
- **Purity guard**: an AST walk of the module asserts it imports nothing
  from `yuantus.database` / `sqlalchemy` / `file_service` /
  `parallel_tasks_service` / `plugins`; `evaluate` has no DB parameter.
- **Drift guard**: introspects R1
  `WorkorderDocumentPackService.serialize_link` (via a fake link with
  `document_version_id=None`, so the session is never touched) and
  asserts every `BundleDocumentDescriptor` field exists in its key set
  — a rename in R1 fails this test loudly.

## 5. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_pack_and_go_version_lock_contract.py
```

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/services/pack_and_go_version_lock_contract.py
git diff --check
```

No alembic / tenant-baseline — the contract adds no schema.

Observed as of 2026-05-15: contract tests all passed; doc-index trio
passed; py_compile clean; `git diff --check` clean.

## 6. Non-Goals (reaffirmed from taskbook §6)

No route; no plugin edit; no table / migration / tenant baseline / schema;
no DB reads in the contract; no feature flag / production setting; no
change to workorder version-lock R1 or the consumption MES contract; no
mainlining of the plugin (RFC-rejected). `.claude/` and `local-dev-env/`
stay out of git.

## 7. Follow-ups (each its own separate opt-in)

- A DB resolver that builds `BundleDocumentDescriptor`s from real item /
  file / version rows.
- Wiring the pack-and-go plugin to call `assert_bundle_version_locks`
  (opt-in, default behaviour unchanged).
- Any export-blocking behaviour inside pack-and-go itself.
