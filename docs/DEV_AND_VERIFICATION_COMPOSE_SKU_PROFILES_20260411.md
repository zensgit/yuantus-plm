# Compose SKU Profiles

## Goal

Land the missing deployment artifacts promised by the PLM / Metasheet packaging plan:

- `base`
- `collab`
- `combined`

The implementation stays pragmatic:

- do not replace the existing Yuantus compose stack
- do not invent a shared runtime between Yuantus and Metasheet
- do add explicit overlay files that map the sales SKU matrix to concrete boot commands

## Design

### Base

`docker-compose.profile-base.yml` is a thin overlay over the existing Yuantus
stack.

It does not fork the runtime. It only pins packaging metadata:

- `YUANTUS_DELIVERY_PROFILE=base`
- `YUANTUS_ENABLE_COLLAB=false`

Command:

```bash
docker compose -f docker-compose.yml -f docker-compose.profile-base.yml up -d --build
```

### Collab

`docker-compose.profile-collab.yml` keeps the same Yuantus stack shape but
turns on the reserved collaboration gate:

- `YUANTUS_DELIVERY_PROFILE=collab`
- `YUANTUS_ENABLE_COLLAB=true`

Command:

```bash
docker compose -f docker-compose.yml -f docker-compose.profile-collab.yml up -d --build
```

This is intentionally a bounded packaging overlay, not a second application
implementation.

### Combined

`docker-compose.profile-combined.yml` keeps Yuantus authoritative and adds a
Metasheet sidecar runtime:

- `metasheet-postgres`
- `metasheet-redis`
- `backend`
- `web`

The combined profile wires Metasheet to Yuantus through environment variables,
not database coupling:

- `PLM_BASE_URL=http://api:7910`
- `PLM_API_MODE=yuantus`
- `PRODUCT_MODE=plm-workbench`

The Metasheet build context is resolved from `METASHEET2_ROOT`, defaulting to
the sibling checkout `../metasheet2`.

Command:

```bash
METASHEET2_ROOT=../metasheet2 \
docker compose -f docker-compose.yml -f docker-compose.profile-combined.yml up -d --build
```

## Verification Assets

Files added:

- `docker-compose.profile-base.yml`
- `docker-compose.profile-collab.yml`
- `docker-compose.profile-combined.yml`
- `scripts/verify_compose_sku_profiles.sh`
- `src/yuantus/meta_engine/tests/test_ci_contracts_compose_sku_profiles.py`

CI protection added:

- compose profile contract test added to `.github/workflows/ci.yml`
- shell syntax gate updated to include `verify_compose_sku_profiles.sh`

## Local Verification

Commands executed:

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_compose_sku_profiles.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py

METASHEET2_ROOT=/path/to/metasheet2 \
  bash scripts/verify_compose_sku_profiles.sh
```

Expected outcome:

- CI contract test passes
- shell syntax gate passes
- compose verifier renders `base`, `collab`, and `combined` successfully

## Why This Shape

This closes the original execution gap without falling into the shared-kernel
trap:

- product packaging is now concrete
- runtime ownership stays separate
- upgrading `base` or `collab` to `combined` remains an overlay change, not a
  PLM data migration
