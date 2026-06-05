# DEV & Verification: OdooPLM 19 CAD-PDM WP1.3 2D/3D Staleness (v0 impl)

Date: 2026-06-05

Implements WP1.3 v0 from
`ODOOPLM_BORROW_DEVELOPMENT_PLAN_AND_TODO_20260604.md`, under the locked design in
`DEVELOPMENT_WP1_3_CAD_2D3D_STALENESS_GROUNDING_TASKBOOK_20260605.md` (D1–D6) and
the WP1.0 representation decision. Single PR (semantic closed loop), committed in
the S1–S6 order below. No assembly-tree scan (deferred to after WP1.2, D6).

## Design recap (locked)

- **Provenance, not raw batch inequality.** A drawing pins the model batch it was
  last co-saved with (`source_batch_id`); stale only when the model moved past
  that pin. `stale ⟺ source_batch_id != model.import_batch_id` (both set). Null
  provenance → `unknown` (fail-open). Batch ids are opaque/unordered, so plain
  inequality is never used.
- **Selector:** model M = `document_type="3d" ∧ file_role="native_cad"`; drawing
  D = `document_type="2d" ∧ file_role ∈ {drawing, native_cad}` (excludes
  preview/geometry/printout/attachment). `document_type` is authoritative.
- **Timestamps advisory only** (`time_hint`); never drive `needs_update`.
- **ItemFile = current authority;** recompute writes ItemFile + the CURRENT
  version's VersionFile mirror only (never historical snapshots).

## S1–S6 (subtasks, as built)

- **S1 migration + model columns** — 5 columns on `ItemFile`
  (`src/yuantus/meta_engine/models/file.py`) and `VersionFile`
  (`version/models.py`): `import_batch_id`, `source_batch_id`, `needs_update`,
  `staleness_reason`, `staleness_checked_at`. Unique index
  `uq_item_file_role (item_id, file_id, file_role)` on `meta_item_files`
  (declared in model `__table_args__` for SQLite/create_all AND in the migration
  for PG). Migration `migrations/versions/wp13_cad_stale_001_*.py` (additive,
  idempotent, **deterministic dedup before the unique index**, PG/SQLite
  portable). Sync carries the fields: `sync_item_files_to_version` (all 5),
  `sync_version_files_to_item` (**provenance only** — never historical verdict, and
  **guarded to the item's current version** — raises `VersionFileError` otherwise,
  so a historical snapshot can never overwrite current provenance),
  `copy_files_to_version` (all 5) in `version/file_service.py`.
- **S2 import_batch_id** — `CadImportRequest.import_batch_id`,
  `cad_import_router` form param + echo (`CadImportResponse.import_batch_id`),
  `_attach_to_item` writes it. **Lookup hardened to `(item_id, file_id,
  file_role)`; role-overwrite branch removed** (same in `file_attachment_router`).
  `import_file` defaults a batch per call and triggers `recompute` (non-fatal).
- **S3 checkin alignment (RATIFIED, required)** — `_CheckinFileService.upload_file`
  derives `document_type` via the shared `_resolve_cad_metadata` (was OTHER);
  `CheckinManager.checkin` materializes a `native_cad` ItemFile (so the model is
  selectable as M), accepts `import_batch_id`, and triggers `recompute`.
- **S4 CadConsistencyService** — `services/cad_consistency_service.py`: selector,
  provenance pin, verdict (`no_model`/`unknown`/`up_to_date`/`model_moved_on`/
  `ambiguous`), current-version mirror, flip-only `CadDrawingStalenessChangedEvent`
  via `enqueue_event`.
- **S5 API** — `web/cad_consistency_router.py`: `GET /cad/items/{id}/staleness`,
  `POST /cad/items/{id}/staleness/recompute` (item-centered, zero traversal, no
  `/documents/...`); registered in `src/yuantus/api/app.py`. RBAC via
  `MetaPermissionService` (get / update).
- **S6 tests + wiring** — `tests/test_cad_2d3d_staleness.py` (17 tests); added to
  `ci.yml` contracts list (sorted) + `conftest.py` no-DB allowlist; route-count
  pin bumped 699 → 701; DEV/V indexed in `DELIVERY_DOC_INDEX.md`. **v0 adds no
  `YUANTUS_*` setting.**

## Review hardening folded in

- Round 1 (provenance): replaced unsound "different batch ⇒ stale" with provenance
  pin; added the `source_batch_id` write rule; timestamps advisory only.
- Round 2: checkin alignment ratified (H1/T16); drawing selector allow-list
  (H2/T13/T17); VersionFile snapshot not polluted by recompute (M3/T15);
  drawing-only regeneration stays stale (M4/T14).
- DB-level unique index `(item_id, file_id, file_role)` + dedup pre-step; both
  ItemFile writers fixed (`_attach_to_item`, `file_attachment_router`); T18.

## Verification (Python 3.11 venv from `/opt/homebrew/bin/python3.11`, requirements.lock)

- `pytest src/yuantus/meta_engine/tests/test_cad_2d3d_staleness.py` → **17 passed**
  (T1, T2, T2b, T3, T5, T11, T12, T13, T14, T15, T16 unit + real-checkin
  integration, T17, T18, **T18a CAD-import writer path, T18b file-attachment
  writer path, non-current-version sync guard**).
- Affected-area regression (cad_import_service, checkin_manager, cad_import_lock_guards,
  cad_checkin_transaction, file_attachment_router_contracts,
  file_router_attachment_lock_guards, version_file_checkout_service,
  pdm_relationship_types, ci_yml_test_list_order, migration_table_coverage,
  version_file_binding_viewer_uniqueness) → **74 passed**.
  - Updated 1 obsolete test: `test_existing_item_file_link_role_update_checks_old_and_new_roles`
    asserted the removed role-overwrite path; rewritten to the new same-triple
    update contract (`test_existing_same_triple_link_updates_batch_without_role_overwrite`).
- `alembic upgrade head` on a fresh SQLite → applies through `wp13_cad_stale_001`;
  both tables carry all 5 columns; `uq_item_file_role` present.
- Route-count contract reconciled (701 = 699 + 2 staleness routes).
- `git diff --check` clean.

## Known limitations (v0, accepted)

- **Recompute is triggered on import/checkin and via the explicit POST endpoint —
  NOT automatically on a version switch / ECO-apply.** `sync_version_files_to_item`
  carries provenance (`import_batch_id`/`source_batch_id`) back from the **current**
  version (a non-current version now hard-raises, so current provenance can't be
  polluted by a historical snapshot), but the derived verdict (`needs_update`) on
  the current `ItemFile` is only refreshed on the next import/checkin or an explicit
  `POST .../recompute`. So immediately after an ECO-apply/version-switch,
  `GET /staleness` may show the pre-switch verdict until one of those runs. Wiring
  an auto-recompute into the version-switch path is a follow-up (cheap; deferred to
  keep v0's blast radius
  to the import/checkin seam).

## Non-goals (unchanged)

- No assembly-tree `stale-drawings` scan (after WP1.2 traversal).
- No pack-and-go (WP3.1); no relationship-type changes (WP1.1 fixed).
