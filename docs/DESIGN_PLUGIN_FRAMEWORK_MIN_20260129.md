# Minimal Plugin Framework Design (2026-01-29)

## Goal
Provide a minimal but complete plugin framework with:
- Registration/discovery
- Health/status visibility
- Capabilities + config exposure

## Components
- **Discovery**: `PLUGIN_DIRS` (default `./plugins`) + manifest (`plugin.json`)
- **Autoload**: `PLUGINS_AUTOLOAD=true` (default)
- **Activation**: `PluginManager` loads and activates plugins
- **Routers**: plugin routers mounted under `/api/v1`

## Health & Capabilities
- Health is represented via `status`, `error_count`, and `last_error` from `/api/v1/plugins`.
- Capabilities are exposed via `/api/v1/plugins/{plugin_id}/config`.

## Minimal Contract
- `plugin.json` defines metadata: `id`, `name`, `version`, `entry_point`, optional `capabilities` and `config_schema`.
- Plugin module exposes a FastAPI `router` (or `get_routers()` / `routers`) for API extension.

## Verification
- `scripts/verify_plugin_framework.sh` validates discovery, status, config schema/capabilities, and demo ping endpoint.
