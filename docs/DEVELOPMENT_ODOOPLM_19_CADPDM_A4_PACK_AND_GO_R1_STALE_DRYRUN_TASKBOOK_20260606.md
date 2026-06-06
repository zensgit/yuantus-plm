# A4 pack-and-go R1 — Grounding/Scope-lock Taskbook (WP1.3 stale injection + dry-run)

Date: 2026-06-06
Status: **doc-only** scope-lock. **Extend-existing**, NOT greenfield — pack-and-go is
already a ~2333-line plugin. R1 adds two deltas only; no traversal-engine swap. No code
in this doc.

## 1. What A4-R1 is

Two borrow-value deltas on the existing `plugins/yuantus-pack-and-go/main.py`:
1. **WP1.3 drawing-staleness injected into the bundle manifest** (so a packager sees
   which drawings are stale vs their model), and
2. a **dry-run / manifest-first mode** (preview the plan/manifest without building the
   zip), so a packager can validate scope/staleness before committing the artifact.

These reuse capability already built (WP1.3 `needs_update`/provenance; the plugin's own
manifest) and turn it into a pre-flight signal — the "package what's built into a user
action" idea from the CAD-PDM closeout ledger §5.

## 2. As-is (grounded — what already exists, do NOT rebuild)

- **Routes (3):** `POST /plugins/pack-and-go` (`:1858`) supports a **sync zip response**
  and an **async job** mode — only `req.async_flag` builds a `JobService` job (`:1958`);
  otherwise it builds inline and returns a `FileResponse`. Plus `GET /jobs/{job_id}`
  (`:2066`, status) and `GET /jobs/{job_id}/download` (`:2105`). The heavy build
  (file-blob copy + zip at `:1773`) runs inline (sync) or in the worker (async); results
  are cached (`pack_and_go_{cache_key}.zip`).
- **Traversal:** the plugin walks a BOM tree with its **own** `_collect_item_ids`
  (`:748`) / `_flatten_bom_tree` (`:837`); it does **not** call WP1.2
  `RelationshipService.get_relationship_tree`.
- **File packaging:** file-role normalization + export presets (2d/3d/pdf), path
  strategies, collision handling, manifest CSV (`_MANIFEST_CSV_COLUMNS`: `file_id`,
  `filename`, `output_filename`, `file_role`, `document_type`, `path_in_package`,
  `source_version_id`, …), BOM tree/flat JSON.
- **Version locks:** `evaluate_bundle_version_locks` (#570/#588) populates
  `manifest["version_lock_summary"]` (`:1709`) and raises `BundleVersionLockError` →
  409. **`version_lock_summary.stale` = owned + non-current VERSION-lock stale — this is
  NOT CAD drawing staleness.**
- **Gap:** zero `needs_update` / `source_batch_id` / drawing-staleness anywhere in the
  plugin; no dry-run / manifest-only mode.

## 3. Scope-locked decisions (R1)

- **D1 — no traversal-engine swap.** R1 keeps `_collect_item_ids()` /
  `_flatten_bom_tree()` as-is; it does NOT migrate to WP1.2 `get_relationship_tree`.
  (Consolidating onto the WP1.2 API — node budget / cycle guard / occurrence_count — is
  a deliberately-deferred later R, not R1.)
- **D2 — dry-run / manifest-first.** Add a `dry_run` (a.k.a. `manifest_only`) request
  flag. When set, the plugin computes the **plan + manifest** (traversal, file
  resolution, staleness, version-lock summary) and returns it **without generating the
  zip or writing any final artifact**. No `.zip` cache entry is written; no download
  URL is produced. (Open Q-A: sync response vs a job that yields a manifest-only
  result — see §4.)
- **D3 — WP1.3 drawing staleness in the manifest.** Each **drawing-role** file entry
  gains: `needs_update` (bool), `staleness_reason`, `source_batch_id`, and
  `model_import_batch_id` (the model's import batch). A bundle-level
  `drawing_staleness_summary` (counts: total drawings, `needs_update` count, list of
  stale `file_id`s) is added to the manifest. This is a **separate** key from
  `version_lock_summary` — the two staleness notions must never be conflated.
- **D4 — warn, do not exclude.** Stale drawings are **flagged** (manifest + summary) and
  a warning is surfaced; they are **NOT excluded** from the bundle by default. A future
  `exclude_stale_drawings=true` opt-in is deferred to **R2**.
- **D5 — no new route, no version-lock change.** R1 extends the existing `POST` request
  schema + the manifest payload; it adds **no route** (route-count unchanged) and does
  not touch `evaluate_bundle_version_locks` / `version_lock_summary`. Permission stays
  the existing `_current_user`.
- **D6 — staleness source (file-scope-aware).** The WP1.3 fields exist on BOTH
  `ItemFile` and `VersionFile`, so R1 reads them from the **same link the file came
  from** — never mixing version-snapshot staleness with current-`ItemFile` staleness:
  - `file_scope="item"` → read `needs_update`/`source_batch_id` from **`ItemFile`**.
  - `file_scope="version"` → read from **`VersionFile`** (the version snapshot,
    `:1376`); for the version-scope **fallback** items (no version files → the existing
    `ItemFile` fallback at `:1396-1403`) read the corresponding **`ItemFile`**.
  `model_import_batch_id` is batch-read per source item. R1 **reads** these, never
  recomputes provenance (same read-only stance as the `stale-drawings` scan).

## 4. Ratified sub-decisions (locked at taskbook stage — they fix API/manifest contract)

- **Q-A (D2) — RATIFIED: synchronous.** `dry_run=true` returns the plan + manifest
  **synchronously** from `POST`; it does **not** create a job, write a zip, write a cache
  entry, or produce a download URL. Response shape: `{ok, dry_run: true, manifest, plan}`.
- **Q-B (D6) — RATIFIED: direct file-link read.** Read the WP1.3 fields straight off the
  drawing file link (per the file-scope source in D6) and batch-fetch
  `model_import_batch_id` per item. Do **NOT** call
  `CadConsistencyService.get_staleness()` per item (read-only, low N+1, fits the
  `ItemFile`/`VersionFile` links pack-and-go already loads).
- **Q-C (D3) — RATIFIED: both JSON and CSV.** The four staleness columns
  (`needs_update`, `staleness_reason`, `source_batch_id`, `model_import_batch_id`) appear
  in **both** the JSON manifest and the **CSV** manifest (the CSV is what packagers most
  often hand off / review), governed by the existing manifest column selector.

## 5. Verification plan (impl PR, not this doc)

- New tests (dual-registered ci.yml + conftest allowlist; hermetic if they touch release
  rulesets): (1) `dry_run=true` returns `{ok, dry_run: true, manifest, plan}` and writes
  **no** zip / no cache entry / no artifact / no download URL; (2) a stale drawing
  surfaces `needs_update`/`staleness_reason`/`source_batch_id`/`model_import_batch_id` in
  its manifest entry — in **both JSON and CSV** — plus the `drawing_staleness_summary`,
  read from the file-scope-correct link (item→`ItemFile`, version→`VersionFile`, plus the
  version fallback→`ItemFile`); (3) drawing staleness is **distinct from**
  `version_lock_summary.stale` (a version-lock-stale item is not drawing-stale and vice
  versa); (4) default behavior **warns, does not exclude** the stale drawing from the
  bundle; (5) existing pack-and-go behavior (non-dry-run sync/async build, version-lock
  409, manifest CSV) unchanged.
- Route-count **unchanged** (no new route) → no pin bump. Existing
  `test_plugin_pack_and_go*` + `test_pack_and_go_*_contract` stay green.
- DEV/V doc + index; full CI contracts/regression green.

## 6. Sequencing

- **R1 (this):** stale injection (warn) + dry-run/manifest-first.
- **R2 (later, opt-in):** `exclude_stale_drawings=true`; possibly migrate the traversal
  onto WP1.2 `get_relationship_tree` (D1 deferral). A3 workstation checkout remains a
  separate, heavier line (CAD desktop / lock state / native signoff) — after A4.
