# DEV_AND_VERIFICATION_SECURITY_DEFAULTS_PLUGIN_INTEGRATIONS_HARDENING_20260420

## Goal

Continue the April 20 security hardening sequence after the `auth/jobs/freecad` package by closing the next smaller fail-closed surfaces without reopening a repo-wide auth rollout:

1. make plugin loading default-deny unless explicitly enabled
2. require auth for `/api/v1/integrations/health` and redact downstream leakage
3. make the in-repo `cad-extractor` sidecar default to authenticated access

## Code Changes

1. `src/yuantus/config/settings.py`
   - Changed `PLUGINS_AUTOLOAD` default from `true` to `false`.
   - Kept the global application `AUTH_MODE` default unchanged in this package after compatibility sampling showed the broader flip would break existing create-app test flows.
2. `src/yuantus/plugin_manager/runtime.py`
   - Default startup now loads no plugins when autoload is disabled and no allowlist is provided.
   - `PLUGINS_ENABLED` now acts as an explicit allowlist even when autoload is off.
3. `src/yuantus/plugin_manager/worker.py`
   - Worker-side plugin job handler registration now follows the same explicit-allowlist behavior.
4. `src/yuantus/api/routers/integrations.py`
   - Added route-level auth via `Depends(get_current_user_id)`.
   - Removed internal `base_url` exposure.
   - Replaced raw upstream error bodies with redacted diagnostics: `error_code`, `error_type`, optional `status_code`, and `summary`.
5. `services/cad-extractor/app.py`
   - Changed default sidecar auth mode from `disabled` to `required`.
   - Invalid auth mode values now fail closed to `required` instead of reopening to `disabled`.
6. `services/cad-extractor/README.md`
   - Updated the documented default auth mode.
7. `docker-compose.yml`
   - Added `YUANTUS_PLUGINS_AUTOLOAD=${YUANTUS_PLUGINS_AUTOLOAD:-false}` to the API service.
   - Changed `CAD_EXTRACTOR_AUTH_MODE` default from `disabled` to `required`.
   - Kept CAD extractor client token wiring configurable via `YUANTUS_CAD_EXTRACTOR_SERVICE_TOKEN`; did not introduce a new hardcoded default token.
8. `docs/PLUGIN_BOM_PACK_AND_GO.md`
   - Updated plugin autoload guidance to describe the new default-deny posture and allowlist path.
9. `docs/DESIGN_PLUGIN_FRAMEWORK_MIN_20260129.md`
   - Updated the framework design note to match the new default.

## Tests Added

1. `src/yuantus/api/tests/test_integrations_router_security.py`
   - Covers `401`, authenticated success, upstream HTTP error redaction, and upstream request error redaction.
2. `src/yuantus/api/tests/test_plugin_runtime_security.py`
   - Covers plugin default-deny startup and explicit allowlist behavior for both API runtime and worker registration.
3. `src/yuantus/api/tests/test_cad_extractor_security_defaults.py`
   - Covers default-required auth and successful bearer-token access for the sidecar.
4. `src/yuantus/meta_engine/tests/test_ci_contracts_compose_security_defaults.py`
   - Covers compose-level defaults for plugin autoload and CAD extractor auth wiring.

## Verification

Focused regression:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/api/tests/test_integrations_router_security.py \
  src/yuantus/api/tests/test_plugin_runtime_security.py \
  src/yuantus/api/tests/test_cad_extractor_security_defaults.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_compose_security_defaults.py
```

Documentation index contracts:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

Compatibility spot-check after explicitly *not* flipping the global app auth default:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py \
  src/yuantus/meta_engine/tests/test_eco_approval_audit.py \
  src/yuantus/meta_engine/tests/test_p2_dev_observation_smoke.py
```

## Outcome

1. Plugin code is no longer auto-loaded by default on API or worker startup.
2. Operators can still activate a controlled plugin subset through `PLUGINS_ENABLED`.
3. `/api/v1/integrations/health` no longer serves as an anonymous inventory or raw-error reflector.
4. The bundled CAD extractor sidecar now fails closed unless an operator intentionally sets auth mode or token configuration.

## Residual Risks

1. This package does not yet flip the global application `AUTH_MODE` default to `required`; compatibility sampling showed that change needs a broader rollout with existing `create_app()` test harnesses and auth overrides.
2. `JWT_SECRET_KEY` and other compose/default credentials are not yet converted to mandatory secure inputs in this package.
3. Successful downstream integration health payloads are still passed through after authentication; if those payloads later grow sensitive fields, a success-shape allowlist should be added.
