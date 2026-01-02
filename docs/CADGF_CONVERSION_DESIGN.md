# CADGameFusion 2D 转换接入设计（Yuantus）

## 目标

把 CADGameFusion 的 2D CAD（DXF）转换能力接入 Yuantus 的 CAD pipeline，使 PLM 侧能产出：

- `mesh.gltf`（Web 预览几何）
- `mesh.bin`（glTF 二进制缓冲）
- `mesh_metadata.json`（实体索引范围/颜色等）
- `document.json`（CADGameFusion Document JSON）
- `manifest.json`（产物清单）

## 接入点

- 任务入口：`cad_geometry`（`src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py`）
- 新增服务：`CADGFConverterService`（`src/yuantus/meta_engine/services/cadgf_converter_service.py`）
- 数据落点：`FileContainer` 新增字段
  - `cad_document_path`
  - `cad_manifest_path`
  - `cad_metadata_path`

## 数据流（2D DXF）

1) CAD 文件上传 → `FileContainer.system_path` 落库  
2) `cad_geometry` 任务判断扩展名为 `dxf`  
3) 调用 `CADGFConverterService` 执行 `tools/plm_convert.py`  
4) 产物写入本地或上传至 S3  
5) `FileContainer` 更新：
   - `geometry_path` → `mesh.gltf`
   - `cad_manifest_path` → `manifest.json`
   - `cad_document_path` → `document.json`
   - `cad_metadata_path` → `mesh_metadata.json`

## 默认行为

- `/api/v1/cad/import` 未显式传 `create_geometry_job` 时，DXF 默认会排队执行 `cad_geometry`。

## 存储布局

- 本地：`{LOCAL_STORAGE_PATH}/cadgf/{file_id[:2]}/{file_id}/...`
- S3：`cadgf/{file_id[:2]}/{file_id}/...`

## glTF 资产访问

CADGameFusion 的 `manifest.json` 与 glTF 资源位于同一目录。为保证 Web Viewer 能解析资源：

- `GET /api/v1/file/{file_id}/cad_manifest?rewrite=1` 会将 `artifacts.mesh_gltf`、
  `document_json`、`mesh_metadata` 改写为绝对 URL。
- 新增接口：`GET /api/v1/file/{file_id}/cad_asset/{asset_name}` 用于提供
  `mesh.gltf`、`mesh.bin` 等同目录资源。
- `cad_viewer_url` 默认使用 `rewrite=1` 的 manifest URL。

## 新增 API

- `GET /api/v1/file/{file_id}/cad_manifest`
- `GET /api/v1/file/{file_id}/cad_document`
- `GET /api/v1/file/{file_id}/cad_metadata`
- `GET /api/v1/file/{file_id}/cad_asset/{asset_name}`

## File Metadata

- `GET /api/v1/file/{file_id}` will expose `cad_viewer_url` once `cad_manifest_path` exists.
- The viewer URL is built using `YUANTUS_CADGF_ROUTER_BASE_URL`.
- The viewer page will fetch the manifest URL; ensure same-origin routing or allow CORS and public access for CAD preview assets.

## 配置项

通过环境变量（前缀 `YUANTUS_`）配置：

- `CADGF_ROOT`：CADGameFusion 仓库根目录
- `CADGF_CONVERT_SCRIPT`：`tools/plm_convert.py` 的绝对路径（可选）
- `CADGF_CONVERT_CLI`：`convert_cli` 的绝对路径（可选）
- `CADGF_DXF_PLUGIN_PATH`：DXF importer plugin 路径（可选）
- `CADGF_PYTHON_BIN`：执行转换时使用的 Python（可选）
- `CAD_PREVIEW_PUBLIC`：是否开放 CAD 预览资源（可选）
- `CAD_PREVIEW_CORS_ORIGINS`：允许的 CORS 来源列表（可选）

## 限制与约束

- 当前仅支持 `DXF`（`DWG` 需外部转换为 DXF）
- 2D 转换使用 CADGameFusion；3D 仍由 FreeCAD/cadquery/trimesh 处理
