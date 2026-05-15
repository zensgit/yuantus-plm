# Claude Taskbook: Odoo18 Pack-and-Go Version-Lock Bridge Contract R1

Date: 2026-05-15

Type: **Doc-only taskbook.** This document changes no runtime, no schema,
no plugin. It specifies the contract an implementation PR will deliver.
That implementation PR is a **separate, independent opt-in** and is NOT
authorized by merging this taskbook.

## 1. Purpose

The pack-and-go mainline RFC (`docs/DEVELOPMENT_CLAUDE_TASK_ODOO18_PACK_AND_GO_MAINLINE_RFC_20260515.md`,
merged `b427d14`, PR #568) selected **Option C**: do not relocate the
plugin; instead add a small, pure, testable core contract that lets a
caller assert "every document in a bundle is version-pinned and belongs
to its item", reusing the workorder version-lock R1 semantics (PR #565,
`12456d3`).

This taskbook specifies that contract. The goal is the same proven shape
as the consumption MES contract (PR #567, `6973a4c`): a pure module +
drift/round-trip tests, default no-op, no route, no schema, no plugin
rewrite.

## 2. Current Baseline

Evidence (read before implementing):

- Workorder version-lock R1 introduced the ownership invariant in
  `src/yuantus/meta_engine/services/parallel_tasks_service.py`:
  - `_load_owned_version(...)` (≈ line 6130) raises if a version is
    missing or does not belong to its item.
  - `serialize_link(...)` (≈ line 6155) computes `version_locked`,
    `version_belongs_to_item`, `version_is_current` per link.
  These are the semantics to **reuse conceptually** — but they live on
  `WorkorderDocumentLink`, which is the *workorder-doc* abstraction, not
  the pack-and-go bundle abstraction.
- pack-and-go (`plugins/yuantus-pack-and-go/main.py`, 2119 lines)
  assembles bundles from item files via `FileService`. It has a
  `default_file_scope` whose default is `item` and whose `version` enum
  value is the closest existing knob; neither enforces the R1 ownership
  invariant.
- The consumption MES contract
  (`src/yuantus/meta_engine/services/consumption_mes_contract.py`, PR
  #567) is the structural template: a pure module, Pydantic v2 DTO +
  frozen dataclass + pure mapper + drift test, no DB reads, no route.

**Design tension to resolve in this taskbook (not in code yet):**
ownership validation inherently needs to know each document's
`(item_id, version_id, version_belongs_to_item, version_is_locked)`.
A *pure* contract cannot read the DB. Therefore the contract operates
over **already-resolved descriptors** supplied by the caller. Resolving
those descriptors from the DB is explicitly a later, separate opt-in
(the "wiring" step), exactly as the consumption contract deferred actual
ingestion wiring.

## 3. R1 Target Output (for the later, separately opted-in impl PR)

A new pure module, e.g.
`src/yuantus/meta_engine/services/pack_and_go_version_lock_contract.py`,
delivering:

- `BundleDocumentDescriptor` — frozen Pydantic v2 / dataclass record:
  - `document_item_id: str` (non-empty)
  - `document_version_id: str | None`
  - `version_belongs_to_item: bool | None`
  - `version_is_current: bool | None`
  Field names deliberately mirror R1's `serialize_link` output so a
  future resolver can map 1:1 and a drift test can assert alignment.
- `BundleLockReport` — frozen result:
  - `total: int`
  - `locked: int` — defined exactly as R1's `version_lock_summary`:
    `locked = total - len(unlocked) - len(mismatched)`. A
    version-present-but-mismatched descriptor is **not** counted as
    locked. A `stale` descriptor (locked & owned but
    `version_is_current is False`) **still counts as locked** — stale is
    informational only, never subtracted.
  - `unlocked: list[str]` (item ids with no `document_version_id`)
  - `mismatched: list[str]` (`version_belongs_to_item is False`)
  - `stale: list[str]` (`version_is_current is False`, among
    locked & owned descriptors)
  - `ok: bool` (True iff `unlocked` and `mismatched` are both empty)
- `evaluate_bundle_version_locks(descriptors) -> BundleLockReport` —
  **pure** (no DB, no I/O). It always *reports*; it never raises and
  takes no enforcement flag. `ok` is fully determined by
  `unlocked`/`mismatched`, so a `require_locked`-style parameter would be
  semantically inert and is deliberately omitted. The decision to block a
  bundle export is the caller's, made via
  `assert_bundle_version_locks(...)` or future wiring — mirroring how
  R1's `export_pack` made the raise decision at the service edge, not in
  the pure layer.
- `assert_bundle_version_locks(descriptors) -> None` — thin helper that
  raises `ValueError` with the offending ids when
  `evaluate_bundle_version_locks(...).ok is False`. Provided so the
  plugin (later, opt-in) can choose enforcement without re-deriving the
  logic.

Stale handling: surfaced in the report, **never** the basis for `ok`
being False — same deferral the R1 export used (`stale` is informational
in R1, freshness enforcement was explicitly deferred).

## 4. Tests Required (in the later impl PR)

New `test_pack_and_go_version_lock_contract.py`:

- Descriptor validation: empty `document_item_id` rejected.
- All-locked descriptors → `ok=True`, `locked == total`, empty
  unlocked/mismatched.
- A descriptor with `document_version_id=None` → counted `unlocked`,
  `ok=False`.
- A descriptor with `version_belongs_to_item=False` → counted
  `mismatched`, `ok=False`.
- A descriptor with `version_is_current=False` but locked & owned →
  counted `stale`, still counted in `locked`, **`ok=True`** (stale never
  fails the gate, never subtracted from `locked`).
- `locked == total - len(unlocked) - len(mismatched)` holds for a mixed
  bundle (assert the arithmetic explicitly).
- `evaluate_bundle_version_locks(...)` never raises and accepts no
  enforcement flag; `assert_bundle_version_locks` raises `ValueError`
  listing offending ids when not ok, returns None when ok.
- Purity guard: the module imports nothing from `database` /
  `Session` / the plugin; a test asserts `evaluate_*` has no DB
  parameter.
- **Drift test**: `BundleDocumentDescriptor` field names are a subset of
  the keys produced by R1
  `WorkorderDocumentPackService.serialize_link` (introspected), so if R1
  renames `version_belongs_to_item` / `version_is_current` the bridge
  contract fails loudly rather than silently diverging.

Doc-index trio stays green for the impl PR's DEV/verification MD.

## 5. Verification Commands (for the impl PR)

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

## 6. Non-Goals (hard boundaries for the impl PR)

- **No route.** No endpoint, no change to `/plugins/pack-and-go`.
- **No plugin rewrite.** `plugins/yuantus-pack-and-go/main.py` is not
  edited in R1. The plugin opting into the check is a *later* step.
- **No table / migration / tenant baseline / schema change.**
- **No DB reads in the contract.** It operates on caller-supplied
  descriptors only. Resolving descriptors from the DB is a separate
  opt-in.
- **No feature flag / production setting.** Nothing executes unless a
  test or a (future, opted-in) caller invokes it.
- **No change to workorder version-lock R1 or the consumption MES
  contract.** This is a new, independent pure module.
- **No mainlining of the plugin** — that was explicitly rejected by the
  RFC.
- `.claude/` and `local-dev-env/` stay out of git.

## 7. Decision Gate / Handoff

This taskbook is doc-only. The implementation PR (pure module + tests +
DEV/verification MD) is owned by Claude Code **only after this taskbook
is merged AND a separate explicit opt-in is given**, on branch:

`feat/odoo18-pack-and-go-version-lock-bridge-contract-r1-20260515`

Follow-ups, each its own separate opt-in (explicitly NOT in R1):

- A DB resolver that builds `BundleDocumentDescriptor`s from real item/
  file/version rows.
- Wiring the plugin to call `assert_bundle_version_locks` (opt-in,
  default unchanged).
- Any export-blocking behaviour in pack-and-go itself.

## 8. Reviewer Focus

- Is the contract genuinely pure (no DB/Session import, no I/O)?
- Does the drift test actually introspect R1 `serialize_link` keys, not
  a hard-coded list (so divergence fails loudly)?
- Is "stale never fails the gate" preserved, consistent with R1?
- Did anything edit the plugin, add a route, or change R1 / the
  consumption contract? It must not.
- Is the descriptor-vs-DB-resolver split clearly deferred to a separate
  opt-in?
