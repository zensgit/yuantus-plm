# CADGF Router Launchd Design (2026-01-25)

## Goal
Run CADGameFusion router as a persistent background service on macOS using launchd.

## Background
The CADGF router uses native macOS binaries (plugins + convert_cli). Running it as a host service avoids containerizing native dependencies.

## Key Decisions
- **Use LaunchAgent**: runs in user session (`gui/<uid>`).
- **KeepAlive + RunAtLoad**: router restarts automatically.
- **Host-only path**: CADGameFusion copied to `/Users/huazhou/src/CADGameFusion-codex-yuantus` to avoid macOS privacy restrictions on `~/Downloads`.

## Service Definition
- Plist: `/Users/huazhou/Library/LaunchAgents/com.yuantus.cadgf-router.plist`
- Command:
  - `/usr/bin/python3 /Users/huazhou/src/CADGameFusion-codex-yuantus/tools/plm_router_service.py`
  - `--host 127.0.0.1 --port 9000`
  - `--default-plugin /Users/huazhou/src/CADGameFusion-codex-yuantus/build_vcpkg/plugins/libcadgf_json_importer_plugin.dylib`
  - `--default-convert-cli /Users/huazhou/src/CADGameFusion-codex-yuantus/build_vcpkg/tools/convert_cli`
- Logs:
  - `/tmp/cadgf_router_launchd.log`
  - `/tmp/cadgf_router_launchd.err`

## Operational Notes
- To reload:
  - `launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.yuantus.cadgf-router.plist`
  - `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.yuantus.cadgf-router.plist`
  - `launchctl kickstart -k gui/$(id -u)/com.yuantus.cadgf-router`
- Health check: `curl http://127.0.0.1:9000/health`

## Risks
- If CADGameFusion is moved, update plist paths accordingly.
- If macOS privacy prompts appear, ensure the CADGF root is outside protected folders (Desktop/Documents/Downloads).
