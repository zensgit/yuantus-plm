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

## 存储布局

- 本地：`{LOCAL_STORAGE_PATH}/cadgf/{file_id[:2]}/{file_id}/...`
- S3：`cadgf/{file_id[:2]}/{file_id}/...`

## glTF 资产访问

CADGameFusion 输出的 glTF 默认引用 `mesh.bin`。为避免路径解析问题：

- 转换完成后自动将 `buffers[].uri` 改写为 `asset/mesh.bin`
- 新增接口：`GET /api/v1/file/{file_id}/asset/{asset_name}`

这样 `GET /api/v1/file/{file_id}/geometry` 返回的 glTF 可以正确加载 `asset/mesh.bin`。

## 新增 API

- `GET /api/v1/file/{file_id}/cad_manifest`
- `GET /api/v1/file/{file_id}/cad_document`
- `GET /api/v1/file/{file_id}/cad_metadata`
- `GET /api/v1/file/{file_id}/asset/{asset_name}`

## 配置项

通过环境变量（前缀 `YUANTUS_`）配置：

- `CADGF_ROOT`：CADGameFusion 仓库根目录
- `CADGF_CONVERT_SCRIPT`：`tools/plm_convert.py` 的绝对路径（可选）
- `CADGF_CONVERT_CLI`：`convert_cli` 的绝对路径（可选）
- `CADGF_DXF_PLUGIN_PATH`：DXF importer plugin 路径（可选）
- `CADGF_PYTHON_BIN`：执行转换时使用的 Python（可选）

## 限制与约束

- 当前仅支持 `DXF`（`DWG` 需外部转换为 DXF）
- 2D 转换使用 CADGameFusion；3D 仍由 FreeCAD/cadquery/trimesh 处理
