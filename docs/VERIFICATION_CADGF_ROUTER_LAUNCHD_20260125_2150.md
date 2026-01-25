# CADGF Router Launchd Verification (2026-01-25 21:50 +0800)

## Steps
1. Copy CADGameFusion to `/Users/huazhou/src/CADGameFusion-codex-yuantus`.
2. Update launchd plist paths to `/Users/huazhou/src/CADGameFusion`.
3. Reload launchd service:
   - `launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.yuantus.cadgf-router.plist`
   - `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.yuantus.cadgf-router.plist`
   - `launchctl kickstart -k gui/$(id -u)/com.yuantus.cadgf-router`
4. Health check:
   - `curl http://127.0.0.1:9000/health`

## Result
- status: `ok`
- router: `http://127.0.0.1:9000`
- evidence: health response returned 200 with `status=ok`.
