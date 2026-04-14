# P1 CAD Checkin Queue Binding

Date: 2026-04-14

## Goal

Port the smallest safe CAD checkin queue slice onto the clean `origin/main`
baseline worktree:

1. remove the current `CheckinManager.checkin()` preview stub
2. enqueue canonical `cad_preview` and `cad_geometry` jobs
3. let CAD handlers emit binding hints for the worker post-processor
4. bind derived roles back to `VersionFile`, and project to `ItemFile` for
   current versions

## Scope

Touched files:

- `src/yuantus/meta_engine/services/checkin_service.py`
- `src/yuantus/meta_engine/services/job_worker.py`
- `src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py`
- `src/yuantus/cli.py`
- `src/yuantus/meta_engine/tests/test_checkin_manager.py`
- `src/yuantus/meta_engine/tests/test_cad_checkin_transaction.py`
- `src/yuantus/meta_engine/tests/test_cad_pipeline_version_binding.py`

## What changed

### 1. Checkin now queues real CAD jobs

`CheckinManager.checkin()` no longer does:

- `subprocess.run(["true"])`
- create an empty `.viewable` file

It now:

- uploads the native CAD file
- resolves current `version_id`
- enqueues:
  - `cad_preview`
  - `cad_geometry` with `target_format="glTF"`
- writes these into version properties:
  - `native_file`
  - `cad_conversion_job_ids`

### 2. CAD handlers gained binding wrappers

Added:

- `_enrich_with_derived_files()`
- `cad_preview_with_binding()`
- `cad_geometry_with_binding()`

These wrappers keep the existing handler behavior intact, but append:

```json
{
  "derived_files": [
    {
      "file_id": "<same file container id>",
      "file_role": "preview|geometry",
      "version_id": "<checkin version id>"
    }
  ]
}
```

This matches the current storage model where preview/geometry sidecars still
live on the same `FileContainer`.

### 3. Worker binds derived files after job completion

`JobWorker._execute_job()` now:

- detects `result["derived_files"]`
- calls `VersionFileService.attach_file(...)`
- commits those bindings
- if the bound version is current:
  - calls `sync_version_files_to_item(remove_missing=False)`

This keeps current item-level read models aligned without changing the core
file storage model.

### 4. CLI now registers wrapper handlers

The worker CLI now registers:

- `cad_preview_with_binding`
- `cad_geometry_with_binding`

instead of the raw handlers.

## Verification

### Focused queue/checkin slice

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_checkin_manager.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_transaction.py \
  src/yuantus/meta_engine/tests/test_cad_pipeline_version_binding.py
```

Observed:

- `14 passed, 1 warning`

### Wider related regression

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_job_queue_tx_boundary_contracts.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py
```

Observed:

- `40 passed, 1 warning`

### Syntax check

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/services/checkin_service.py \
  src/yuantus/meta_engine/services/job_worker.py \
  src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py \
  src/yuantus/cli.py
```

Observed:

- passed

### Warning note

The warning is the existing local `urllib3/LibreSSL` environment warning. It is
not introduced by this change.

## Outcome

The clean mainline baseline no longer uses a fake viewable stub for CAD
checkin.

The mainline CAD checkin path is now:

`native upload -> meta_conversion_jobs -> cad_preview/cad_geometry -> job worker -> VersionFile bind -> current ItemFile sync`

## Claude Code CLI

This session did call `Claude Code CLI` in the clean worktree for read-only
sidecar inspection.

Current practical status:

- CLI is authenticated
- short probes can run
- a subsequent longer read-only prompt hit a usage limit window (`resets 6pm`)

So `Claude` is callable, but it should still be treated as best-effort sidecar
support rather than the only execution path for this slice.
