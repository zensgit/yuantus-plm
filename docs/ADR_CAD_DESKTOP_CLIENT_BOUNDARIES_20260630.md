# ADR: CAD Desktop Client Boundaries

Date: 2026-06-30

## Decision

The AutoCAD desktop package keeps the legacy `CADDedupPlugin` assembly and bundle identity for the drawing deduplication plugin. Yuantus PLM material-sync functionality is exposed as `YuantusPlugin` at the user-facing command/ribbon/package level.

New material commands use the `YUANTUS*` prefix:

- `YUANTUSPROFILES`
- `YUANTUSCOMPOSE`
- `YUANTUSPUSH`
- `YUANTUSPULL`
- `YUANTUSASSIST`

The existing `PLMMAT*` commands remain compatibility aliases for existing scripts, validation guides, and trained operators.

## Runtime Boundary

- `CADDedupPlugin` remains the in-process CAD adapter. It owns AutoCAD commands, WPF diff UI, DWG field extraction, and DWG field write-back.
- `yuantus-cad-helper` is the local Yuantus PLM gateway. It owns PLM login state, bearer-token storage, local-token authorization, helper audit rows, and PLM HTTP forwarding.
- `YuantusCadHelperBridge` remains a thin Lisp/NETLOAD bridge for non-AutoCAD hosts. It does not parse Yuantus business payloads and does not write DWG files.

## Transport Rule

Yuantus material-sync calls should go through helper whenever the upstream service is the Yuantus PLM `cad-material-sync` plugin.

The AutoCAD material client now uses helper for:

- `/material/profiles`
- `/material/profiles/{profileId}`
- `/material/compose`
- `/material/validate`
- `/diff/preview`
- `/sync/inbound`
- `/sync/outbound`
- `/material/assistant/resolve`
- `/material/assistant/create`
- `/audit/apply-result`

`DedupApiClient.CheckDuplicateAsync` remains a legacy direct path for now. Do not move it to helper until the upstream owner is ratified, because current evidence shows `/api/dedup/check` is not a normal PLM `cad-material-sync` endpoint and may belong to a separate dedup-vision service/auth seam.

## Build Rule

The legacy AutoCAD project may continue to target .NET Framework v4.6/v4.8, but clean checkout builds must not rely on local-only `Directory.Build.props` / `Directory.Build.targets` rewrites. Because the AutoCAD project is a legacy non-SDK WPF project and `Yuantus.Cad.Shared` is SDK-style, the committed build boundary links the `Yuantus.Cad.Shared` source files directly into `CADDedupPlugin.csproj` for the AutoCAD assembly, excluding Shared's own `AssemblyInfo` plus generated `obj` and `bin` files. SDK-style helper, detector, bridge, and tests continue to use the normal `ProjectReference` to `Yuantus.Cad.Shared.csproj`.

## Security Rule

Helper should remain a narrow local gateway, not a generic proxy. New helper routes require:

- loopback-only access,
- local-token and protocol-header protection,
- PLM session/bearer checks before forwarding,
- explicit route names rather than arbitrary upstream paths,
- tests proving no token or Authorization header is echoed through payloads.
