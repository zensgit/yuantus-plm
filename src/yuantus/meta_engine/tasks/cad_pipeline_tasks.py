from __future__ import annotations

import base64
import io
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from yuantus.config import get_settings
from yuantus.integrations.cad_ml import CadMLClient
from yuantus.integrations.dedup_vision import DedupVisionClient
from yuantus.meta_engine.models.file import ConversionStatus, FileContainer
from yuantus.meta_engine.services.cad_converter_service import CADConverterService
from yuantus.meta_engine.services.file_service import FileService


def _vault_base_path() -> str:
    return str(Path(get_settings().LOCAL_STORAGE_PATH).resolve())


def _is_s3_storage() -> bool:
    """Check if storage type is S3."""
    return get_settings().STORAGE_TYPE == "s3"


def _download_to_temp(file_service: FileService, system_path: str, suffix: str = "") -> str:
    """
    Download a file from storage to a temporary local file.
    Returns the path to the temporary file.
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        file_service.download_file(system_path, temp_file)
        temp_file.close()
        return temp_file.name
    except Exception:
        temp_file.close()
        os.unlink(temp_file.name)
        raise


def _upload_from_local(file_service: FileService, local_path: str, storage_key: str) -> str:
    """
    Upload a local file to storage.
    Returns the storage key.
    """
    with open(local_path, "rb") as f:
        return file_service.upload_file(f, storage_key)


def cad_preview(payload: Dict[str, Any], session: Session) -> Dict[str, Any]:
    file_id = str(payload.get("file_id") or "").strip()
    if not file_id:
        raise ValueError("Missing file_id")

    file_container: Optional[FileContainer] = session.get(FileContainer, file_id)
    if not file_container:
        raise ValueError("File not found")

    if file_container.preview_path:
        return {
            "ok": True,
            "file_id": file_container.id,
            "preview_path": file_container.preview_path,
            "preview_url": f"/api/v1/file/{file_container.id}/preview",
            "skipped": True,
        }

    vault_base_path = _vault_base_path()
    file_service = FileService()
    use_s3 = _is_s3_storage()

    # For S3: download source to temp, process, upload result back
    temp_source_path: Optional[str] = None
    temp_preview_path: Optional[str] = None

    try:
        if use_s3:
            # Download source file to temp directory
            ext = file_container.get_extension() or ""
            temp_source_path = _download_to_temp(
                file_service, file_container.system_path, suffix=f".{ext}" if ext else ""
            )
            source_path = temp_source_path
        else:
            converter = CADConverterService(session, vault_base_path=vault_base_path)
            source_path = converter._get_file_path(file_container)

        # Generate preview (works on local file)
        converter = CADConverterService(session, vault_base_path=vault_base_path)
        preview_abs = converter._generate_preview(source_path, file_container)
        temp_preview_path = preview_abs  # Mark for cleanup

        if use_s3:
            # Upload preview to S3
            preview_key = f"previews/{file_container.id[:2]}/{file_container.id}.png"
            _upload_from_local(file_service, preview_abs, preview_key)
            file_container.preview_path = preview_key
        else:
            # Local storage: store relative path
            rel = os.path.relpath(preview_abs, vault_base_path)
            file_container.preview_path = preview_abs if rel.startswith("..") else rel

        if file_container.conversion_status:
            file_container.conversion_status = ConversionStatus.COMPLETED.value
        session.add(file_container)
        session.flush()

        return {
            "ok": True,
            "file_id": file_container.id,
            "preview_path": file_container.preview_path,
            "preview_url": f"/api/v1/file/{file_container.id}/preview",
        }
    finally:
        # Cleanup temp files
        if use_s3:
            if temp_source_path and os.path.exists(temp_source_path):
                os.unlink(temp_source_path)
            if temp_preview_path and os.path.exists(temp_preview_path):
                os.unlink(temp_preview_path)


def cad_geometry(payload: Dict[str, Any], session: Session) -> Dict[str, Any]:
    file_id = str(payload.get("file_id") or "").strip()
    if not file_id:
        raise ValueError("Missing file_id")

    target_format = str(payload.get("target_format") or "gltf").strip().lower()
    if target_format not in {"obj", "gltf", "glb", "stl"}:
        target_format = "gltf"

    file_container: Optional[FileContainer] = session.get(FileContainer, file_id)
    if not file_container:
        raise ValueError("File not found")

    if file_container.geometry_path:
        return {
            "ok": True,
            "file_id": file_container.id,
            "geometry_path": file_container.geometry_path,
            "geometry_url": f"/api/v1/file/{file_container.id}/geometry",
            "skipped": True,
        }

    ext = (file_container.get_extension() or "").lower()
    # Already viewable formats: just point geometry to the original file.
    if ext in {"stl", "obj", "gltf", "glb"}:
        file_container.geometry_path = file_container.system_path
        file_container.conversion_status = ConversionStatus.COMPLETED.value
        session.add(file_container)
        session.flush()
        return {
            "ok": True,
            "file_id": file_container.id,
            "geometry_path": file_container.geometry_path,
            "geometry_url": f"/api/v1/file/{file_container.id}/geometry",
            "note": "already_viewable",
        }

    vault_base_path = _vault_base_path()
    file_service = FileService()
    use_s3 = _is_s3_storage()

    # For S3: download source to temp, process, upload result back
    temp_source_path: Optional[str] = None
    temp_geometry_path: Optional[str] = None

    try:
        if use_s3:
            # Download source file to temp directory
            source_ext = file_container.get_extension() or ""
            temp_source_path = _download_to_temp(
                file_service, file_container.system_path, suffix=f".{source_ext}" if source_ext else ""
            )
            source_path = temp_source_path
        else:
            converter = CADConverterService(session, vault_base_path=vault_base_path)
            source_path = converter._get_file_path(file_container)

        converter = CADConverterService(session, vault_base_path=vault_base_path)

        try:
            geometry_abs = converter._convert_to_geometry(
                source_path, file_container, target_format
            )
            temp_geometry_path = geometry_abs  # Mark for cleanup if not same as source

            # Determine final geometry path
            if os.path.abspath(geometry_abs) == os.path.abspath(source_path):
                # Converter returned original file (no conversion needed)
                file_container.geometry_path = file_container.system_path
            elif use_s3:
                # Upload geometry to S3
                geometry_key = f"geometry/{file_container.id[:2]}/{file_container.id}.{target_format}"
                _upload_from_local(file_service, geometry_abs, geometry_key)
                file_container.geometry_path = geometry_key
            else:
                # Local storage: store relative path
                rel = os.path.relpath(geometry_abs, vault_base_path)
                file_container.geometry_path = geometry_abs if rel.startswith("..") else rel

            file_container.conversion_status = ConversionStatus.COMPLETED.value
            file_container.conversion_error = None
            session.add(file_container)
            session.flush()
            return {
                "ok": True,
                "file_id": file_container.id,
                "geometry_path": file_container.geometry_path,
                "geometry_url": f"/api/v1/file/{file_container.id}/geometry",
                "target_format": target_format,
            }
        except Exception as e:
            # Avoid retry storms when converters are not installed; mark result as a handled failure.
            file_container.conversion_status = ConversionStatus.FAILED.value
            file_container.conversion_error = str(e)
            session.add(file_container)
            session.flush()
            return {
                "ok": False,
                "file_id": file_container.id,
                "error": str(e),
                "target_format": target_format,
            }
    finally:
        # Cleanup temp files
        if use_s3:
            if temp_source_path and os.path.exists(temp_source_path):
                os.unlink(temp_source_path)
            # Only cleanup geometry if it's different from source and was uploaded
            if temp_geometry_path and temp_geometry_path != temp_source_path and os.path.exists(temp_geometry_path):
                os.unlink(temp_geometry_path)


def cad_dedup_vision(payload: Dict[str, Any], session: Session) -> Dict[str, Any]:
    file_id = str(payload.get("file_id") or "").strip()
    if not file_id:
        raise ValueError("Missing file_id")

    mode = str(payload.get("mode") or "balanced").strip().lower()
    user_name = str(payload.get("user_name") or "anonymous").strip() or "anonymous"

    file_container: Optional[FileContainer] = session.get(FileContainer, file_id)
    if not file_container:
        raise ValueError("File not found")

    file_service = FileService()
    use_s3 = _is_s3_storage()
    temp_path: Optional[str] = None

    try:
        if use_s3:
            # Download to temp for S3
            ext = file_container.get_extension() or ""
            temp_path = _download_to_temp(
                file_service, file_container.system_path, suffix=f".{ext}" if ext else ""
            )
            local_path = temp_path
        else:
            local_path = file_service.get_local_path(file_container.system_path)
            if not local_path or not os.path.exists(local_path):
                return {"ok": False, "file_id": file_id, "error": "Local file not available"}

        client = DedupVisionClient()
        try:
            search = client.search_sync(
                file_path=local_path,
                mode=mode,
                max_results=5,
            )
        except Exception as e:
            return {"ok": False, "file_id": file_id, "error": str(e)}

        indexed: Optional[Dict[str, Any]] = None
        if bool(payload.get("index", False)):
            try:
                indexed = client.index_add_sync(
                    file_path=local_path, user_name=user_name, upload_to_s3=False
                )
            except Exception as e:
                indexed = {"ok": False, "error": str(e)}

        return {"ok": True, "file_id": file_id, "search": search, "indexed": indexed}
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


def cad_ml_vision(payload: Dict[str, Any], session: Session) -> Dict[str, Any]:
    file_id = str(payload.get("file_id") or "").strip()
    if not file_id:
        raise ValueError("Missing file_id")

    file_container: Optional[FileContainer] = session.get(FileContainer, file_id)
    if not file_container:
        raise ValueError("File not found")

    vault_base_path = _vault_base_path()
    file_service = FileService()
    use_s3 = _is_s3_storage()

    preview_path = file_container.preview_path
    if not preview_path:
        # Ensure we always have something to analyze (placeholder preview is fine).
        _ = cad_preview({"file_id": file_id}, session)
        # Refresh from DB
        session.refresh(file_container)
        preview_path = file_container.preview_path

    if not preview_path:
        return {"ok": False, "file_id": file_id, "error": "Preview not available"}

    temp_preview_path: Optional[str] = None

    try:
        if use_s3:
            # Download preview from S3 to temp
            temp_preview_path = _download_to_temp(file_service, preview_path, suffix=".png")
            preview_abs = temp_preview_path
        else:
            preview_abs = preview_path
            if not os.path.isabs(preview_abs):
                preview_abs = os.path.join(vault_base_path, preview_abs)

            if not os.path.exists(preview_abs):
                return {"ok": False, "file_id": file_id, "error": "Preview file missing"}

        with open(preview_abs, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("ascii")

        client = CadMLClient()
        try:
            resp = client.vision_analyze_sync(
                image_base64=image_b64,
                include_description=True,
                include_ocr=True,
            )
            return {"ok": True, "file_id": file_id, "vision": resp}
        except Exception as e:
            return {"ok": False, "file_id": file_id, "error": str(e)}
    finally:
        if temp_preview_path and os.path.exists(temp_preview_path):
            os.unlink(temp_preview_path)

