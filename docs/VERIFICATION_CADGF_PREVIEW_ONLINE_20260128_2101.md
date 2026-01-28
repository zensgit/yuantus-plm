# Verification - CADGF Preview Online

Date: 2026-01-28

## Goal

Start CADGameFusion router and verify online CAD preview flow.

## Attempted Steps

1) Start CADGF router:

```bash
scripts/run_cadgf_router.sh
```

## Result

SKIP

## Reason

CADGameFusion router entrypoint not found. The script requires
`CADGF_ROOT` pointing to a repo that contains `tools/plm_router_service.py`
plus built artifacts (`build_vcpkg/tools/convert_cli` and
`build_vcpkg/plugins/libcadgf_json_importer_plugin.*`).

Current error:

```
Missing CADGF_ROOT. Set CADGF_ROOT=/path/to/CADGameFusion
```

## Next

Provide a valid CADGameFusion repo path and build outputs, then re-run:

```bash
CADGF_ROOT=/path/to/CADGameFusion \
  scripts/run_cadgf_router.sh

BASE_URL=http://127.0.0.1:7910 \
SAMPLE_FILE=/path/to/sample.dwg \
RUN_CADGF_PREVIEW_ONLINE=1 \
scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```
