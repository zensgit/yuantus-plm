# DEV & Verification: OdooPLM 19 CAD-PDM A4 pack-and-go R2 (impl)

Date: 2026-06-08

Implements the A4-R2 follow-up on top of A4-R1 (#738) + the manifest-first fix
(#739) + temp-dir test hardening (#742): optional stale-drawing exclusion for
pack-and-go. **Extend-existing** only; no traversal-engine swap, no route, no
migration.

## As built

- `PackAndGoRequest.exclude_stale_drawings` added, default `false`.
- Default `false` preserves A4-R1: stale drawing-role files remain in the
  package and are surfaced through `drawing_staleness_summary` + warnings.
- When `true`, drawing-role files whose file-scope-correct link has
  `needs_update=True` are excluded from:
  - `pack_files` / ZIP payload;
  - `manifest.files`;
  - `manifest.csv`;
  - version-lock evaluation file set (which remains tied to files that actually
    enter the bundle).
- The manifest records the decision without hiding it:
  - `drawing_staleness_summary.excluded = true`
  - `drawing_staleness_summary.excluded_file_ids = [...]`
  - `manifest.excluded_files[]` contains the stale drawing metadata plus
    `excluded_reason="stale_drawing"`.
- The exclusion check happens **before** `_resolve_source_path`, so excluded stale
  drawings are not downloaded even on the non-dry-run ZIP path.
- Cache safety: `exclude_stale_drawings` is included in `_build_cache_payload`,
  so include/exclude requests cannot share a cached ZIP key. Async job payloads
  carry the flag through `model_dump(by_alias=True)` and the async handler passes
  it into `build_pack_and_go_package(...)`.

## Verification

Targeted tests added:

- default warn-not-exclude remains intact;
- default file-id de-duplication remains intact when the same blob is attached
  under multiple roles;
- `exclude_stale_drawings=true` removes stale drawings from `manifest.files`
  while preserving `excluded_file_ids` / `excluded_files`;
- exclusion is role-scoped: if the same FileContainer is attached as both
  `drawing` and `native_cad`, excluding the stale drawing does not hide the
  native CAD role;
- non-dry-run ZIP + manifest CSV omit the excluded stale drawing;
- request serialization includes the flag with default `false`;
- cache payload/key includes the flag and differs between include/exclude modes.

Commands run:

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_plugin_pack_and_go_stale_dryrun.py \
  src/yuantus/meta_engine/tests/test_plugin_pack_and_go_version_lock_wiring.py
# 32 passed
```

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py \
  src/yuantus/meta_engine/tests/test_plugin_pack_and_go_stale_dryrun.py \
  src/yuantus/meta_engine/tests/test_plugin_pack_and_go_version_lock_wiring.py \
  src/yuantus/meta_engine/tests/test_pack_and_go_db_resolver_contract.py \
  src/yuantus/meta_engine/tests/test_pack_and_go_version_lock_contract.py
# 87 passed
```

## Non-goals

- No new route and no Alembic migration.
- No migration to WP1.2 `get_relationship_tree`.
- No A3 workstation checkout.
- No policy beyond the explicit request flag; org-level default/persistence can be
  added later if product asks for it.
