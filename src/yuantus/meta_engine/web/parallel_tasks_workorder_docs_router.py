from __future__ import annotations

import io
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.services.parallel_tasks_service import (
    WorkorderDocumentPackService,
)


parallel_tasks_workorder_docs_router = APIRouter(tags=["ParallelTasks"])


def _error_detail(
    code: str,
    message: str,
    *,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "code": str(code),
        "message": str(message),
        "context": context or {},
    }


def _raise_api_error(
    *,
    status_code: int,
    code: str,
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    raise HTTPException(
        status_code=status_code,
        detail=_error_detail(code, message, context=context),
    )


def _manifest_to_pdf_bytes(manifest: Dict[str, Any]) -> bytes:
    def esc(text: str) -> str:
        return (
            str(text)
            .replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )

    export_meta = manifest.get("export_meta") if isinstance(manifest, dict) else {}
    if not isinstance(export_meta, dict):
        export_meta = {}
    scope_summary = manifest.get("scope_summary") if isinstance(manifest, dict) else {}
    if not isinstance(scope_summary, dict):
        scope_summary = {}
    locale = manifest.get("locale") if isinstance(manifest, dict) else {}
    if not isinstance(locale, dict):
        locale = {}
    version_lock_summary = (
        manifest.get("version_lock_summary") if isinstance(manifest, dict) else {}
    )
    if not isinstance(version_lock_summary, dict):
        version_lock_summary = {}

    lines = [
        "Workorder Document Pack",
        "=== Export Metadata ===",
        f"routing_id: {manifest.get('routing_id') or ''}",
        f"operation_id: {manifest.get('operation_id') or ''}",
        f"job_no: {export_meta.get('job_no') or ''}",
        f"operator_id: {export_meta.get('operator_id') or ''}",
        f"operator_name: {export_meta.get('operator_name') or ''}",
        f"exported_by: {export_meta.get('exported_by') or ''}",
        f"generated_at: {manifest.get('generated_at') or ''}",
        "=== Document Summary ===",
        f"total_documents: {manifest.get('count') or 0}",
        f"routing_scope_docs: {scope_summary.get('routing') or 0}",
        f"operation_scope_docs: {scope_summary.get('operation') or 0}",
    ]
    if version_lock_summary:
        lines.extend(
            [
                "=== Version Lock Summary ===",
                f"locked: {version_lock_summary.get('locked') or 0}",
                f"unlocked: {version_lock_summary.get('unlocked') or 0}",
                f"mismatched: {version_lock_summary.get('mismatched') or 0}",
                f"stale: {version_lock_summary.get('stale') or 0}",
                f"requires_lock: {bool(version_lock_summary.get('requires_lock'))}",
            ]
        )
    if locale:
        lines.extend(
            [
                "=== Locale ===",
                f"lang: {locale.get('lang') or ''}",
                f"profile_id: {locale.get('id') or ''}",
                f"report_type: {locale.get('report_type') or locale.get('requested_report_type') or ''}",
                f"timezone: {locale.get('timezone') or ''}",
            ]
        )
    lines.append("=== Documents ===")
    for idx, row in enumerate(manifest.get("documents") or [], start=1):
        lines.append(
            f"{idx}. doc={row.get('document_item_id')} "
            f"op={row.get('operation_id') or '-'} "
            f"scope={row.get('document_scope') or '-'} "
            f"inherit={row.get('inherit_to_children')} "
            f"visible={row.get('visible_in_production')}"
        )

    y = 800
    text_ops: List[str] = []
    for line in lines:
        text_ops.append(f"1 0 0 1 40 {y} Tm ({esc(line)}) Tj")
        y -= 14
        if y < 40:
            break

    stream = "BT\n/F1 10 Tf\n" + "\n".join(text_ops) + "\nET\n"
    stream_bytes = stream.encode("latin-1", errors="replace")

    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        (
            b"3 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\n"
            b"endobj\n"
        ),
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        (
            f"5 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin-1")
            + stream_bytes
            + b"endstream\nendobj\n"
        ),
    ]

    pdf = b"%PDF-1.4\n"
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj

    xref_start = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n".encode("latin-1")
    pdf += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        pdf += f"{offset:010d} 00000 n \n".encode("latin-1")

    pdf += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF\n"
    ).encode("latin-1")
    return pdf


class WorkorderDocLinkRequest(BaseModel):
    routing_id: str
    operation_id: Optional[str] = None
    document_item_id: str
    inherit_to_children: bool = True
    visible_in_production: bool = True
    document_version_id: Optional[str] = None


@parallel_tasks_workorder_docs_router.post("/workorder-docs/links")
async def upsert_workorder_doc_link(
    payload: WorkorderDocLinkRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = WorkorderDocumentPackService(db)
    extras: Dict[str, Any] = {}
    # Preserve existing lock state when the client omitted document_version_id
    # entirely. An explicit null in the body still clears the lock.
    if "document_version_id" in payload.model_fields_set:
        extras["document_version_id"] = payload.document_version_id
    try:
        link = service.upsert_link(
            routing_id=payload.routing_id,
            operation_id=payload.operation_id,
            document_item_id=payload.document_item_id,
            inherit_to_children=payload.inherit_to_children,
            visible_in_production=payload.visible_in_production,
            **extras,
        )
        serialized = service.serialize_link(link)
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_api_error(
            status_code=400,
            code="workorder_doc_link_invalid",
            message=str(exc),
            context={
                "routing_id": payload.routing_id,
                "operation_id": payload.operation_id,
                "document_item_id": payload.document_item_id,
                "document_version_id": payload.document_version_id,
            },
        )
    return serialized


@parallel_tasks_workorder_docs_router.get("/workorder-docs/links")
async def list_workorder_doc_links(
    routing_id: str = Query(...),
    operation_id: Optional[str] = Query(None),
    include_inherited: bool = Query(True),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = WorkorderDocumentPackService(db)
    links = service.list_links(
        routing_id=routing_id,
        operation_id=operation_id,
        include_inherited=include_inherited,
    )
    return {
        "routing_id": routing_id,
        "operation_id": operation_id,
        "total": len(links),
        "links": [service.serialize_link(link) for link in links],
        "operator_id": int(user.id),
    }


@parallel_tasks_workorder_docs_router.get("/workorder-docs/export")
async def export_workorder_doc_pack(
    routing_id: str = Query(...),
    operation_id: Optional[str] = Query(None),
    include_inherited: bool = Query(True),
    export_format: str = Query("zip", description="zip|json|pdf"),
    job_no: Optional[str] = Query(None),
    operator_name: Optional[str] = Query(None),
    report_lang: Optional[str] = Query(None),
    report_type: Optional[str] = Query(None),
    locale_profile_id: Optional[str] = Query(None),
    require_locked_versions: bool = Query(False),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = WorkorderDocumentPackService(db)
    try:
        result = service.export_pack(
            routing_id=routing_id,
            operation_id=operation_id,
            include_inherited=include_inherited,
            require_locked_versions=require_locked_versions,
            export_meta={
                "job_no": job_no,
                "operator_id": int(user.id),
                "operator_name": operator_name,
                "exported_by": str(getattr(user, "email", "") or getattr(user, "id", "")),
                "report_lang": report_lang,
                "report_type": report_type,
                "locale_profile_id": locale_profile_id,
            },
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=409,
            code="workorder_export_unlocked_versions",
            message=str(exc),
            context={
                "routing_id": routing_id,
                "operation_id": operation_id,
                "require_locked_versions": require_locked_versions,
            },
        )
    manifest = result["manifest"]
    normalized = (export_format or "zip").strip().lower()
    if normalized == "json":
        content = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/json",
            headers={
                "Content-Disposition": 'attachment; filename="workorder-doc-pack.json"'
            },
        )
    if normalized == "pdf":
        content = _manifest_to_pdf_bytes(manifest)
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="workorder-doc-pack.pdf"'
            },
        )
    if normalized != "zip":
        _raise_api_error(
            status_code=400,
            code="workorder_export_invalid_format",
            message="export_format must be zip, json or pdf",
            context={"export_format": export_format},
        )
    return StreamingResponse(
        io.BytesIO(result["zip_bytes"]),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="workorder-doc-pack.zip"'},
    )
