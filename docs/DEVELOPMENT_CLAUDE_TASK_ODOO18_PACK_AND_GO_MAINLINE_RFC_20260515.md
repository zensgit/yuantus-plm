# Claude Taskbook (RFC): Odoo18 Pack-and-Go Mainline Evaluation

Date: 2026-05-15

Type: **Doc-only RFC / decision evaluation.** This document changes no
runtime, no schema, no plugin. Its only output is a recommendation plus a
decision gate. Any code that follows is a separate, independently
opted-in implementation taskbook.

## 1. Purpose

R2 candidate #4 (`docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260514.md` §四.4,
§3.2 row `plm_pack_and_go`) is explicitly a **strategy question, not a
from-scratch build**: pack-and-go already exists as a plugin. The gap
analysis defers the real decision to "先做主线化评估（小 RFC）". This
RFC is that evaluation.

It answers one question: **what, if anything, should change about how
pack-and-go is delivered?** It deliberately does not implement any of the
options.

## 2. Current Reality (grounded)

Evidence (read before forming an opinion):

- `plugins/yuantus-pack-and-go/plugin.json` — id `yuantus-pack-and-go`,
  `plugin_type: extension`, category `files`, version `0.1.0`. Rich
  `config_schema`: `max_files` (default 2000), `max_bytes`,
  `cache_enabled` (default false), `cache_ttl_minutes`,
  `progress_interval`, `default_export_type`
  (`all|2d|3d|pdf|2dpdf|3dpdf|3d2d`), `default_path_strategy` (8
  strategies), `default_filename_mode` (4 modes), `default_file_scope`
  (`item|version`).
- `plugins/yuantus-pack-and-go/main.py` — 2119 lines. FastAPI router
  `prefix="/plugins/pack-and-go"`, three endpoints:
  - `POST /plugins/pack-and-go` (enqueue a pack job)
  - `GET /plugins/pack-and-go/jobs/{job_id}` (status)
  - `GET /plugins/pack-and-go/jobs/{job_id}/download` (download bundle)
  Capabilities (from `plugin.json`): zip export, manifest, `bom_tree`,
  `bom_flat` (csv/jsonl), 8 path strategies, 4 filename modes,
  item/version file scope, filters (`item_ids`, `item_types`, `states`,
  `extensions`), async, cache. Depends on
  `yuantus.meta_engine.services.file_service.FileService` and the item/
  file models.
- Loader posture: `src/yuantus/config/settings.py:397` —
  `PLUGINS_AUTOLOAD` default **False**;
  `src/yuantus/config/settings.py:401` — `PLUGINS_ENABLED` default
  **empty**. `src/yuantus/plugin_manager/worker.py:21` /
  `runtime.py:19` — a plugin loads only if explicitly in
  `PLUGINS_ENABLED` (or autoload is explicitly turned on). So pack-and-go
  is **already default-off** and unreachable in a default deployment.
- Adjacent mainline capability that overlaps conceptually: the workorder
  version-lock R1 (PR #565, merged `12456d3`) added a
  `document_version_id` pointer + `version_belongs_to_item` on workorder
  document links and a `version_lock_summary` export. pack-and-go's
  `default_file_scope` defaults to `item`; its `version` enum value is
  the closest existing knob, but even that is **not** the same as the R1
  version-lock invariant.

**Key fact for the decision:** the capability is built and substantial.
The question is purely about *delivery surface and lifecycle*, not about
whether to write a BOM archiver.

## 3. The Decision

Should pack-and-go remain a default-off plugin, or move toward mainline,
and if so, how does it relate to the workorder version-lock invariant?

The gap analysis named four candidate directions. This RFC evaluates them
against the owner's stated ordering: **low-risk, default-off, testable**.

### Option A — Status quo (keep as default-off plugin)

Keep `plugins/yuantus-pack-and-go/` exactly as is. Document it as a
supported optional extension; add nothing to core.

- **Risk**: none (no change).
- **Default-off**: yes, by construction (`PLUGINS_AUTOLOAD=False`).
- **Testability**: plugin already shippable; no core test surface added.
- **Cost**: zero.
- **Downside**: pack-and-go's bundle does **not** honour the workorder
  version-lock invariant. A supplier hand-off produced via pack-and-go
  can still include a non-pinned / stale document version, which is
  exactly the risk class R1 was created to close. Status quo leaves that
  gap open for the pack-and-go path.

### Option B — Mainline the plugin into core (default-off route)

Move the pack-and-go capability into `meta_engine` as a first-class
service + router, mounted but gated behind a default-off setting (mirror
the R1 "default off" boundary).

- **Risk**: medium. 2119 lines of plugin logic crossing into core; the
  plugin currently builds its own router, auth shims, db shims. A move
  invites scope creep and a large diff.
- **Default-off**: achievable via a setting, but a core route is a
  larger attack/maintenance surface than an unloaded plugin.
- **Testability**: would need a full contract suite mirroring the plugin
  behaviour. Large.
- **Cost**: high. Not a "small slice".

### Option C — Bridge: keep plugin, add a thin version-lock-aware contract in core

Do **not** move pack-and-go. Instead define (later, separate opt-in) a
small, pure, testable contract in core that the plugin (and any future
mainline exporter) can call to assert "every document in this bundle is
version-pinned and belongs to its item", reusing the R1
`document_version_id` / `version_belongs_to_item` semantics. The plugin
opts in to the check; default behaviour unchanged.

- **Risk**: low. Pure contract function + tests, no route, no plugin
  rewrite, no schema. Same shape as the just-shipped consumption MES
  contract (`6973a4c`).
- **Default-off**: yes — the check is opt-in; nothing changes unless a
  caller requests `require_locked_versions`-style enforcement.
- **Testability**: high — pure function + drift tests, exactly the
  pattern the owner has now validated twice (#565, #567).
- **Cost**: low, single small slice.
- **Downside**: does not "mainline" pack-and-go; it closes the
  version-lock gap for bundles without relocating the plugin.

### Option D — New core `bom_archive` endpoint

Build a fresh minimal BOM-archive exporter in core, ignoring the plugin.

- **Risk**: medium-high. Re-implements a 2119-line capability badly or
  partially; two divergent archivers.
- **Default-off**: a new route is default-reachable unless gated.
- **Testability**: large new surface.
- **Cost**: high; explicitly the "not from scratch" anti-goal the gap
  analysis warned against.
- **Verdict**: rejected on first principles — duplicates existing work.

## 4. Evaluation Summary

| Option | Risk | Default-off | Testable (small) | Closes version-lock gap | Cost |
|---|---|---|---|---|---|
| A status quo | none | yes | n/a | **no** | zero |
| B mainline plugin | medium | gated | large | partial | high |
| C bridge contract | low | yes | **yes** | **yes** | low |
| D new bom_archive | med-high | gated | large | maybe | high |

## 5. Recommendation

**Adopt Option C as the next slice; treat Option A as the fallback if no
appetite for any change.**

Rationale:

- It is the only option that is simultaneously low-risk, default-off,
  and a genuinely small testable slice — matching the owner's ordering
  and the pattern proven by #565 and #567.
- It closes the one substantive downside of the status quo (pack-and-go
  bundles ignoring the R1 version-lock invariant) without a 2000-line
  core migration.
- It keeps the plugin as the delivery vehicle, so no plugin lifecycle /
  surface decision is forced now.
- Mainlining the plugin wholesale (Option B) and a parallel
  `bom_archive` (Option D) are both rejected as not "small, low-risk"
  and, for D, as duplicative.

Explicitly **not** recommended now: relocating plugin code into core,
adding any default-on route, or changing pack-and-go's existing
behaviour.

## 6. Proposed Decision Gate

This RFC does not authorize code. The next step is the owner's choice:

1. **Accept Option C** → a separate doc-only implementation taskbook is
   written for "pack-and-go version-lock bridge contract" (pure
   contract + drift/round-trip tests, no route, no plugin rewrite, no
   schema), then a separately opted-in implementation PR — same
   two-step cadence as #566→#567.
2. **Accept Option A** → record "pack-and-go stays a default-off plugin;
   version-lock gap accepted for the plugin path" as a closed decision;
   move to the next R2 candidate.
3. **Request deeper analysis** on B or D before deciding.

No implementation branch is created until the owner picks 1, 2, or 3.

## 7. Non-Goals (this RFC)

- No code, no plugin edit, no route, no schema, no setting change.
- No decision is made *by* this document; it only recommends.
- No contact with workorder version-lock R1 runtime or the consumption
  MES contract.
- `.claude/` and `local-dev-env/` stay out of git.

## 8. Reviewer Focus

- Is the "current reality" section accurate (plugin default-off, three
  endpoints, capability set)? Spot-check `plugin.json` and the loader
  defaults.
- Is the recommendation honest that Option C does *not* mainline the
  plugin — i.e. is the title "mainline evaluation" still fair? (It is:
  the evaluation's conclusion is "do not mainline now, bridge instead".)
- Does any option smuggle in a default-on surface or a runtime change?
  It must not.
- Is the decision gate genuinely deferring the code opt-in to the owner?
