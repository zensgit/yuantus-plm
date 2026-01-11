from __future__ import annotations

import csv
import io
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

from yuantus.context import get_request_context
from yuantus.meta_engine.services.file_service import FileService

router = APIRouter(prefix="/plugins/pack-and-go", tags=["plugins-pack-and-go"])


def _get_db():
    from yuantus.database import get_db

    yield from get_db()


def _get_identity_db():
    from yuantus.security.auth.database import get_identity_db

    yield from get_identity_db()


def _current_user(
    request: Request,
    identity_db=Depends(_get_identity_db),
    db=Depends(_get_db),
):
    from yuantus.api.dependencies.auth import (
        get_current_user,
        get_current_user_optional,
    )

    user = get_current_user_optional(request, identity_db=identity_db, db=db)
    return get_current_user(user=user)

_DEFAULT_FILE_ROLES = (
    "native_cad",
    "attachment",
    "printout",
    "geometry",
    "drawing",
)
_DEFAULT_DOCUMENT_TYPES = ("2d", "3d", "pr", "other")
_MANIFEST_CSV_COLUMNS = (
    "file_id",
    "filename",
    "output_filename",
    "file_role",
    "document_type",
    "cad_format",
    "size",
    "path_in_package",
    "source_item_id",
    "source_item_number",
)
_EXPORT_TYPE_OPTIONS = ("all", "2d", "3d", "pdf", "2dpdf", "3dpdf", "3d2d")
_EXPORT_TYPE_PRESETS = {
    "all": {
        "file_roles": _DEFAULT_FILE_ROLES,
        "document_types": _DEFAULT_DOCUMENT_TYPES,
        "include_printouts": True,
        "include_geometry": True,
    },
    "2d": {
        "file_roles": ("native_cad", "attachment", "drawing"),
        "document_types": ("2d",),
        "include_printouts": False,
        "include_geometry": False,
    },
    "3d": {
        "file_roles": ("native_cad", "attachment"),
        "document_types": ("3d",),
        "include_printouts": False,
        "include_geometry": True,
    },
    "pdf": {
        "file_roles": ("printout",),
        "document_types": _DEFAULT_DOCUMENT_TYPES,
        "include_printouts": True,
        "include_geometry": False,
    },
    "2dpdf": {
        "file_roles": ("native_cad", "attachment", "drawing"),
        "document_types": ("2d",),
        "include_printouts": True,
        "include_geometry": False,
    },
    "3dpdf": {
        "file_roles": ("native_cad", "attachment"),
        "document_types": ("3d",),
        "include_printouts": True,
        "include_geometry": True,
    },
    "3d2d": {
        "file_roles": ("native_cad", "attachment", "drawing"),
        "document_types": ("3d", "2d"),
        "include_printouts": False,
        "include_geometry": True,
    },
}
_FILENAME_MODES = ("original", "item_number", "item_number_rev", "internal_ref")
_PATH_STRATEGIES = ("item_role", "item", "role", "flat", "document_type")


class PackAndGoRequest(BaseModel):
    item_id: str = Field(..., description="Root item id")
    depth: int = Field(default=-1, description="BOM depth (-1 for full)")
    export_type: Optional[str] = Field(
        default=None,
        description="Preset export type (all|2d|3d|pdf|2dpdf|3dpdf|3d2d)",
    )
    filename_mode: Optional[str] = Field(
        default=None,
        description="Filename mode (original|item_number|item_number_rev|internal_ref)",
    )
    path_strategy: Optional[str] = Field(
        default=None,
        description="Path strategy (item_role|item|role|flat|document_type)",
    )
    file_roles: Optional[List[str]] = None
    document_types: Optional[List[str]] = None
    include_previews: bool = Field(default=False)
    include_printouts: bool = Field(default=True)
    include_geometry: bool = Field(default=True)
    include_bom_tree: bool = Field(
        default=False, description="Include BOM tree JSON in the package"
    )
    bom_tree_filename: Optional[str] = Field(
        default=None, description="Filename for BOM tree JSON"
    )
    include_manifest_csv: bool = Field(
        default=False, description="Include manifest CSV in the package"
    )
    manifest_csv_filename: Optional[str] = Field(
        default=None, description="Filename for manifest CSV"
    )
    async_flag: bool = Field(default=False, alias="async")


class PackAndGoJobResponse(BaseModel):
    ok: bool
    job_id: str
    status_url: str


@dataclass
class PackAndGoFile:
    file_id: str
    filename: str
    output_filename: str
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


def _normalize_export_type(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = re.sub(r"[\\s_+\\-]+", "", value.strip().lower())
    if normalized in _EXPORT_TYPE_PRESETS:
        return normalized
    allowed = ", ".join(_EXPORT_TYPE_OPTIONS)
    raise ValueError(f"export_type must be one of: {allowed}")


def _normalize_filename_mode(value: Optional[str]) -> str:
    if not value:
        return "original"
    normalized = re.sub(r"[\\s_+\\-]+", "", value.strip().lower())
    mapping = {
        "original": "original",
        "filename": "original",
        "file": "original",
        "itemnumber": "item_number",
        "itemnumberrev": "item_number_rev",
        "itemnumberrevision": "item_number_rev",
        "internalref": "internal_ref",
        "internalreference": "internal_ref",
    }
    if normalized in mapping:
        return mapping[normalized]
    allowed = ", ".join(_FILENAME_MODES)
    raise ValueError(f"filename_mode must be one of: {allowed}")


def _normalize_path_strategy(value: Optional[str]) -> str:
    if not value:
        return "item_role"
    normalized = re.sub(r"[\\s_+\\-]+", "", value.strip().lower())
    mapping = {
        "itemrole": "item_role",
        "item": "item",
        "role": "role",
        "flat": "flat",
        "root": "flat",
        "documenttype": "document_type",
        "doctype": "document_type",
    }
    if normalized in mapping:
        return mapping[normalized]
    allowed = ", ".join(_PATH_STRATEGIES)
    raise ValueError(f"path_strategy must be one of: {allowed}")


def _resolve_export_preset(
    *,
    export_type: Optional[str],
    file_roles: Optional[Sequence[str]],
    document_types: Optional[Sequence[str]],
    include_printouts: bool,
    include_geometry: bool,
    fields_set: set[str],
) -> Tuple[Optional[List[str]], Optional[List[str]], bool, bool, Optional[str]]:
    normalized = _normalize_export_type(export_type)
    if not normalized:
        return (
            list(file_roles) if file_roles is not None else None,
            list(document_types) if document_types is not None else None,
            include_printouts,
            include_geometry,
            None,
        )
    preset = _EXPORT_TYPE_PRESETS[normalized]
    if "file_roles" not in fields_set:
        file_roles = list(preset["file_roles"])
    if "document_types" not in fields_set:
        document_types = list(preset["document_types"])
    if "include_printouts" not in fields_set:
        include_printouts = preset["include_printouts"]
    if "include_geometry" not in fields_set:
        include_geometry = preset["include_geometry"]
    return (
        list(file_roles) if file_roles is not None else None,
        list(document_types) if document_types is not None else None,
        include_printouts,
        include_geometry,
        normalized,
    )


def _model_fields_set(model: BaseModel) -> set[str]:
    fields = getattr(model, "model_fields_set", None)
    if fields is not None:
        return set(fields)
    return set(getattr(model, "__fields_set__", set()))


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


def _resolve_item_revision(
    item: Optional[Item],
    version_by_id: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    if not item:
        return None
    props = item.properties or {}
    for key in ("revision", "rev", "version"):
        value = props.get(key)
        if value:
            return str(value).strip()
    if version_by_id:
        version_id = getattr(item, "current_version_id", None)
        if version_id:
            revision = version_by_id.get(version_id)
            if revision:
                return str(revision).strip()
    return None


def _resolve_internal_ref(item: Optional[Item]) -> Optional[str]:
    if not item:
        return None
    props = item.properties or {}
    for key in (
        "internal_ref",
        "internal_reference",
        "default_code",
        "internal_number",
        "number",
    ):
        value = props.get(key)
        if value:
            return str(value).strip()
    return None


def _build_output_filename(
    original_name: str,
    *,
    filename_mode: str,
    item_number: str,
    internal_ref: Optional[str],
    revision: Optional[str],
) -> str:
    original = Path(original_name).name
    if filename_mode == "original":
        return original
    suffix = Path(original).suffix
    if filename_mode == "item_number":
        base = item_number
    elif filename_mode == "item_number_rev":
        base = item_number
        if revision:
            base = f"{base}_{revision}"
    elif filename_mode == "internal_ref":
        base = internal_ref or item_number
    else:
        base = item_number
    safe_base = _sanitize_component(base)
    return f"{safe_base}{suffix}" if suffix else safe_base


def _build_package_path(
    item_number: str,
    file_role: str,
    filename: str,
    *,
    path_strategy: str,
    document_type: Optional[str],
) -> str:
    safe_item = _sanitize_component(item_number)
    safe_role = _sanitize_component(file_role)
    safe_doc = _sanitize_component(document_type or "other")
    safe_name = Path(filename).name
    if path_strategy == "item":
        return f"{safe_item}/{safe_name}"
    if path_strategy == "role":
        return f"{safe_role}/{safe_name}"
    if path_strategy == "flat":
        return safe_name
    if path_strategy == "document_type":
        return f"{safe_doc}/{safe_name}"
    return f"{safe_item}/{safe_role}/{safe_name}"


def _ensure_unique_path(path: str, *, file_id: str, used_paths: set[str]) -> str:
    if path not in used_paths:
        return path
    base, ext = os.path.splitext(path)
    suffix = file_id[:8]
    candidate = f"{base}_{suffix}{ext}"
    counter = 1
    while candidate in used_paths:
        candidate = f"{base}_{suffix}_{counter}{ext}"
        counter += 1
    return candidate


def _safe_filename(value: Optional[str], default: str) -> str:
    if value:
        name = Path(value).name
        cleaned = _sanitize_component(name)
        if cleaned:
            return cleaned
    return default


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


def _build_manifest_csv(
    entries: Sequence[Dict[str, Any]],
    columns: Sequence[str] = _MANIFEST_CSV_COLUMNS,
) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(list(columns))
    for entry in entries:
        row: List[Any] = []
        for column in columns:
            value = entry.get(column, "")
            row.append("" if value is None else value)
        writer.writerow(row)
    return output.getvalue()


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
    filename_mode: str = "original",
    path_strategy: str = "item_role",
    include_bom_tree: bool = False,
    bom_tree_filename: Optional[str] = None,
    include_manifest_csv: bool = False,
    manifest_csv_filename: Optional[str] = None,
    output_dir: Path,
    file_service: Optional[FileService] = None,
) -> PackAndGoResult:
    from sqlalchemy.orm import joinedload
    from yuantus.meta_engine.models.file import ItemFile
    from yuantus.meta_engine.models.item import Item
    from yuantus.meta_engine.services.bom_service import BOMService
    from yuantus.meta_engine.version.models import ItemVersion

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
    version_by_id: Dict[str, str] = {}
    current_version_ids = {
        item.current_version_id for item in items if item.current_version_id
    }
    if current_version_ids:
        versions = (
            session.query(ItemVersion)
            .filter(ItemVersion.id.in_(current_version_ids))
            .all()
        )
        version_by_id = {
            version.id: version.revision
            for version in versions
            if version.revision
        }

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
    used_paths: set[str] = set()

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
        source_item_number = (
            _resolve_item_number(source_item) if source_item else item_file.item_id
        )
        internal_ref = _resolve_internal_ref(source_item)
        revision = _resolve_item_revision(source_item, version_by_id)
        output_name = _build_output_filename(
            file.filename,
            filename_mode=filename_mode,
            item_number=source_item_number,
            internal_ref=internal_ref,
            revision=revision,
        )
        package_path = _build_package_path(
            source_item_number,
            file_role,
            output_name,
            path_strategy=path_strategy,
            document_type=document_type or None,
        )
        package_path = _ensure_unique_path(
            package_path, file_id=file.id, used_paths=used_paths
        )
        output_filename = Path(package_path).name
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
                output_filename=output_filename,
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
        used_paths.add(package_path)

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
    bom_tree_name = None
    manifest_csv_name = None
    if include_bom_tree:
        bom_tree_name = _safe_filename(bom_tree_filename, "bom_tree.json")
    if include_manifest_csv:
        manifest_csv_name = _safe_filename(manifest_csv_filename, "manifest.csv")

    manifest = {
        "root_item_id": item_id,
        "root_item_number": root_number,
        "depth": depth,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filename_mode": filename_mode,
        "path_strategy": path_strategy,
        "file_count": len(pack_files),
        "total_bytes": total_bytes,
        "files": [
            {
                "file_id": entry.file_id,
                "filename": entry.filename,
                "output_filename": entry.output_filename,
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
    extra_files: List[Dict[str, Any]] = []
    if bom_tree_name:
        manifest["bom_tree_file"] = bom_tree_name
        extra_files.append({"kind": "bom_tree", "path": bom_tree_name})
    if manifest_csv_name:
        manifest["manifest_csv_file"] = manifest_csv_name
        extra_files.append({"kind": "manifest_csv", "path": manifest_csv_name})
    if extra_files:
        manifest["extra_files"] = extra_files

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for entry in pack_files:
            zipf.write(entry.source_path, entry.path_in_package)
        zipf.writestr(
            "manifest.json",
            json.dumps(manifest, ensure_ascii=True, indent=2),
        )
        if bom_tree_name:
            zipf.writestr(
                bom_tree_name,
                json.dumps(bom_tree, ensure_ascii=True, indent=2),
            )
        if manifest_csv_name:
            zipf.writestr(
                manifest_csv_name,
                _build_manifest_csv(manifest["files"]),
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
    try:
        (
            file_roles,
            document_types,
            include_printouts,
            include_geometry,
            export_type,
        ) = _resolve_export_preset(
            export_type=req.export_type,
            file_roles=req.file_roles,
            document_types=req.document_types,
            include_printouts=req.include_printouts,
            include_geometry=req.include_geometry,
            fields_set=_model_fields_set(req),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        filename_mode = _normalize_filename_mode(req.filename_mode)
        path_strategy = _normalize_path_strategy(req.path_strategy)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if req.async_flag:
        from yuantus.meta_engine.services.job_service import JobService

        job_service = JobService(db)
        payload = _build_job_payload(req, user_id=str(getattr(current_user, "id", "")) or None)
        payload.update(
            {
                "export_type": export_type,
                "file_roles": file_roles,
                "document_types": document_types,
                "include_printouts": include_printouts,
                "include_geometry": include_geometry,
                "filename_mode": filename_mode,
                "path_strategy": path_strategy,
            }
        )
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
            file_roles=file_roles or _DEFAULT_FILE_ROLES,
            document_types=document_types or _DEFAULT_DOCUMENT_TYPES,
            include_previews=req.include_previews,
            include_printouts=include_printouts,
            include_geometry=include_geometry,
            filename_mode=filename_mode,
            path_strategy=path_strategy,
            include_bom_tree=req.include_bom_tree,
            bom_tree_filename=req.bom_tree_filename,
            include_manifest_csv=req.include_manifest_csv,
            manifest_csv_filename=req.manifest_csv_filename,
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
    fields_set = {
        key
        for key in payload
        if key in {"file_roles", "document_types", "include_printouts", "include_geometry"}
    }
    try:
        (
            file_roles,
            document_types,
            include_printouts,
            include_geometry,
            _,
        ) = _resolve_export_preset(
            export_type=payload.get("export_type"),
            file_roles=payload.get("file_roles"),
            document_types=payload.get("document_types"),
            include_printouts=bool(payload.get("include_printouts", True)),
            include_geometry=bool(payload.get("include_geometry", True)),
            fields_set=fields_set,
        )
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    try:
        filename_mode = _normalize_filename_mode(payload.get("filename_mode"))
        path_strategy = _normalize_path_strategy(payload.get("path_strategy"))
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    result = build_pack_and_go_package(
        session,
        item_id=item_id,
        depth=int(payload.get("depth", -1)),
        file_roles=file_roles or _DEFAULT_FILE_ROLES,
        document_types=document_types or _DEFAULT_DOCUMENT_TYPES,
        include_previews=bool(payload.get("include_previews", False)),
        include_printouts=include_printouts,
        include_geometry=include_geometry,
        filename_mode=filename_mode,
        path_strategy=path_strategy,
        include_bom_tree=bool(payload.get("include_bom_tree", False)),
        bom_tree_filename=payload.get("bom_tree_filename"),
        include_manifest_csv=bool(payload.get("include_manifest_csv", False)),
        manifest_csv_filename=payload.get("manifest_csv_filename"),
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
