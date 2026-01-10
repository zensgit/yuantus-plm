from __future__ import annotations

import json
import os
import re
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.orm import Session
    from yuantus.meta_engine.models.file import FileContainer, ItemFile
    from yuantus.meta_engine.models.item import Item
else:
    Session = Any

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.context import get_request_context
from yuantus.meta_engine.services.file_service import FileService

router = APIRouter(prefix="/plugins/pack-and-go", tags=["plugins-pack-and-go"])


def _get_db():
    from yuantus.database import get_db

    yield from get_db()


def _current_user(
    user: CurrentUser = Depends(get_current_user),
):
    return user

_DEFAULT_FILE_ROLES = (
    "native_cad",
    "attachment",
    "printout",
    "geometry",
    "drawing",
)
_DEFAULT_DOCUMENT_TYPES = ("2d", "3d", "pr", "other")


class PackAndGoRequest(BaseModel):
    item_id: str = Field(..., description="Root item id")
    depth: int = Field(default=-1, description="BOM depth (-1 for full)")
    file_roles: Optional[List[str]] = None
    document_types: Optional[List[str]] = None
    include_previews: bool = Field(default=False)
    include_printouts: bool = Field(default=True)
    include_geometry: bool = Field(default=True)
    async_flag: bool = Field(default=False, alias="async")


class PackAndGoJobResponse(BaseModel):
    ok: bool
    job_id: str
    status_url: str


@dataclass
class PackAndGoFile:
    file_id: str
    filename: str
    file_role: str
    document_type: Optional[str]
    cad_format: Optional[str]
    size: int
    path_in_package: str
    source_item_id: str
    source_item_number: str
    source_path: str


@dataclass
class PackAndGoResult:
    zip_path: Path
    zip_name: str
    manifest: Dict[str, Any]
    file_count: int
    total_bytes: int


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    return value.strip() if value else default


def _sanitize_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned or "item"


def _normalize_file_roles(
    file_roles: Optional[Sequence[str]],
    *,
    include_previews: bool,
    include_printouts: bool,
    include_geometry: bool,
) -> List[str]:
    roles = [r.strip().lower() for r in (file_roles or _DEFAULT_FILE_ROLES) if r]
    role_set = set(roles)
    if include_previews:
        role_set.add("preview")
    if include_printouts:
        role_set.add("printout")
    if include_geometry:
        role_set.add("geometry")
    return sorted(role_set)


def _normalize_document_types(document_types: Optional[Sequence[str]]) -> List[str]:
    types = [t.strip().lower() for t in (document_types or _DEFAULT_DOCUMENT_TYPES) if t]
    return sorted(set(types))


def _build_package_path(item_number: str, file_role: str, filename: str) -> str:
    safe_item = _sanitize_component(item_number)
    safe_role = _sanitize_component(file_role)
    safe_name = Path(filename).name
    return f"{safe_item}/{safe_role}/{safe_name}"


def _resolve_item_number(item: Item) -> str:
    props = item.properties or {}
    return (
        props.get("item_number")
        or props.get("part_number")
        or props.get("doc_number")
        or item.id
    )


def _collect_item_ids(tree: Dict[str, Any]) -> List[str]:
    ids: List[str] = []

    def _walk(node: Dict[str, Any]) -> None:
        node_id = node.get("id")
        if node_id and node_id not in ids:
            ids.append(node_id)
        for child_entry in node.get("children", []) or []:
            child = child_entry.get("child") or {}
            _walk(child)

    _walk(tree)
    return ids


def _resolve_source_path(
    file_service: FileService,
    file: FileContainer,
    temp_dir: Path,
) -> Tuple[str, Optional[Path]]:
    local_path = file_service.get_local_path(file.system_path)
    if local_path and os.path.exists(local_path):
        return local_path, None

    temp_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename).suffix or ""
    temp_path = temp_dir / f"{file.id}{suffix}"
    with open(temp_path, "wb") as handle:
        file_service.download_file(file.system_path, handle)
    return str(temp_path), temp_path


def _prune_old_outputs(output_dir: Path, retention_minutes: int) -> None:
    if retention_minutes <= 0:
        return
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=retention_minutes)
    for entry in output_dir.glob("pack_and_go_*.zip"):
        try:
            stat = entry.stat()
        except OSError:
            continue
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            try:
                entry.unlink()
            except OSError:
                continue


def build_pack_and_go_package(
    session: Session,
    *,
    item_id: str,
    depth: int,
    file_roles: Sequence[str],
    document_types: Sequence[str],
    include_previews: bool,
    include_printouts: bool,
    include_geometry: bool,
    output_dir: Path,
    file_service: Optional[FileService] = None,
) -> PackAndGoResult:
    from sqlalchemy.orm import joinedload
    from yuantus.meta_engine.models.file import ItemFile
    from yuantus.meta_engine.models.item import Item
    from yuantus.meta_engine.services.bom_service import BOMService

    bom_service = BOMService(session)
    bom_tree = bom_service.get_bom_structure(item_id, levels=depth)

    file_service = file_service or FileService()
    item_ids = _collect_item_ids(bom_tree)
    items = (
        session.query(Item)
        .filter(Item.id.in_(item_ids))
        .all()
    )
    item_by_id = {item.id: item for item in items}

    item_files = (
        session.query(ItemFile)
        .options(joinedload(ItemFile.file))
        .filter(ItemFile.item_id.in_(item_ids))
        .all()
    )

    normalized_roles = _normalize_file_roles(
        file_roles,
        include_previews=include_previews,
        include_printouts=include_printouts,
        include_geometry=include_geometry,
    )
    normalized_types = _normalize_document_types(document_types)

    max_files = _env_int("YUANTUS_PACKGO_MAX_FILES", 2000)
    max_bytes = _env_int("YUANTUS_PACKGO_MAX_BYTES", 0)

    temp_dir = Path(tempfile.mkdtemp(prefix="yuantus_packgo_"))
    temp_paths: List[Path] = []
    pack_files: List[PackAndGoFile] = []
    missing_files: List[Dict[str, Any]] = []
    seen_files: set[str] = set()

    for item_file in item_files:
        file = item_file.file
        if not file or not file.id:
            continue
        if file.id in seen_files:
            continue

        file_role = (item_file.file_role or "").lower()
        if file_role not in normalized_roles:
            continue

        document_type = (file.document_type or "").lower()
        if document_type and document_type not in normalized_types:
            continue

        if not file.filename or not file.system_path:
            continue

        if not file_service.file_exists(file.system_path):
            missing_files.append(
                {
                    "file_id": file.id,
                    "filename": file.filename,
                    "file_role": file_role,
                    "source_item_id": item_file.item_id,
                }
            )
            continue

        source_item = item_by_id.get(item_file.item_id)
        source_item_number = _resolve_item_number(source_item) if source_item else item_file.item_id
        package_path = _build_package_path(source_item_number, file_role, file.filename)
        source_path, temp_path = _resolve_source_path(file_service, file, temp_dir)
        if temp_path:
            temp_paths.append(temp_path)

        size = int(file.file_size or 0)
        if not size:
            try:
                size = int(Path(source_path).stat().st_size)
            except OSError:
                size = 0

        pack_files.append(
            PackAndGoFile(
                file_id=file.id,
                filename=file.filename,
                file_role=file_role,
                document_type=document_type or None,
                cad_format=file.cad_format,
                size=size,
                path_in_package=package_path,
                source_item_id=item_file.item_id,
                source_item_number=source_item_number,
                source_path=source_path,
            )
        )
        seen_files.add(file.id)

        if max_files > 0 and len(pack_files) > max_files:
            raise HTTPException(status_code=413, detail="pack-and-go max files exceeded")

    total_bytes = sum(entry.size for entry in pack_files)
    if max_bytes > 0 and total_bytes > max_bytes:
        raise HTTPException(status_code=413, detail="pack-and-go max bytes exceeded")

    output_dir.mkdir(parents=True, exist_ok=True)
    root_item = item_by_id.get(item_id)
    root_number = _resolve_item_number(root_item) if root_item else item_id
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    zip_name = f"pack_and_go_{_sanitize_component(root_number)}_{timestamp}.zip"
    zip_path = output_dir / zip_name

    manifest = {
        "root_item_id": item_id,
        "root_item_number": root_number,
        "depth": depth,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "file_count": len(pack_files),
        "total_bytes": total_bytes,
        "files": [
            {
                "file_id": entry.file_id,
                "filename": entry.filename,
                "file_role": entry.file_role,
                "document_type": entry.document_type,
                "cad_format": entry.cad_format,
                "size": entry.size,
                "path_in_package": entry.path_in_package,
                "source_item_id": entry.source_item_id,
                "source_item_number": entry.source_item_number,
            }
            for entry in pack_files
        ],
        "missing_files": missing_files,
    }

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for entry in pack_files:
            zipf.write(entry.source_path, entry.path_in_package)
        zipf.writestr(
            "manifest.json",
            json.dumps(manifest, ensure_ascii=True, indent=2),
        )

    for temp_path in temp_paths:
        try:
            temp_path.unlink()
        except OSError:
            continue
    try:
        temp_dir.rmdir()
    except OSError:
        pass

    return PackAndGoResult(
        zip_path=zip_path,
        zip_name=zip_name,
        manifest=manifest,
        file_count=len(pack_files),
        total_bytes=total_bytes,
    )


def _build_job_payload(req: PackAndGoRequest, *, user_id: Optional[str]) -> Dict[str, Any]:
    ctx = get_request_context()
    payload = req.model_dump(by_alias=True)
    payload.update(
        {
            "tenant_id": ctx.tenant_id,
            "org_id": ctx.org_id,
            "user_id": user_id,
        }
    )
    return payload


@router.post("")
def pack_and_go(
    req: PackAndGoRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(_get_db),
    current_user: Any = Depends(_current_user),
):
    if req.async_flag:
        from yuantus.meta_engine.services.job_service import JobService

        job_service = JobService(db)
        payload = _build_job_payload(req, user_id=str(getattr(current_user, "id", "")) or None)
        job = job_service.create_job("pack_and_go", payload, user_id=getattr(current_user, "id", None))
        status_url = str(request.url_for("pack_and_go_job_status", job_id=job.id))
        return JSONResponse(
            PackAndGoJobResponse(ok=True, job_id=job.id, status_url=status_url).model_dump()
        )

    output_dir = Path(_env_str("YUANTUS_PACKGO_OUTPUT_DIR", "./tmp/pack_and_go"))
    retention_minutes = _env_int("YUANTUS_PACKGO_RETENTION_MINUTES", 30)
    _prune_old_outputs(output_dir, retention_minutes)

    try:
        result = build_pack_and_go_package(
            db,
            item_id=req.item_id,
            depth=req.depth,
            file_roles=req.file_roles or _DEFAULT_FILE_ROLES,
            document_types=req.document_types or _DEFAULT_DOCUMENT_TYPES,
            include_previews=req.include_previews,
            include_printouts=req.include_printouts,
            include_geometry=req.include_geometry,
            output_dir=output_dir,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    def _cleanup(path: Path) -> None:
        try:
            path.unlink()
        except OSError:
            return

    background_tasks.add_task(_cleanup, result.zip_path)
    return FileResponse(
        result.zip_path,
        filename=result.zip_name,
        media_type="application/zip",
        background=background_tasks,
    )


@router.get("/jobs/{job_id}", name="pack_and_go_job_status")
def pack_and_go_job_status(
    job_id: str,
    request: Request,
    db: Session = Depends(_get_db),
    _current_user: Any = Depends(_current_user),
) -> Dict[str, Any]:
    from yuantus.meta_engine.services.job_service import JobService

    service = JobService(db)
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    payload = job.payload or {}
    result = payload.get("result", {}) if isinstance(payload, dict) else {}
    safe_result = dict(result) if isinstance(result, dict) else {}
    safe_result.pop("zip_path", None)
    download_url = None
    zip_path = result.get("zip_path") if isinstance(result, dict) else None
    if job.status == "completed" and zip_path:
        if os.path.exists(zip_path):
            download_url = str(
                request.url_for("pack_and_go_job_download", job_id=job.id)
            )

    return {
        "id": job.id,
        "status": job.status,
        "task_type": job.task_type,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "result": safe_result,
        "download_url": download_url,
    }


@router.get("/jobs/{job_id}/download", name="pack_and_go_job_download")
def pack_and_go_job_download(
    job_id: str,
    db: Session = Depends(_get_db),
    _current_user: Any = Depends(_current_user),
):
    from yuantus.meta_engine.services.job_service import JobService

    service = JobService(db)
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    payload = job.payload or {}
    result = payload.get("result", {}) if isinstance(payload, dict) else {}
    zip_path = result.get("zip_path") if isinstance(result, dict) else None
    zip_name = result.get("zip_name") if isinstance(result, dict) else None

    if job.status != "completed" or not zip_path:
        raise HTTPException(status_code=409, detail="Job not completed")
    if not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="Package not found")

    return FileResponse(
        zip_path,
        filename=zip_name or Path(zip_path).name,
        media_type="application/zip",
    )


def handle_pack_and_go_job(payload: Dict[str, Any], session: Session) -> Dict[str, Any]:
    item_id = payload.get("item_id")
    if not item_id:
        raise ValueError("item_id required")

    output_dir = Path(_env_str("YUANTUS_PACKGO_OUTPUT_DIR", "./tmp/pack_and_go"))
    retention_minutes = _env_int("YUANTUS_PACKGO_RETENTION_MINUTES", 30)
    _prune_old_outputs(output_dir, retention_minutes)

    result = build_pack_and_go_package(
        session,
        item_id=item_id,
        depth=int(payload.get("depth", -1)),
        file_roles=payload.get("file_roles") or _DEFAULT_FILE_ROLES,
        document_types=payload.get("document_types") or _DEFAULT_DOCUMENT_TYPES,
        include_previews=bool(payload.get("include_previews", False)),
        include_printouts=bool(payload.get("include_printouts", True)),
        include_geometry=bool(payload.get("include_geometry", True)),
        output_dir=output_dir,
    )

    return {
        "zip_path": str(result.zip_path),
        "zip_name": result.zip_name,
        "file_count": result.file_count,
        "total_bytes": result.total_bytes,
    }


def register_job_handlers(worker: Any) -> None:
    worker.register_handler("pack_and_go", handle_pack_and_go_job)
