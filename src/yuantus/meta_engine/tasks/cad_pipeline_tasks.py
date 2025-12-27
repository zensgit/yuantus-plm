from __future__ import annotations

import base64
import io
import logging
import os
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from yuantus.config import get_settings
from yuantus.integrations.cad_ml import CadMLClient
from yuantus.integrations.dedup_vision import DedupVisionClient
from yuantus.meta_engine.models.file import ConversionStatus, FileContainer
from yuantus.meta_engine.services.cad_converter_service import CADConverterService
from yuantus.meta_engine.services.cadgf_converter_service import (
    CADGFConverterService,
    CadgfConversionError,
)
from yuantus.meta_engine.services.cad_service import CadService, normalize_cad_attributes
from yuantus.meta_engine.services.file_service import FileService
from yuantus.meta_engine.services.job_errors import JobFatalError

logger = logging.getLogger(__name__)


def _vault_base_path() -> str:
    return str(Path(get_settings().LOCAL_STORAGE_PATH).resolve())


def _is_s3_storage() -> bool:
    """Check if storage type is S3."""
    return get_settings().STORAGE_TYPE == "s3"


def _build_authorization_header(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    token = str(token).strip()
    if not token:
        return None
    if token.lower().startswith("bearer "):
        return token
    return f"Bearer {token}"


def _is_missing_storage_error(exc: Exception) -> bool:
    if isinstance(exc, FileNotFoundError):
        return True
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        code = response.get("Error", {}).get("Code", "")
        if str(code) in {"404", "NoSuchKey", "NotFound"}:
            return True
    return False


def _ensure_source_exists(file_service: FileService, system_path: str) -> None:
    if not system_path:
        raise JobFatalError("Missing system_path for source file")
    exists = file_service.file_exists(system_path)
    if not exists:
        raise JobFatalError(f"Source file missing: {system_path}")


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
    except Exception as exc:
        temp_file.close()
        os.unlink(temp_file.name)
        if _is_missing_storage_error(exc):
            raise JobFatalError(f"Source file missing: {system_path}") from exc
        raise


def _upload_from_local(file_service: FileService, local_path: str, storage_key: str) -> str:
    """
    Upload a local file to storage.
    Returns the storage key.
    """
    with open(local_path, "rb") as f:
        return file_service.upload_file(f, storage_key)


def _cadgf_storage_prefix(file_id: str) -> str:
    return f"cadgf/{file_id[:2]}/{file_id}"


def _cadgf_output_dir(vault_base_path: str, file_id: str) -> str:
    return os.path.join(vault_base_path, _cadgf_storage_prefix(file_id))


def _is_nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def _merge_missing(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base or {})
    for key, value in (extra or {}).items():
        if key not in merged or merged[key] in (None, ""):
            merged[key] = value
    return merged


def _append_source(existing: Optional[str], addition: str) -> Optional[str]:
    if not addition:
        return existing
    if not existing:
        return addition
    parts = [part.strip() for part in existing.split("+") if part.strip()]
    if addition not in parts:
        parts.append(addition)
    return "+".join(parts) if parts else addition


def _extract_ocr_attributes(vision_resp: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(vision_resp, dict):
        return {}
    ocr = vision_resp.get("ocr")
    if not isinstance(ocr, dict):
        return {}
    title_block = ocr.get("title_block")
    if not isinstance(title_block, dict):
        return {}

    lower = {str(k).lower(): v for k, v in title_block.items()}

    def _pick(*keys: str) -> Optional[str]:
        for key in keys:
            value = title_block.get(key)
            if value is None:
                value = lower.get(key.lower())
            if isinstance(value, str):
                value = value.strip()
            if _is_nonempty(value):
                return str(value)
        return None

    attrs: Dict[str, Any] = {}
    drawing_no = _pick("drawing_number", "drawing_no", "drawingno")
    material = _pick("material")
    part_name = _pick("part_name", "partname", "name")
    revision = _pick("revision", "rev", "version")
    weight = _pick("weight", "mass", "net_weight", "gross_weight")

    if drawing_no:
        attrs["drawing_no"] = drawing_no
        attrs["part_number"] = drawing_no
    if material:
        attrs["material"] = material
    if part_name:
        attrs["part_name"] = part_name
    if revision:
        attrs["revision"] = revision
    if weight:
        attrs["weight"] = weight

    return attrs


def _normalize_ocr_payload(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    return {
        "dimensions": raw.get("dimensions") or [],
        "symbols": raw.get("symbols") or [],
        "title_block": raw.get("title_block") or {},
        "fallback_level": raw.get("fallback_level"),
        "confidence": raw.get("confidence"),
    }


def cad_preview(payload: Dict[str, Any], session: Session) -> Dict[str, Any]:
    file_id = str(payload.get("file_id") or "").strip()
    if not file_id:
        raise JobFatalError("Missing file_id")

    file_container: Optional[FileContainer] = session.get(FileContainer, file_id)
    if not file_container:
        raise JobFatalError("File not found")

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
    _ensure_source_exists(file_service, file_container.system_path)
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

        preview_bytes: Optional[bytes] = None
        ext = (file_container.get_extension() or "").lower()
        settings = get_settings()
        authorization = _build_authorization_header(
            payload.get("authorization") or settings.CAD_ML_SERVICE_TOKEN
        )
        if ext in {"dwg", "dxf"} and settings.CAD_ML_BASE_URL:
            try:
                client = CadMLClient()
                preview_bytes = client.render_cad_preview_sync(
                    file_path=source_path,
                    filename=file_container.filename,
                    authorization=authorization,
                )
            except Exception as exc:
                logger.warning("CAD ML render preview failed: %s", exc)
                preview_bytes = None

        if preview_bytes:
            if use_s3:
                preview_key = f"previews/{file_container.id[:2]}/{file_container.id}.png"
                file_service.upload_file(io.BytesIO(preview_bytes), preview_key)
                file_container.preview_path = preview_key
            else:
                converter = CADConverterService(session, vault_base_path=vault_base_path)
                output_dir = converter._get_generated_dir(file_container)
                preview_filename = f"{Path(file_container.filename).stem}_preview.png"
                preview_abs = os.path.join(output_dir, preview_filename)
                with open(preview_abs, "wb") as handle:
                    handle.write(preview_bytes)
                rel = os.path.relpath(preview_abs, vault_base_path)
                file_container.preview_path = preview_abs if rel.startswith("..") else rel
            temp_preview_path = None
        else:
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
        raise JobFatalError("Missing file_id")

    target_format = str(payload.get("target_format") or "gltf").strip().lower()
    if target_format not in {"obj", "gltf", "glb", "stl"}:
        target_format = "gltf"

    file_container: Optional[FileContainer] = session.get(FileContainer, file_id)
    if not file_container:
        raise JobFatalError("File not found")

    if file_container.geometry_path:
        return {
            "ok": True,
            "file_id": file_container.id,
            "geometry_path": file_container.geometry_path,
            "geometry_url": f"/api/v1/file/{file_container.id}/geometry",
            "skipped": True,
        }

    file_service = FileService()
    _ensure_source_exists(file_service, file_container.system_path)

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

    if ext in {"dxf", "dwg"}:
        vault_base_path = _vault_base_path()
        use_s3 = _is_s3_storage()

        temp_source_path: Optional[str] = None
        temp_output_dir: Optional[str] = None

        try:
            if use_s3:
                source_ext = file_container.get_extension() or ""
                temp_source_path = _download_to_temp(
                    file_service,
                    file_container.system_path,
                    suffix=f".{source_ext}" if source_ext else "",
                )
                source_path = temp_source_path
                temp_output_dir = tempfile.mkdtemp(prefix="cadgf_")
                output_dir = temp_output_dir
            else:
                local_source = file_service.get_local_path(file_container.system_path)
                source_path = local_source or os.path.join(
                    vault_base_path, file_container.system_path
                )
                output_dir = _cadgf_output_dir(vault_base_path, file_container.id)

            if ext != "dxf":
                raise CadgfConversionError(
                    "CADGF conversion supports DXF only; convert DWG to DXF first."
                )

            cadgf = CADGFConverterService()
            artifacts = cadgf.convert(source_path, output_dir, extension=ext)

            if not artifacts.mesh_gltf_path:
                raise CadgfConversionError(
                    "CADGF conversion did not produce mesh.gltf"
                )

            if use_s3:
                prefix = _cadgf_storage_prefix(file_container.id)

                def _upload(name: str, path: Path) -> str:
                    storage_key = f"{prefix}/{name}"
                    _upload_from_local(file_service, str(path), storage_key)
                    return storage_key

                file_container.cad_manifest_path = _upload(
                    "manifest.json", artifacts.manifest_path
                )
                file_container.cad_document_path = (
                    _upload("document.json", artifacts.document_path)
                    if artifacts.document_path
                    else None
                )
                file_container.cad_metadata_path = (
                    _upload("mesh_metadata.json", artifacts.mesh_metadata_path)
                    if artifacts.mesh_metadata_path
                    else None
                )
                if artifacts.mesh_bin_path:
                    _upload("mesh.bin", artifacts.mesh_bin_path)
                file_container.geometry_path = _upload(
                    "mesh.gltf", artifacts.mesh_gltf_path
                )
            else:
                def _rel(path: Path) -> str:
                    rel = os.path.relpath(path, vault_base_path)
                    return str(path) if rel.startswith("..") else rel

                file_container.cad_manifest_path = _rel(artifacts.manifest_path)
                file_container.cad_document_path = (
                    _rel(artifacts.document_path)
                    if artifacts.document_path
                    else None
                )
                file_container.cad_metadata_path = (
                    _rel(artifacts.mesh_metadata_path)
                    if artifacts.mesh_metadata_path
                    else None
                )
                file_container.geometry_path = _rel(artifacts.mesh_gltf_path)

            file_container.conversion_status = ConversionStatus.COMPLETED.value
            file_container.conversion_error = None
            session.add(file_container)
            session.flush()
            return {
                "ok": True,
                "file_id": file_container.id,
                "geometry_path": file_container.geometry_path,
                "geometry_url": f"/api/v1/file/{file_container.id}/geometry",
                "cad_manifest_url": (
                    f"/api/v1/file/{file_container.id}/cad_manifest"
                    if file_container.cad_manifest_path
                    else None
                ),
                "cad_document_url": (
                    f"/api/v1/file/{file_container.id}/cad_document"
                    if file_container.cad_document_path
                    else None
                ),
                "cad_metadata_url": (
                    f"/api/v1/file/{file_container.id}/cad_metadata"
                    if file_container.cad_metadata_path
                    else None
                ),
                "target_format": "gltf",
            }
        except Exception as e:
            file_container.conversion_status = ConversionStatus.FAILED.value
            file_container.conversion_error = str(e)
            session.add(file_container)
            session.flush()
            return {
                "ok": False,
                "file_id": file_container.id,
                "error": str(e),
                "target_format": "gltf",
            }
        finally:
            if use_s3:
                if temp_source_path and os.path.exists(temp_source_path):
                    os.unlink(temp_source_path)
                if temp_output_dir and os.path.exists(temp_output_dir):
                    shutil.rmtree(temp_output_dir)

    vault_base_path = _vault_base_path()
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
        raise JobFatalError("Missing file_id")

    mode = str(payload.get("mode") or "balanced").strip().lower()
    user_name = str(payload.get("user_name") or "anonymous").strip() or "anonymous"

    file_container: Optional[FileContainer] = session.get(FileContainer, file_id)
    if not file_container:
        raise JobFatalError("File not found")

    file_service = FileService()
    _ensure_source_exists(file_service, file_container.system_path)
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
        settings = get_settings()
        authorization = _build_authorization_header(
            payload.get("authorization") or settings.DEDUP_VISION_SERVICE_TOKEN
        )
        try:
            search = client.search_sync(
                file_path=local_path,
                mode=mode,
                max_results=5,
                authorization=authorization,
            )
        except Exception as e:
            return {"ok": False, "file_id": file_id, "error": str(e)}

        indexed: Optional[Dict[str, Any]] = None
        if bool(payload.get("index", False)):
            try:
                indexed = client.index_add_sync(
                    file_path=local_path,
                    user_name=user_name,
                    upload_to_s3=False,
                    authorization=authorization,
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
        raise JobFatalError("Missing file_id")

    file_container: Optional[FileContainer] = session.get(FileContainer, file_id)
    if not file_container:
        raise JobFatalError("File not found")

    vault_base_path = _vault_base_path()
    file_service = FileService()
    use_s3 = _is_s3_storage()

    preview_path = file_container.preview_path
    preview_is_source = False
    if preview_path:
        if use_s3:
            if not file_service.file_exists(preview_path):
                file_container.preview_path = None
                session.add(file_container)
                session.flush()
                preview_path = None
        else:
            preview_abs = preview_path
            if not os.path.isabs(preview_abs):
                preview_abs = os.path.join(vault_base_path, preview_abs)
            if not os.path.exists(preview_abs):
                file_container.preview_path = None
                session.add(file_container)
                session.flush()
                preview_path = None

    if not preview_path and file_container.file_type in {"png", "jpg", "jpeg"}:
        if file_service.file_exists(file_container.system_path):
            preview_path = file_container.system_path
            preview_is_source = True

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
            suffix = ".png"
            if preview_is_source:
                ext = file_container.get_extension() or ""
                if ext:
                    suffix = f".{ext}"
            temp_preview_path = _download_to_temp(file_service, preview_path, suffix=suffix)
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
        settings = get_settings()
        authorization = _build_authorization_header(
            payload.get("authorization") or settings.CAD_ML_SERVICE_TOKEN
        )
        try:
            resp = client.vision_analyze_sync(
                image_base64=image_b64,
                include_description=True,
                include_ocr=True,
                authorization=authorization,
            )
            if not isinstance(resp.get("ocr"), dict):
                ocr_provider = payload.get("ocr_provider")
                try:
                    ocr_raw = client.ocr_extract_sync(
                        file_path=preview_abs,
                        filename=os.path.basename(preview_abs),
                        provider=str(ocr_provider).strip() if ocr_provider else None,
                        authorization=authorization,
                    )
                    if isinstance(ocr_raw, dict) and ocr_raw.get("success"):
                        resp["ocr"] = _normalize_ocr_payload(ocr_raw)
                except Exception:
                    pass
            ocr_attrs = normalize_cad_attributes(_extract_ocr_attributes(resp))
            if ocr_attrs:
                existing = dict(file_container.cad_attributes or {})
                merged = normalize_cad_attributes(_merge_missing(existing, ocr_attrs))
                if merged != existing:
                    file_container.cad_attributes = merged
                    file_container.cad_attributes_updated_at = datetime.utcnow()
                    file_container.cad_attributes_source = _append_source(
                        file_container.cad_attributes_source, "ocr"
                    )
                    session.add(file_container)
                    session.flush()
            return {
                "ok": True,
                "file_id": file_id,
                "vision": resp,
                "ocr_attributes": ocr_attrs,
            }
        except Exception as e:
            return {"ok": False, "file_id": file_id, "error": str(e)}
    finally:
        if temp_preview_path and os.path.exists(temp_preview_path):
            os.unlink(temp_preview_path)


def cad_extract(payload: Dict[str, Any], session: Session) -> Dict[str, Any]:
    file_id = str(payload.get("file_id") or "").strip()
    if not file_id:
        raise JobFatalError("Missing file_id")

    file_container: Optional[FileContainer] = session.get(FileContainer, file_id)
    if not file_container:
        raise JobFatalError("File not found")

    cad_service = CadService(session)
    file_service = FileService()
    attributes, source = cad_service.extract_attributes_for_file(
        file_container, file_service=file_service, return_source=True
    )

    file_container.cad_attributes = dict(attributes or {})
    file_container.cad_attributes_source = source
    file_container.cad_attributes_updated_at = datetime.utcnow()
    session.add(file_container)
    session.flush()

    return {
        "ok": True,
        "file_id": file_container.id,
        "cad_format": file_container.cad_format,
        "cad_connector_id": file_container.cad_connector_id,
        "extracted_attributes": attributes,
        "source": source,
    }
