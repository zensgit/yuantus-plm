# 3D CAD Connector Capability Matrix (2026-01-29)

## Goal
Define a clear capability matrix and contract for built-in 3D connectors and provide a baseline for plugin/adapter extensions.

## Contract (Common)
All connectors implement:
- **Identification**: `connector_id`, `cad_format`, `document_type`
- **Routing**: detect by file extension, optional signature tokens
- **Metadata**: attribute extraction is optional (static or key/value)

## Built-in 3D Connectors (Current)
| Connector ID | CAD Format | Extensions | Doc Type | Notes |
| --- | --- | --- | --- | --- |
| `step` | STEP | `.step`, `.stp` | 3d | neutral interchange |
| `iges` | IGES | `.iges`, `.igs` | 3d | neutral interchange |
| `solidworks` | SOLIDWORKS | `.sldprt`, `.sldasm` | 3d | part/assembly |
| `inventor` | INVENTOR | `.ipt`, `.iam` | 3d | part/assembly |
| `nx` | NX | `.prt`, `.asm` | 3d | Siemens NX |
| `creo` | CREO | `.prt`, `.asm` | 3d | PTC Creo/ProE |
| `catia` | CATIA | `.catpart`, `.catproduct` | 3d | Dassault CATIA |
| `solid_edge` | SOLID_EDGE | `.par`, `.psm` | 3d | Solid Edge |
| `rhino` | RHINO | `.3dm` | 3d | Rhino |
| `stl` | STL | `.stl` | 3d | mesh |
| `obj` | OBJ | `.obj` | 3d | mesh |
| `gltf` | GLTF | `.gltf`, `.glb` | 3d | scene |

## 2D Connector Notes
2D connectors (AutoCAD/GStarCAD/ZWCAD/Haochen/Zhongwang) are key/value variants and already declared in `builtin.py`. The 3D list above is the baseline for UI integration and plugin registration.

## Plugin Extension Direction
Future connector plugins must declare:
- `id`, `label`, `cad_format`, `document_type`
- `extensions` and optional `aliases`
- `signature_tokens` for detection hints
- optional attribute extraction hooks

## Verification
- API: `GET /api/v1/cad/connectors`
- Scripts: `scripts/verify_cad_connectors_3d.sh`
