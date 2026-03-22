from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import String, cast
from sqlalchemy.orm import Session

from yuantus.database import get_db
from yuantus.config import get_settings
from yuantus.integrations.cad_connectors import (
    registry as cad_registry,
    reload_connectors,
    resolve_cad_sync_key,
)

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.exceptions.handlers import PLMException, QuotaExceededError
from yuantus.meta_engine.models.cad_audit import CadChangeLog
from yuantus.meta_engine.models.file import FileContainer, FileRole, ItemFile
from yuantus.meta_engine.models.meta_schema import ItemType, Property
from yuantus.meta_engine.models.job import ConversionJob
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.schemas.aml import AMLAction, GenericItem
from yuantus.meta_engine.services.cad_service import CadService
from yuantus.meta_engine.services.cad_bom_import_service import (
    build_cad_bom_mismatch_analysis,
    build_cad_bom_operator_summary,
)
from yuantus.meta_engine.services.cad_converter_service import CADConverterService
from yuantus.meta_engine.services.engine import AMLEngine
from yuantus.meta_engine.services.file_service import FileService
from yuantus.meta_engine.services.job_errors import JobFatalError
from yuantus.meta_engine.services.job_service import JobService
from yuantus.meta_engine.services.checkin_service import CheckinManager
from yuantus.security.auth.database import get_identity_db
from yuantus.security.auth.quota_service import QuotaService

router = APIRouter(prefix="/cad", tags=["CAD"])
VAULT_DIR = get_settings().LOCAL_STORAGE_PATH
CAD_PROOF_DECISION_ACTIONS = {
    "cad_operator_proof_acknowledged": "acknowledged",
    "cad_operator_proof_waived": "waived",
}
CAD_PROOF_ALLOWED_DECISIONS = set(CAD_PROOF_DECISION_ACTIONS.values())
CAD_PROOF_ALLOWED_SCOPES = {"full_proof", "selected_gaps"}

"""
CAD Connector API
Handles Document Locking and Versioning.
"""

_FILENAME_REV_RE = re.compile(r"(?i)(?:rev|revision)[\\s_-]*([A-Za-z0-9]+)$")
_FILENAME_VER_RE = re.compile(r"(?i)v(\\d+(?:\\.\\d+)*)$")


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    roles = set(user.roles or [])
    if "admin" not in roles and "superuser" not in roles:
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


def get_checkin_manager(
    user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> CheckinManager:
    # RBACUser should have an integer ID map?
    # user.id is the key (99, 1, 2)
    return CheckinManager(db, user_id=user.id)


def _load_cad_document_payload(file_container: FileContainer) -> Optional[Dict[str, Any]]:
    if not file_container.cad_document_path:
        return None
    file_service = FileService()
    output_stream = io.BytesIO()
    try:
        file_service.download_file(file_container.cad_document_path, output_stream)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"CAD document download failed: {exc}"
        ) from exc
    output_stream.seek(0)
    try:
        payload = json.load(output_stream)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail="CAD document invalid JSON"
        ) from exc
    return payload if isinstance(payload, dict) else None


def _load_cad_metadata_payload(file_container: FileContainer) -> Optional[Dict[str, Any]]:
    if not file_container.cad_metadata_path:
        return None
    file_service = FileService()
    output_stream = io.BytesIO()
    try:
        file_service.download_file(file_container.cad_metadata_path, output_stream)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"CAD metadata download failed: {exc}"
        ) from exc
    output_stream.seek(0)
    try:
        payload = json.load(output_stream)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail="CAD metadata invalid JSON"
        ) from exc
    return payload if isinstance(payload, dict) else None


def _extract_entity_ids(document_payload: Dict[str, Any]) -> List[int]:
    entities = document_payload.get("entities")
    if not isinstance(entities, list):
        return []
    entity_ids: List[int] = []
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        entity_id = entity.get("id")
        if isinstance(entity_id, int):
            entity_ids.append(entity_id)
    return entity_ids


def _extract_mesh_stats(payload: Dict[str, Any]) -> Dict[str, Any]:
    stats: Dict[str, Any] = {"raw_keys": sorted(payload.keys())}
    entities = payload.get("entities")
    if isinstance(entities, list):
        stats["entity_count"] = len(entities)
    for key in ("triangle_count", "triangles", "face_count", "faces"):
        value = payload.get(key)
        if isinstance(value, int):
            stats["triangle_count"] = value
            break
        if isinstance(value, list):
            stats["triangle_count"] = len(value)
            break
    bounds = payload.get("bounds") or payload.get("bbox")
    if bounds is not None:
        stats["bounds"] = bounds
    return stats


def _validate_entity_ids(
    file_container: FileContainer, entity_ids: List[int]
) -> None:
    if not entity_ids:
        return
    document_payload = _load_cad_document_payload(file_container)
    if not document_payload:
        return
    known_ids = set(_extract_entity_ids(document_payload))
    missing = sorted({eid for eid in entity_ids if eid not in known_ids})
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown CAD entity ids: {missing}",
        )


def _normalize_view_notes(notes: Optional[List[Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for note in notes or []:
        if isinstance(note, CadEntityNote):
            normalized.append(note.model_dump())
        elif isinstance(note, dict):
            normalized.append(note)
    return normalized


def _log_cad_change(
    db: Session,
    file_container: FileContainer,
    action: str,
    payload: Dict[str, Any],
    user: CurrentUser,
) -> CadChangeLog:
    entry = CadChangeLog(
        id=str(uuid.uuid4()),
        file_id=file_container.id,
        action=action,
        payload=payload,
        created_at=datetime.utcnow(),
        tenant_id=user.tenant_id,
        org_id=user.org_id,
        user_id=user.id,
    )
    db.add(entry)
    return entry


def _diff_dicts(
    before: Dict[str, Any], after: Dict[str, Any]
) -> Dict[str, Any]:
    added = {key: after[key] for key in after.keys() - before.keys()}
    removed = {key: before[key] for key in before.keys() - after.keys()}
    changed = {
        key: {"from": before[key], "to": after[key]}
        for key in before.keys() & after.keys()
        if before[key] != after[key]
    }
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
    }


class CadImportJob(BaseModel):
    id: str
    task_type: str
    status: str


class CadImportResponse(BaseModel):
    file_id: str
    filename: str
    checksum: str
    is_duplicate: bool
    item_id: Optional[str] = None
    attachment_id: Optional[str] = None
    jobs: List[CadImportJob] = Field(default_factory=list)
    download_url: str
    preview_url: Optional[str] = None
    geometry_url: Optional[str] = None
    cad_manifest_url: Optional[str] = None
    cad_document_url: Optional[str] = None
    cad_metadata_url: Optional[str] = None
    cad_bom_url: Optional[str] = None
    cad_dedup_url: Optional[str] = None
    cad_viewer_url: Optional[str] = None
    cad_document_schema_version: Optional[int] = None
    cad_format: Optional[str] = None
    cad_connector_id: Optional[str] = None
    document_type: Optional[str] = None
    is_native_cad: bool = False
    author: Optional[str] = None
    source_system: Optional[str] = None
    source_version: Optional[str] = None
    document_version: Optional[str] = None


class CadConnectorInfoResponse(BaseModel):
    id: str
    label: str
    cad_format: str
    document_type: str
    extensions: List[str]
    aliases: List[str] = Field(default_factory=list)
    priority: int
    description: Optional[str] = None


class CadCapabilityMode(BaseModel):
    available: bool
    modes: List[str] = Field(default_factory=list)
    note: Optional[str] = None
    status: str = "ok"
    degraded_reason: Optional[str] = None


class CadCapabilitiesResponse(BaseModel):
    connectors: List[CadConnectorInfoResponse]
    counts: Dict[str, int]
    formats: Dict[str, List[str]]
    extensions: Dict[str, List[str]]
    features: Dict[str, CadCapabilityMode]
    integrations: Dict[str, Any]


def _feature_status(
    *,
    available: bool,
    modes: List[str],
    has_local_fallback: bool,
    remote_modes: Optional[List[str]] = None,
    disabled_reason: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    if not available:
        return {
            "status": "disabled",
            "degraded_reason": disabled_reason,
        }
    remote_set = set(remote_modes or [])
    if any(mode in remote_set for mode in modes):
        return {
            "status": "ok",
            "degraded_reason": None,
        }
    if has_local_fallback:
        return {
            "status": "degraded",
            "degraded_reason": "local fallback only",
        }
    return {
        "status": "ok",
        "degraded_reason": None,
    }


def _integration_status(
    *,
    configured: bool,
    available: bool,
    fallback_reason: Optional[str],
    disabled_reason: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    if configured and available:
        return {
            "status": "ok",
            "degraded_reason": None,
        }
    if not configured and fallback_reason:
        return {
            "status": "degraded",
            "degraded_reason": fallback_reason,
        }
    if not available:
        return {
            "status": "disabled",
            "degraded_reason": disabled_reason,
        }
    return {"status": "disabled", "degraded_reason": disabled_reason}


class CadConnectorReloadRequest(BaseModel):
    config_path: Optional[str] = None
    config: Optional[Any] = None


class CadConnectorReloadResponse(BaseModel):
    config_path: Optional[str] = None
    custom_loaded: int
    errors: List[str] = Field(default_factory=list)


class CadSyncTemplateRow(BaseModel):
    property_name: str
    label: Optional[str] = None
    data_type: Optional[str] = None
    is_cad_synced: bool = False
    cad_key: Optional[str] = None


class CadSyncTemplateResponse(BaseModel):
    item_type_id: str
    properties: List[CadSyncTemplateRow]


class CadSyncTemplateApplyResponse(BaseModel):
    item_type_id: str
    updated: int
    skipped: int
    missing: List[str] = Field(default_factory=list)


class CadExtractAttributesResponse(BaseModel):
    file_id: str
    cad_format: Optional[str] = None
    cad_connector_id: Optional[str] = None
    job_id: Optional[str] = None
    job_status: Optional[str] = None
    extracted_at: Optional[str] = None
    extracted_attributes: Dict[str, Any] = Field(default_factory=dict)
    source: Optional[str] = None


class CadBomResponse(BaseModel):
    file_id: str
    item_id: Optional[str] = None
    job_id: Optional[str] = None
    job_status: Optional[str] = None
    imported_at: Optional[str] = None
    import_result: Dict[str, Any] = Field(default_factory=dict)
    bom: Dict[str, Any] = Field(default_factory=dict)
    summary: Dict[str, Any] = Field(default_factory=dict)
    mismatch: Dict[str, Any] = Field(default_factory=dict)


class CadBomReimportRequest(BaseModel):
    item_id: Optional[str] = None


class CadBomReimportResponse(BaseModel):
    file_id: str
    item_id: str
    job_id: str
    job_status: str


class CadBomBundleFileInfo(BaseModel):
    file_id: str
    filename: Optional[str] = None
    cad_connector_id: Optional[str] = None
    cad_format: Optional[str] = None
    document_type: Optional[str] = None
    cad_review_state: Optional[str] = None
    cad_review_note: Optional[str] = None
    has_stored_artifact: bool = False


class CadProofDecisionEntry(BaseModel):
    id: str
    decision: str
    scope: str = "full_proof"
    comment: Optional[str] = None
    reason_code: Optional[str] = None
    issue_codes: List[str] = Field(default_factory=list)
    proof_fingerprint: Optional[str] = None
    proof_status: Optional[str] = None
    proof_gaps: List[str] = Field(default_factory=list)
    asset_quality_status: Optional[str] = None
    mismatch_status: Optional[str] = None
    review_state: Optional[str] = None
    expires_at: Optional[str] = None
    created_at: str
    user_id: Optional[int] = None
    is_current: bool = False
    covers_current_proof: bool = False


class CadProofDecisionRequest(BaseModel):
    decision: str
    comment: str
    reason_code: Optional[str] = None
    scope: str = "full_proof"
    issue_codes: List[str] = Field(default_factory=list)
    expires_at: Optional[str] = None


class CadProofDecisionListResponse(BaseModel):
    file_id: str
    current_fingerprint: Optional[str] = None
    active_decision: Optional[CadProofDecisionEntry] = None
    entries: List[CadProofDecisionEntry] = Field(default_factory=list)


class CadBomOperatorBundleResponse(BaseModel):
    bundle_version: str = "cad_operator_proof_bundle_v1"
    exported_at: datetime
    file: CadBomBundleFileInfo
    viewer_readiness: Dict[str, Any] = Field(default_factory=dict)
    asset_quality: Dict[str, Any] = Field(default_factory=dict)
    cad_bom: CadBomResponse
    operator_proof: Dict[str, Any] = Field(default_factory=dict)
    active_decision: Optional[CadProofDecisionEntry] = None
    proof_decisions: List[CadProofDecisionEntry] = Field(default_factory=list)
    review: CadReviewResponse
    history: List[CadChangeLogEntry] = Field(default_factory=list)
    proof_manifest: Dict[str, Any] = Field(default_factory=dict)
    links: Dict[str, Optional[str]] = Field(default_factory=dict)


def _mismatch_links(file_id: str, history_limit: int) -> Dict[str, str]:
    return {
        "bom_url": f"/api/v1/cad/files/{file_id}/bom",
        "mismatch_url": f"/api/v1/cad/files/{file_id}/bom/mismatch",
        "proof_url": f"/api/v1/cad/files/{file_id}/proof?history_limit={history_limit}",
        "proof_decisions_url": f"/api/v1/cad/files/{file_id}/proof/decisions?history_limit={history_limit}",
        "export_url": f"/api/v1/cad/files/{file_id}/bom/export",
        "asset_quality_url": f"/api/v1/file/{file_id}/asset_quality",
        "viewer_readiness_url": f"/api/v1/file/{file_id}/viewer_readiness",
        "review_url": f"/api/v1/cad/files/{file_id}/review",
        "history_url": f"/api/v1/cad/files/{file_id}/history?limit={history_limit}",
        "reimport_url": f"/api/v1/cad/files/{file_id}/bom/reimport",
    }


def _dedupe_code_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    deduped: List[Dict[str, str]] = []
    for row in rows:
        code = str((row or {}).get("code") or "").strip()
        label = str((row or {}).get("label") or "").strip()
        if not code:
            continue
        key = (code, label)
        if key in seen:
            continue
        seen.add(key)
        deduped.append({"code": code, "label": label})
    return deduped


def _dedupe_text(values: List[Any]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _compute_operator_proof_fingerprint(operator_proof: Dict[str, Any]) -> str:
    fingerprint_payload = {
        "status": operator_proof.get("status"),
        "asset_quality_status": operator_proof.get("asset_quality_status"),
        "asset_result_status": operator_proof.get("asset_result_status"),
        "converter_result_status": operator_proof.get("converter_result_status"),
        "viewer_mode": operator_proof.get("viewer_mode"),
        "is_viewer_ready": bool(operator_proof.get("is_viewer_ready")),
        "cad_bom_status": operator_proof.get("cad_bom_status"),
        "mismatch_status": operator_proof.get("mismatch_status"),
        "review_state": operator_proof.get("review_state"),
        "proof_gaps": sorted(_dedupe_text(list(operator_proof.get("proof_gaps") or []))),
        "issue_codes": sorted(_dedupe_text(list(operator_proof.get("issue_codes") or []))),
        "components": operator_proof.get("components") or {},
        "file_context": operator_proof.get("file_context") or {},
    }
    raw = json.dumps(
        fingerprint_payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _normalize_optional_iso_datetime(value: Optional[str]) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).isoformat()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid expires_at: {text}") from exc


def _build_cad_proof_decision_entries(
    *,
    history_entries: List[CadChangeLogEntry],
    current_fingerprint: str,
    current_issue_codes: List[str],
) -> List[CadProofDecisionEntry]:
    current_issue_set = set(_dedupe_text(current_issue_codes))
    decisions: List[CadProofDecisionEntry] = []
    for entry in history_entries:
        decision = CAD_PROOF_DECISION_ACTIONS.get(entry.action)
        if not decision:
            continue
        payload = entry.payload or {}
        issue_codes = _dedupe_text(list(payload.get("issue_codes") or []))
        proof_gaps = _dedupe_text(list(payload.get("proof_gaps") or []))
        proof_fingerprint = str(payload.get("proof_fingerprint") or "").strip() or None
        is_current = proof_fingerprint == current_fingerprint
        decision_issue_set = set(issue_codes)
        covers_current_proof = bool(
            is_current
            and (
                str(payload.get("scope") or "full_proof") == "full_proof"
                or (current_issue_set and current_issue_set.issubset(decision_issue_set))
            )
        )
        decisions.append(
            CadProofDecisionEntry(
                id=entry.id,
                decision=decision,
                scope=str(payload.get("scope") or "full_proof"),
                comment=str(payload.get("comment") or "").strip() or None,
                reason_code=str(payload.get("reason_code") or "").strip() or None,
                issue_codes=issue_codes,
                proof_fingerprint=proof_fingerprint,
                proof_status=str(payload.get("proof_status") or "").strip() or None,
                proof_gaps=proof_gaps,
                asset_quality_status=str(payload.get("asset_quality_status") or "").strip() or None,
                mismatch_status=str(payload.get("mismatch_status") or "").strip() or None,
                review_state=str(payload.get("review_state") or "").strip() or None,
                expires_at=str(payload.get("expires_at") or "").strip() or None,
                created_at=entry.created_at,
                user_id=entry.user_id,
                is_current=is_current,
                covers_current_proof=covers_current_proof,
            )
        )
    return decisions


def _build_cad_operator_proof(
    *,
    file_container: FileContainer,
    cad_bom: CadBomResponse,
    viewer_readiness: Dict[str, Any],
    asset_quality: Dict[str, Any],
    review: CadReviewResponse,
) -> Dict[str, Any]:
    proof_gaps: List[str] = []

    def _append_gap(code: str) -> None:
        if code not in proof_gaps:
            proof_gaps.append(code)

    asset_status = str(asset_quality.get("status") or "missing")
    asset_result_status = str(asset_quality.get("result_status") or "missing")
    converter_result_status = str(
        (asset_quality.get("result") or {}).get("status") or "missing"
    )
    viewer_mode = str(viewer_readiness.get("viewer_mode") or "none")
    is_viewer_ready = bool(viewer_readiness.get("is_viewer_ready"))
    bom_status = str((cad_bom.summary or {}).get("status") or "missing")
    mismatch_status = str((cad_bom.mismatch or {}).get("status") or "missing")
    review_state = str(review.state or "").strip().lower() or None

    if asset_status == "missing":
        _append_gap("asset_quality_missing")
    elif asset_status == "degraded":
        _append_gap("asset_quality_degraded")
    if converter_result_status == "failed":
        _append_gap("converter_result_failed")
    elif converter_result_status == "degraded":
        _append_gap("converter_result_degraded")
    if not is_viewer_ready:
        _append_gap("viewer_not_ready")
    if bom_status == "missing":
        _append_gap("cad_bom_missing")
    elif bom_status == "empty":
        _append_gap("cad_bom_empty")
    elif bom_status == "degraded":
        _append_gap("cad_bom_degraded")
    if mismatch_status == "mismatch":
        _append_gap("cad_bom_live_mismatch")
    elif mismatch_status == "unresolved":
        _append_gap("cad_bom_mismatch_unresolved")
    if review_state == "pending":
        _append_gap("cad_review_pending")

    blocked_codes = {
        "asset_quality_missing",
        "converter_result_failed",
        "viewer_not_ready",
    }
    if any(code in blocked_codes for code in proof_gaps):
        status = "blocked"
    elif proof_gaps:
        status = "needs_review"
    else:
        status = "ready"

    next_actions = _dedupe_code_rows(
        list(asset_quality.get("recovery_actions") or [])
        + list((cad_bom.summary or {}).get("recovery_actions") or [])
        + list((cad_bom.mismatch or {}).get("recovery_actions") or [])
    )

    issue_codes = _dedupe_text(
        list(asset_quality.get("issue_codes") or [])
        + list((cad_bom.summary or {}).get("issue_codes") or [])
        + list((cad_bom.mismatch or {}).get("issue_codes") or [])
        + proof_gaps
    )

    return {
        "status": status,
        "asset_quality_status": asset_status,
        "asset_result_status": asset_result_status,
        "converter_result_status": converter_result_status,
        "viewer_mode": viewer_mode,
        "is_viewer_ready": is_viewer_ready,
        "cad_bom_status": bom_status,
        "mismatch_status": mismatch_status,
        "review_state": review_state,
        "needs_operator_review": status != "ready",
        "requires_export_before_recovery": status != "ready",
        "proof_gaps": proof_gaps,
        "issue_codes": issue_codes,
        "next_actions": next_actions,
        "components": {
            "asset_quality": asset_status,
            "viewer_readiness": viewer_mode,
            "cad_bom": bom_status,
            "mismatch": mismatch_status,
            "review": review_state,
        },
        "file_context": {
            "file_id": file_container.id,
            "cad_connector_id": file_container.cad_connector_id,
            "cad_format": file_container.cad_format,
            "document_type": file_container.document_type,
        },
    }


def _build_cad_operator_bundle(
    *,
    file_container: FileContainer,
    db: Session,
    history_limit: int,
) -> CadBomOperatorBundleResponse:
    cad_bom = _build_cad_bom_response(file_container=file_container, db=db)
    review = _build_cad_review_response(file_container)
    history_entries = _load_cad_history_entries(
        file_container=file_container,
        db=db,
        limit=history_limit,
    )
    converter = CADConverterService(db, vault_base_path=VAULT_DIR)
    viewer_readiness = converter.assess_viewer_readiness(file_container)
    asset_quality = dict(viewer_readiness.get("asset_quality") or {})
    if not asset_quality:
        asset_quality = converter.assess_asset_quality(file_container)
    operator_proof = _build_cad_operator_proof(
        file_container=file_container,
        cad_bom=cad_bom,
        viewer_readiness=viewer_readiness,
        asset_quality=asset_quality,
        review=review,
    )
    proof_fingerprint = _compute_operator_proof_fingerprint(operator_proof)
    operator_proof["proof_fingerprint"] = proof_fingerprint
    proof_decisions = _build_cad_proof_decision_entries(
        history_entries=history_entries,
        current_fingerprint=proof_fingerprint,
        current_issue_codes=list(operator_proof.get("issue_codes") or []),
    )
    active_decision = next(
        (entry for entry in proof_decisions if entry.is_current),
        None,
    )
    if active_decision:
        operator_proof["decision_status"] = active_decision.decision
        operator_proof["has_active_decision"] = True
        operator_proof["active_decision_id"] = active_decision.id
        operator_proof["active_decision_scope"] = active_decision.scope
        operator_proof["active_decision_covers_current_proof"] = bool(
            active_decision.covers_current_proof
        )
        operator_proof["requires_operator_decision"] = bool(
            operator_proof.get("status") != "ready"
            and not active_decision.covers_current_proof
        )
    else:
        operator_proof["decision_status"] = (
            "not_required" if operator_proof.get("status") == "ready" else "open"
        )
        operator_proof["has_active_decision"] = False
        operator_proof["active_decision_id"] = None
        operator_proof["active_decision_scope"] = None
        operator_proof["active_decision_covers_current_proof"] = False
        operator_proof["requires_operator_decision"] = bool(
            operator_proof.get("status") != "ready"
        )
    governance_actions: List[Dict[str, str]] = []
    if operator_proof.get("status") != "ready":
        if active_decision and not active_decision.covers_current_proof:
            governance_actions.append(
                {
                    "code": "complete_operator_proof_decision",
                    "label": "Record a full-proof acknowledgement or waiver for the remaining gaps.",
                }
            )
        elif not active_decision:
            governance_actions.extend(
                [
                    {
                        "code": "acknowledge_operator_proof",
                        "label": "Record an acknowledgement for the current CAD proof gaps.",
                    },
                    {
                        "code": "waive_operator_proof",
                        "label": "Record a bounded waiver with reason and review scope.",
                    },
                ]
            )
    operator_proof["next_actions"] = _dedupe_code_rows(
        list(operator_proof.get("next_actions") or []) + governance_actions
    )
    proof_files = [
        "bundle.json",
        "file.json",
        "operator_proof.json",
        "active_decision.json",
        "proof_decisions.json",
        "proof_decisions.csv",
        "viewer_readiness.json",
        "asset_quality.json",
        "asset_quality_issue_codes.csv",
        "asset_quality_recovery_actions.csv",
        "summary.json",
        "review.json",
        "import_result.json",
        "bom.json",
        "mismatch.json",
        "live_bom.json",
        "history.json",
        "history.csv",
        "recovery_actions.csv",
        "issue_codes.csv",
        "mismatch_delta.csv",
        "mismatch_rows.csv",
        "mismatch_issue_codes.csv",
        "mismatch_recovery_actions.csv",
        "mismatch_delta_preview.json",
        "proof_manifest.json",
        "README.txt",
    ]
    proof_manifest = {
        "bundle_kind": "cad_operator_proof_bundle",
        "bundle_version": 1,
        "file_id": file_container.id,
        "generated_at": datetime.utcnow().isoformat(),
        "proof_fingerprint": proof_fingerprint,
        "operator_proof_status": operator_proof.get("status"),
        "decision_status": operator_proof.get("decision_status"),
        "proof_gaps": operator_proof.get("proof_gaps") or [],
        "needs_operator_review": bool(operator_proof.get("needs_operator_review")),
        "requires_operator_decision": bool(
            operator_proof.get("requires_operator_decision")
        ),
        "proof_decision_count": len(proof_decisions),
        "active_decision_id": active_decision.id if active_decision else None,
        "active_decision_status": active_decision.decision if active_decision else None,
        "active_decision_scope": active_decision.scope if active_decision else None,
        "active_decision_reason_code": active_decision.reason_code if active_decision else None,
        "active_decision_expires_at": active_decision.expires_at if active_decision else None,
        "active_decision_covers_current_proof": bool(
            active_decision.covers_current_proof if active_decision else False
        ),
        "asset_quality_status": asset_quality.get("status"),
        "asset_result_status": asset_quality.get("result_status"),
        "converter_result_status": (asset_quality.get("result") or {}).get("status"),
        "viewer_mode": viewer_readiness.get("viewer_mode"),
        "viewer_ready": bool(viewer_readiness.get("is_viewer_ready")),
        "summary_status": cad_bom.summary.get("status"),
        "mismatch_status": cad_bom.mismatch.get("status"),
        "mismatch_reason": cad_bom.mismatch.get("reason"),
        "mismatch_line_key": cad_bom.mismatch.get("line_key"),
        "mismatch_analysis_scope": cad_bom.mismatch.get("analysis_scope"),
        "mismatch_recoverable": bool(cad_bom.mismatch.get("recoverable")),
        "mismatch_grouped_counters": cad_bom.mismatch.get("grouped_counters") or {},
        "mismatch_issue_codes": cad_bom.mismatch.get("issue_codes") or [],
        "asset_issue_codes": asset_quality.get("issue_codes") or [],
        "history_entries": len(history_entries),
        "has_stored_artifact": bool(file_container.cad_bom_path),
        "proof_files": proof_files,
    }
    links = {
        "structured_bom_url": f"/api/v1/cad/files/{file_container.id}/bom",
        "mismatch_url": f"/api/v1/cad/files/{file_container.id}/bom/mismatch",
        "proof_url": f"/api/v1/cad/files/{file_container.id}/proof?history_limit={history_limit}",
        "proof_decisions_url": (
            f"/api/v1/cad/files/{file_container.id}/proof/decisions?history_limit={history_limit}"
        ),
        "raw_bom_url": (
            f"/api/v1/file/{file_container.id}/cad_bom"
            if file_container.cad_bom_path
            else None
        ),
        "asset_quality_url": f"/api/v1/file/{file_container.id}/asset_quality",
        "viewer_readiness_url": f"/api/v1/file/{file_container.id}/viewer_readiness",
        "review_url": f"/api/v1/cad/files/{file_container.id}/review",
        "history_url": f"/api/v1/cad/files/{file_container.id}/history?limit={history_limit}",
        "reimport_url": f"/api/v1/cad/files/{file_container.id}/bom/reimport",
        "file_url": f"/api/v1/file/{file_container.id}",
    }
    return CadBomOperatorBundleResponse(
        exported_at=datetime.utcnow(),
        file=CadBomBundleFileInfo(
            file_id=file_container.id,
            filename=getattr(file_container, "filename", None),
            cad_connector_id=file_container.cad_connector_id,
            cad_format=file_container.cad_format,
            document_type=file_container.document_type,
            cad_review_state=file_container.cad_review_state,
            cad_review_note=file_container.cad_review_note,
            has_stored_artifact=bool(file_container.cad_bom_path),
        ),
        viewer_readiness=viewer_readiness,
        asset_quality=asset_quality,
        cad_bom=cad_bom,
        operator_proof=operator_proof,
        active_decision=active_decision,
        proof_decisions=proof_decisions,
        review=review,
        history=history_entries,
        proof_manifest=proof_manifest,
        links=links,
    )


class CadPropertiesResponse(BaseModel):
    file_id: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    updated_at: Optional[str] = None
    source: Optional[str] = None
    cad_document_schema_version: Optional[int] = None


class CadPropertiesUpdateRequest(BaseModel):
    properties: Dict[str, Any] = Field(default_factory=dict)
    source: Optional[str] = None


class CadEntityNote(BaseModel):
    entity_id: int
    note: str
    color: Optional[str] = None


class CadViewStateResponse(BaseModel):
    file_id: str
    hidden_entity_ids: List[int] = Field(default_factory=list)
    notes: List[CadEntityNote] = Field(default_factory=list)
    updated_at: Optional[str] = None
    source: Optional[str] = None
    cad_document_schema_version: Optional[int] = None


class CadViewStateUpdateRequest(BaseModel):
    hidden_entity_ids: Optional[List[int]] = None
    notes: Optional[List[CadEntityNote]] = None
    source: Optional[str] = None
    refresh_preview: bool = False


class CadReviewResponse(BaseModel):
    file_id: str
    state: Optional[str] = None
    note: Optional[str] = None
    reviewed_at: Optional[str] = None
    reviewed_by_id: Optional[int] = None


class CadReviewRequest(BaseModel):
    state: str
    note: Optional[str] = None


def _load_cad_bom_wrapper(file_container: FileContainer) -> Optional[Dict[str, Any]]:
    if not file_container.cad_bom_path:
        return None
    file_service = FileService()
    output_stream = io.BytesIO()
    try:
        file_service.download_file(file_container.cad_bom_path, output_stream)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"CAD BOM download failed: {exc}") from exc
    output_stream.seek(0)
    try:
        payload = json.load(output_stream)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="CAD BOM invalid JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="CAD BOM invalid JSON")
    return payload


def _csv_bytes(*, rows: List[Dict[str, Any]], columns: List[str]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(list(columns))
    for row in rows:
        out_row: List[str] = []
        for col in columns:
            value = (row or {}).get(col)
            if isinstance(value, (dict, list)):
                out_row.append(json.dumps(value, ensure_ascii=False, default=str))
            elif value is None:
                out_row.append("")
            else:
                out_row.append(str(value))
        writer.writerow(out_row)
    return buffer.getvalue().encode("utf-8-sig")


def _zip_bytes(*, files: Dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content or b"")
    return buffer.getvalue()


def _resolve_cad_bom_item_id(
    *,
    file_container: FileContainer,
    request_item_id: Optional[str],
    db: Session,
) -> str:
    item_id = (request_item_id or "").strip()
    if item_id:
        return item_id

    wrapper = _load_cad_bom_wrapper(file_container)
    stored_item_id = str((wrapper or {}).get("item_id") or "").strip()
    if stored_item_id:
        return stored_item_id

    attached_rows = (
        db.query(ItemFile)
        .filter(ItemFile.file_id == file_container.id)
        .order_by(ItemFile.created_at.asc())
        .all()
    )
    item_ids = sorted({str(row.item_id).strip() for row in attached_rows if str(row.item_id).strip()})
    if len(item_ids) == 1:
        return item_ids[0]
    if len(item_ids) > 1:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "cad_bom_reimport_item_ambiguous",
                "context": {
                    "file_id": file_container.id,
                    "item_ids": item_ids,
                },
            },
        )
    raise HTTPException(
        status_code=400,
        detail={
            "code": "cad_bom_reimport_item_missing",
            "context": {"file_id": file_container.id},
        },
    )


class CadDiffResponse(BaseModel):
    file_id: str
    other_file_id: str
    properties: Dict[str, Any]
    cad_document_schema_version: Dict[str, Optional[int]]


class CadChangeLogEntry(BaseModel):
    id: str
    action: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    user_id: Optional[int] = None


class CadChangeLogResponse(BaseModel):
    file_id: str
    entries: List[CadChangeLogEntry]


class CadMeshStatsResponse(BaseModel):
    file_id: str
    stats: Dict[str, Any]


def _build_cad_review_response(file_container: FileContainer) -> CadReviewResponse:
    reviewed_at = file_container.cad_reviewed_at
    return CadReviewResponse(
        file_id=file_container.id,
        state=file_container.cad_review_state,
        note=file_container.cad_review_note,
        reviewed_at=reviewed_at.isoformat() if reviewed_at else None,
        reviewed_by_id=file_container.cad_review_by_id,
    )


def _load_cad_history_entries(
    *,
    file_container: FileContainer,
    db: Session,
    limit: int,
) -> List[CadChangeLogEntry]:
    logs = (
        db.query(CadChangeLog)
        .filter(CadChangeLog.file_id == file_container.id)
        .order_by(CadChangeLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        CadChangeLogEntry(
            id=log.id,
            action=log.action,
            payload=log.payload or {},
            created_at=log.created_at.isoformat(),
            user_id=log.user_id,
        )
        for log in logs
    ]


def _build_cad_bom_response(
    *,
    file_container: FileContainer,
    db: Session,
) -> CadBomResponse:
    if file_container.cad_bom_path:
        payload = _load_cad_bom_wrapper(file_container)
        mismatch = build_cad_bom_mismatch_analysis(
            session=db,
            root_item_id=payload.get("item_id"),
            bom_payload=payload.get("bom") or {},
        )
        return CadBomResponse(
            file_id=file_container.id,
            item_id=payload.get("item_id"),
            imported_at=payload.get("imported_at"),
            import_result=payload.get("import_result") or {},
            bom=payload.get("bom") or {},
            job_status="completed",
            summary=build_cad_bom_operator_summary(
                import_result=payload.get("import_result") or {},
                bom_payload=payload.get("bom") or {},
                has_artifact=True,
            ),
            mismatch=mismatch,
        )

    jobs = (
        db.query(ConversionJob)
        .filter(ConversionJob.task_type == "cad_bom")
        .order_by(ConversionJob.created_at.desc())
        .limit(50)
        .all()
    )
    matched_job = None
    for job in jobs:
        payload = job.payload or {}
        if str(payload.get("file_id") or "") == file_container.id:
            matched_job = job
            break

    if not matched_job:
        raise HTTPException(status_code=404, detail="No cad_bom data found")

    payload = matched_job.payload or {}
    result = payload.get("result") or {}
    imported_at = matched_job.completed_at or matched_job.created_at
    mismatch = build_cad_bom_mismatch_analysis(
        session=db,
        root_item_id=payload.get("item_id"),
        bom_payload=result.get("bom") or {},
    )

    return CadBomResponse(
        file_id=file_container.id,
        item_id=payload.get("item_id"),
        job_id=matched_job.id,
        job_status=matched_job.status,
        imported_at=imported_at.isoformat() if imported_at else None,
        import_result=result.get("import_result") or {},
        bom=result.get("bom") or {},
        summary=build_cad_bom_operator_summary(
            import_result=result.get("import_result") or {},
            bom_payload=result.get("bom") or {},
            has_artifact=bool(file_container.cad_bom_path),
        ),
        mismatch=mismatch,
    )


def _calculate_checksum(content: bytes) -> str:
    import hashlib

    return hashlib.sha256(content).hexdigest()


def _get_mime_type(filename: str) -> str:
    import mimetypes

    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"


def _validate_upload(filename: str, file_size: int) -> None:
    settings = get_settings()
    max_bytes = settings.FILE_UPLOAD_MAX_BYTES
    if max_bytes and file_size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail={
                "code": "FILE_TOO_LARGE",
                "max_bytes": max_bytes,
                "file_size": file_size,
            },
        )

    allowed = {
        ext.strip().lower().lstrip(".")
        for ext in settings.FILE_ALLOWED_EXTENSIONS.split(",")
        if ext.strip()
    }
    if allowed:
        ext = Path(filename).suffix.lower().lstrip(".")
        if ext not in allowed:
            raise HTTPException(
                status_code=415,
                detail={
                    "code": "FILE_TYPE_NOT_ALLOWED",
                    "extension": ext,
                },
            )


def _get_document_type(extension: str) -> str:
    ext = extension.lower().lstrip(".")
    # Treat common 2D drawing formats (including rendered images) as "2d"
    # so dedup rules (document_type=2d) can apply consistently.
    if ext in {"dwg", "dxf", "pdf", "png", "jpg", "jpeg"}:
        return "2d"
    if ext in {
        "step",
        "stp",
        "iges",
        "igs",
        "stl",
        "obj",
        "gltf",
        "glb",
        "sldprt",
        "sldasm",
        "ipt",
        "iam",
        "prt",
        "asm",
        "catpart",
        "catproduct",
        "par",
        "psm",
        "3dm",
    }:
        return "3d"
    return "other"


def _build_cad_viewer_url(request: Request, file_id: str, cad_manifest_path: Optional[str]) -> Optional[str]:
    if not cad_manifest_path:
        return None
    settings = get_settings()
    base_url = (
        settings.CADGF_ROUTER_PUBLIC_BASE_URL
        or settings.CADGF_ROUTER_BASE_URL
        or ""
    ).strip()
    if not base_url:
        return None
    manifest_url = f"{request.url_for('get_cad_manifest', file_id=file_id)}?rewrite=1"
    manifest_param = quote(str(manifest_url), safe="")
    return f"{base_url.rstrip('/')}/tools/web_viewer/index.html?manifest={manifest_param}"


def _json_text(expr):
    if hasattr(expr, "as_string"):
        return expr.as_string()
    if hasattr(expr, "astext"):
        return expr.astext
    return cast(expr, String)


def _normalize_text(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_filename_attrs(stem: str) -> Dict[str, str]:
    stem = stem.strip()
    if not stem:
        return {}

    attrs: Dict[str, str] = {}
    revision = None

    match = _FILENAME_REV_RE.search(stem)
    if match:
        revision = match.group(1)
        stem = stem[: match.start()].rstrip(" _-")
    else:
        match = _FILENAME_VER_RE.search(stem)
        if match:
            revision = f"v{match.group(1)}"
            stem = stem[: match.start()].rstrip(" _-")

    if revision:
        attrs["revision"] = revision

    if stem:
        attrs.setdefault("description", stem)

    return attrs


def _build_auto_part_properties(
    item_type: ItemType, attrs: Dict[str, Any], filename: Optional[str]
) -> tuple[str, Dict[str, Any]]:
    attributes = dict(attrs or {})
    lower_attributes = {str(k).lower(): v for k, v in attributes.items()}
    prop_defs = {prop.name: prop for prop in (item_type.properties or [])}

    def _get_value(*keys: str) -> Optional[Any]:
        for key in keys:
            if key in attributes:
                return attributes[key]
            lower = key.lower()
            if lower in lower_attributes:
                return lower_attributes[lower]
        return None

    def _apply_length_limit(name: str, value: Optional[Any]) -> Optional[Any]:
        if value is None:
            return None
        text = str(value)
        prop = prop_defs.get(name)
        max_len = getattr(prop, "length", None) if prop else None
        if isinstance(max_len, int) and max_len > 0 and len(text) > max_len:
            return text[:max_len]
        return value

    def _looks_like_uuid(value: Optional[str]) -> bool:
        if not value:
            return False
        text = value.strip()
        if len(text) < 24:
            return False
        hex_part = text.replace("-", "")
        if len(hex_part) < 24:
            return False
        if not all(c in "0123456789abcdefABCDEF" for c in hex_part):
            return False
        if text.count("-") >= 2:
            return True
        return len(hex_part) in (24, 32)

    item_number = _get_value(
        "part_number",
        "item_number",
        "item_no",
        "number",
        "drawing_no",
        "drawing_number",
    )
    if not item_number:
        stem = Path(filename).stem if filename else ""
        item_number = stem or f"PART-{uuid.uuid4().hex[:8]}"

    item_number = _normalize_text(item_number) or f"PART-{uuid.uuid4().hex[:8]}"
    stem = Path(filename).stem if filename else ""
    if stem and _looks_like_uuid(item_number):
        item_number = stem
    item_number = _apply_length_limit("item_number", item_number) or item_number
    prop_names = {prop.name for prop in (item_type.properties or [])}
    props: Dict[str, Any] = {}

    if "item_number" in prop_names:
        props["item_number"] = item_number

    description = _normalize_text(_get_value("description", "title", "name"))
    if description and "description" in prop_names:
        props["description"] = _apply_length_limit("description", description) or description

    if "name" in prop_names:
        props["name"] = _apply_length_limit("name", description or item_number) or (
            description or item_number
        )

    revision = _normalize_text(_get_value("revision", "rev"))
    if revision and "revision" in prop_names:
        props["revision"] = _apply_length_limit("revision", revision) or revision

    if filename:
        parsed = _parse_filename_attrs(Path(filename).stem)
        if "description" not in props and "description" in prop_names:
            parsed_desc = _normalize_text(parsed.get("description"))
            if parsed_desc:
                props["description"] = _apply_length_limit("description", parsed_desc) or parsed_desc
                if "name" in prop_names and not props.get("name"):
                    props["name"] = _apply_length_limit("name", parsed_desc) or parsed_desc
        if "revision" not in props and "revision" in prop_names:
            parsed_rev = _normalize_text(parsed.get("revision"))
            if parsed_rev:
                props["revision"] = _apply_length_limit("revision", parsed_rev) or parsed_rev

    for prop in item_type.properties or []:
        if prop.name in props or not prop.is_cad_synced:
            continue
        cad_key = resolve_cad_sync_key(prop.name, prop.ui_options)
        value = _get_value(cad_key)
        if value is not None:
            props[prop.name] = value

    return item_number, props


def _build_missing_updates(
    existing: Optional[Dict[str, Any]], incoming: Dict[str, Any]
) -> Dict[str, Any]:
    existing = existing or {}
    updates: Dict[str, Any] = {}

    for key, value in incoming.items():
        if value is None:
            continue
        current = existing.get(key)
        if current is None:
            updates[key] = value
            continue
        if isinstance(current, str) and not current.strip():
            updates[key] = value

    return updates


def _get_cad_format(extension: str) -> Optional[str]:
    ext = extension.lower().lstrip(".")
    cad_formats = {
        "step": "STEP",
        "stp": "STEP",
        "iges": "IGES",
        "igs": "IGES",
        "sldprt": "SOLIDWORKS",
        "sldasm": "SOLIDWORKS",
        "ipt": "INVENTOR",
        "iam": "INVENTOR",
        "prt": "NX",
        "asm": "NX",
        "catpart": "CATIA",
        "catproduct": "CATIA",
        "par": "SOLID_EDGE",
        "psm": "SOLID_EDGE",
        "3dm": "RHINO",
        "dwg": "AUTOCAD",
        "dxf": "AUTOCAD",
        "stl": "STL",
        "obj": "OBJ",
        "gltf": "GLTF",
        "glb": "GLTF",
        "pdf": "PDF",
    }
    return cad_formats.get(ext)


def _resolve_cad_metadata(
    extension: str,
    override_format: Optional[str],
    connector_id: Optional[str],
    *,
    content: Optional[bytes] = None,
    filename: Optional[str] = None,
    source_system: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    connector = None
    if connector_id:
        connector = cad_registry.find_by_id(connector_id)
    if not connector and override_format:
        connector = cad_registry.find_by_format(override_format)
    if not connector:
        connector = cad_registry.detect_by_content(
            content,
            filename=filename,
            source_system=source_system,
        )
    if not connector:
        connector = cad_registry.resolve(None, extension)

    if connector:
        return {
            "cad_format": connector.info.cad_format,
            "document_type": connector.info.document_type,
            "connector_id": connector.info.id,
        }

    resolved = cad_registry.resolve_metadata(override_format, extension)
    cad_format = resolved.cad_format or _get_cad_format(extension)
    document_type = resolved.document_type or _get_document_type(extension)
    return {
        "cad_format": cad_format,
        "document_type": document_type,
        "connector_id": resolved.connector_id,
    }


@router.get("/connectors", response_model=List[CadConnectorInfoResponse])
def list_cad_connectors() -> List[CadConnectorInfoResponse]:
    connectors = sorted(cad_registry.list(), key=lambda info: info.id)
    return [
        CadConnectorInfoResponse(
            id=info.id,
            label=info.label,
            cad_format=info.cad_format,
            document_type=info.document_type,
            extensions=list(info.extensions),
            aliases=list(info.aliases),
            priority=info.priority,
            description=info.description,
        )
        for info in connectors
    ]


@router.get("/capabilities", response_model=CadCapabilitiesResponse)
def get_cad_capabilities() -> CadCapabilitiesResponse:
    settings = get_settings()
    connectors = sorted(cad_registry.list(), key=lambda info: info.id)

    def _collect(values):
        return sorted({v for v in values if v})

    formats_2d = _collect(
        info.cad_format for info in connectors if info.document_type == "2d"
    )
    formats_3d = _collect(
        info.cad_format for info in connectors if info.document_type == "3d"
    )
    extensions_2d = _collect(
        ext
        for info in connectors
        if info.document_type == "2d"
        for ext in info.extensions
    )
    extensions_3d = _collect(
        ext
        for info in connectors
        if info.document_type == "3d"
        for ext in info.extensions
    )

    cad_connector_enabled = bool(settings.CAD_CONNECTOR_BASE_URL) and (
        (settings.CAD_CONNECTOR_MODE or "optional").strip().lower() != "disabled"
    )
    cad_extractor_enabled = bool(settings.CAD_EXTRACTOR_BASE_URL)
    cad_ml_enabled = bool(settings.CAD_ML_BASE_URL)
    cadgf_enabled = bool(settings.CADGF_ROUTER_BASE_URL)

    preview_modes = ["local"]
    if cad_ml_enabled:
        preview_modes.append("cad_ml")
    if cad_connector_enabled:
        preview_modes.append("connector")

    geometry_modes = ["local"]
    if cad_connector_enabled:
        geometry_modes.append("connector")
    if cadgf_enabled:
        geometry_modes.append("cadgf")

    extract_modes = ["local"]
    if cad_extractor_enabled:
        extract_modes.append("extractor")
    if cad_connector_enabled:
        extract_modes.append("connector")

    features = {
        "preview": CadCapabilityMode(
            available=True,
            modes=preview_modes,
            **_feature_status(
                available=True,
                modes=preview_modes,
                has_local_fallback=True,
                remote_modes=["cad_ml", "connector"],
            ),
        ),
        "geometry": CadCapabilityMode(
            available=True,
            modes=geometry_modes,
            **_feature_status(
                available=True,
                modes=geometry_modes,
                has_local_fallback=True,
                remote_modes=["connector", "cadgf"],
            ),
        ),
        "extract": CadCapabilityMode(
            available=True,
            modes=extract_modes,
            **_feature_status(
                available=True,
                modes=extract_modes,
                has_local_fallback=True,
                remote_modes=["extractor", "connector"],
            ),
        ),
        "bom": CadCapabilityMode(
            available=cad_connector_enabled,
            modes=["connector"] if cad_connector_enabled else [],
            note="Requires CAD connector service",
            **_feature_status(
                available=cad_connector_enabled,
                modes=["connector"] if cad_connector_enabled else [],
                has_local_fallback=False,
                remote_modes=["connector"],
                disabled_reason="CAD connector service not configured",
            ),
        ),
        "manifest": CadCapabilityMode(
            available=cadgf_enabled,
            modes=["cadgf"] if cadgf_enabled else [],
            note="CADGF router produces manifest/document/metadata",
            **_feature_status(
                available=cadgf_enabled,
                modes=["cadgf"] if cadgf_enabled else [],
                has_local_fallback=False,
                remote_modes=["cadgf"],
                disabled_reason="CADGF router not configured",
            ),
        ),
        "metadata": CadCapabilityMode(
            available=True,
            modes=["extract", "cadgf"] if cadgf_enabled else ["extract"],
            **_feature_status(
                available=True,
                modes=["extract", "cadgf"] if cadgf_enabled else ["extract"],
                has_local_fallback=True,
                remote_modes=["cadgf"],
            ),
        ),
    }

    return CadCapabilitiesResponse(
        connectors=[
            CadConnectorInfoResponse(
                id=info.id,
                label=info.label,
                cad_format=info.cad_format,
                document_type=info.document_type,
                extensions=list(info.extensions),
                aliases=list(info.aliases),
                priority=info.priority,
                description=info.description,
            )
            for info in connectors
        ],
        counts={
            "total": len(connectors),
            "2d": len([c for c in connectors if c.document_type == "2d"]),
            "3d": len([c for c in connectors if c.document_type == "3d"]),
        },
        formats={"2d": formats_2d, "3d": formats_3d},
        extensions={"2d": extensions_2d, "3d": extensions_3d},
        features=features,
        integrations={
            "cad_connector": {
                "configured": bool(settings.CAD_CONNECTOR_BASE_URL),
                "enabled": cad_connector_enabled,
                "mode": settings.CAD_CONNECTOR_MODE,
                "base_url": settings.CAD_CONNECTOR_BASE_URL or None,
                **_integration_status(
                    configured=bool(settings.CAD_CONNECTOR_BASE_URL),
                    available=cad_connector_enabled,
                    fallback_reason="local fallback only"
                    if not cad_connector_enabled
                    else None,
                    disabled_reason="CAD connector mode disabled"
                    if bool(settings.CAD_CONNECTOR_BASE_URL)
                    and not cad_connector_enabled
                    else "CAD connector service not configured",
                ),
            },
            "cad_extractor": {
                "configured": cad_extractor_enabled,
                "mode": settings.CAD_EXTRACTOR_MODE,
                "base_url": settings.CAD_EXTRACTOR_BASE_URL or None,
                **_integration_status(
                    configured=cad_extractor_enabled,
                    available=cad_extractor_enabled,
                    fallback_reason="local fallback only"
                    if not cad_extractor_enabled
                    else None,
                    disabled_reason="CAD extractor not configured",
                ),
            },
            "cad_ml": {
                "configured": cad_ml_enabled,
                "base_url": settings.CAD_ML_BASE_URL or None,
                **_integration_status(
                    configured=cad_ml_enabled,
                    available=cad_ml_enabled,
                    fallback_reason="local fallback only"
                    if not cad_ml_enabled
                    else None,
                    disabled_reason="CAD ML service not configured",
                ),
            },
            "cadgf_router": {
                "configured": cadgf_enabled,
                "base_url": settings.CADGF_ROUTER_BASE_URL or None,
                **_integration_status(
                    configured=cadgf_enabled,
                    available=cadgf_enabled,
                    fallback_reason=None,
                    disabled_reason="CADGF router not configured",
                ),
            },
        },
    )


@router.post("/connectors/reload", response_model=CadConnectorReloadResponse)
def reload_cad_connectors(
    req: CadConnectorReloadRequest,
    _: CurrentUser = Depends(require_admin),
) -> CadConnectorReloadResponse:
    settings = get_settings()
    config_path = req.config_path
    if config_path and not settings.CAD_CONNECTORS_ALLOW_PATH_OVERRIDE:
        raise HTTPException(
            status_code=403,
            detail="Path override disabled (set CAD_CONNECTORS_ALLOW_PATH_OVERRIDE=true)",
        )
    if req.config is not None:
        result = reload_connectors(config_payload=req.config)
    else:
        result = reload_connectors(config_path=config_path)
    return CadConnectorReloadResponse(
        config_path=config_path or settings.CAD_CONNECTORS_CONFIG_PATH or None,
        custom_loaded=len(result.entries),
        errors=result.errors,
    )


def _csv_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return None


@router.get("/sync-template/{item_type_id}", response_model=CadSyncTemplateResponse)
def get_cad_sync_template(
    item_type_id: str,
    output_format: str = "csv",
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    item_type = db.query(ItemType).filter(ItemType.id == item_type_id).first()
    if not item_type:
        raise HTTPException(status_code=404, detail="ItemType not found")

    rows: List[CadSyncTemplateRow] = []
    for prop in item_type.properties or []:
        cad_key = None
        if prop.is_cad_synced:
            cad_key = resolve_cad_sync_key(prop.name, prop.ui_options)
        rows.append(
            CadSyncTemplateRow(
                property_name=prop.name,
                label=prop.label,
                data_type=prop.data_type,
                is_cad_synced=bool(prop.is_cad_synced),
                cad_key=cad_key,
            )
        )

    if output_format.lower() == "json":
        return CadSyncTemplateResponse(item_type_id=item_type_id, properties=rows)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["property_name", "label", "data_type", "is_cad_synced", "cad_key"])
    for row in rows:
        writer.writerow(
            [
                row.property_name,
                row.label or "",
                row.data_type or "",
                "true" if row.is_cad_synced else "false",
                row.cad_key or "",
            ]
        )
    output.seek(0)
    filename = f"cad_sync_template_{item_type_id}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=output.getvalue(), media_type="text/csv", headers=headers)


@router.post("/sync-template/{item_type_id}", response_model=CadSyncTemplateApplyResponse)
async def apply_cad_sync_template(
    item_type_id: str,
    file: UploadFile = File(...),
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> CadSyncTemplateApplyResponse:
    item_type = db.query(ItemType).filter(ItemType.id == item_type_id).first()
    if not item_type:
        raise HTTPException(status_code=404, detail="ItemType not found")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Empty template file")

    text = payload.decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    props_by_name = {prop.name: prop for prop in (item_type.properties or [])}

    updated = 0
    skipped = 0
    missing: List[str] = []

    for row in reader:
        name = (row.get("property_name") or row.get("name") or "").strip()
        if not name:
            skipped += 1
            continue
        prop = props_by_name.get(name)
        if not prop:
            missing.append(name)
            continue

        cad_key = (row.get("cad_key") or row.get("cad_attribute") or "").strip()
        sync_flag = _csv_bool(row.get("is_cad_synced"))
        changed = False

        if sync_flag is not None and prop.is_cad_synced != sync_flag:
            prop.is_cad_synced = sync_flag
            changed = True

        if cad_key or sync_flag:
            ui_opts = prop.ui_options
            if isinstance(ui_opts, str):
                try:
                    ui_opts = json.loads(ui_opts)
                except Exception:
                    ui_opts = {}
            if not isinstance(ui_opts, dict):
                ui_opts = {}
            if cad_key:
                ui_opts["cad_key"] = cad_key
            else:
                ui_opts.pop("cad_key", None)
            prop.ui_options = ui_opts
            changed = True

        if changed:
            db.add(prop)
            updated += 1
        else:
            skipped += 1

    if updated:
        item_type.properties_schema = None
        db.add(item_type)
    db.commit()

    return CadSyncTemplateApplyResponse(
        item_type_id=item_type_id,
        updated=updated,
        skipped=skipped,
        missing=missing,
    )


@router.get("/files/{file_id}/attributes", response_model=CadExtractAttributesResponse)
def get_cad_attributes(
    file_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadExtractAttributesResponse:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    if file_container.cad_attributes is not None:
        extracted_at = file_container.cad_attributes_updated_at
        return CadExtractAttributesResponse(
            file_id=file_container.id,
            cad_format=file_container.cad_format,
            cad_connector_id=file_container.cad_connector_id,
            job_id=None,
            job_status="completed",
            extracted_at=extracted_at.isoformat() if extracted_at else None,
            extracted_attributes=file_container.cad_attributes or {},
            source=file_container.cad_attributes_source,
        )

    jobs = (
        db.query(ConversionJob)
        .filter(ConversionJob.task_type == "cad_extract")
        .order_by(ConversionJob.created_at.desc())
        .limit(50)
        .all()
    )
    matched_job = None
    for job in jobs:
        payload = job.payload or {}
        if str(payload.get("file_id") or "") == file_id:
            matched_job = job
            break

    if not matched_job:
        raise HTTPException(status_code=404, detail="No cad_extract data found")

    payload = matched_job.payload or {}
    result = payload.get("result") or {}
    extracted_attributes = result.get("extracted_attributes") or {}
    extracted_at = matched_job.completed_at or matched_job.created_at

    return CadExtractAttributesResponse(
        file_id=file_container.id,
        cad_format=file_container.cad_format,
        cad_connector_id=file_container.cad_connector_id,
        job_id=matched_job.id,
        job_status=matched_job.status,
        extracted_at=extracted_at.isoformat() if extracted_at else None,
        extracted_attributes=extracted_attributes,
        source=result.get("source"),
    )


@router.get("/files/{file_id}/bom", response_model=CadBomResponse)
def get_cad_bom(
    file_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadBomResponse:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")
    return _build_cad_bom_response(file_container=file_container, db=db)


@router.get("/files/{file_id}/bom/mismatch")
def get_cad_bom_mismatch(
    file_id: str,
    history_limit: int = Query(20, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    cad_bom = _build_cad_bom_response(file_container=file_container, db=db)
    mismatch = dict(cad_bom.mismatch or {})
    mismatch["file_id"] = file_container.id
    mismatch["item_id"] = cad_bom.item_id
    mismatch["links"] = _mismatch_links(file_id, history_limit)
    return mismatch


@router.get("/files/{file_id}/proof", response_model=CadBomOperatorBundleResponse)
def get_cad_operator_proof(
    file_id: str,
    history_limit: int = Query(20, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadBomOperatorBundleResponse:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")
    return _build_cad_operator_bundle(
        file_container=file_container,
        db=db,
        history_limit=history_limit,
    )


@router.get("/files/{file_id}/proof/decisions", response_model=CadProofDecisionListResponse)
def get_cad_operator_proof_decisions(
    file_id: str,
    history_limit: int = Query(20, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadProofDecisionListResponse:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")
    bundle = _build_cad_operator_bundle(
        file_container=file_container,
        db=db,
        history_limit=history_limit,
    )
    return CadProofDecisionListResponse(
        file_id=file_container.id,
        current_fingerprint=str(bundle.operator_proof.get("proof_fingerprint") or "").strip() or None,
        active_decision=bundle.active_decision,
        entries=bundle.proof_decisions,
    )


@router.post("/files/{file_id}/proof/decisions", response_model=CadProofDecisionEntry)
def record_cad_operator_proof_decision(
    file_id: str,
    payload: CadProofDecisionRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadProofDecisionEntry:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    bundle = _build_cad_operator_bundle(
        file_container=file_container,
        db=db,
        history_limit=50,
    )
    operator_proof = bundle.operator_proof
    if operator_proof.get("status") == "ready":
        raise HTTPException(
            status_code=400,
            detail={
                "code": "cad_operator_proof_ready_no_decision_required",
                "context": {"file_id": file_container.id},
            },
        )

    decision = str(payload.decision or "").strip().lower()
    if decision not in CAD_PROOF_ALLOWED_DECISIONS:
        raise HTTPException(status_code=400, detail=f"Invalid proof decision: {decision}")

    scope = str(payload.scope or "full_proof").strip().lower() or "full_proof"
    if scope not in CAD_PROOF_ALLOWED_SCOPES:
        raise HTTPException(status_code=400, detail=f"Invalid proof scope: {scope}")

    comment = str(payload.comment or "").strip()
    if not comment:
        raise HTTPException(status_code=400, detail="Proof decision comment is required")

    reason_code = str(payload.reason_code or "").strip() or None
    if decision == "waived" and not reason_code:
        raise HTTPException(status_code=400, detail="Proof waiver reason_code is required")

    current_issue_codes = _dedupe_text(list(operator_proof.get("issue_codes") or []))
    decision_issue_codes = _dedupe_text(list(payload.issue_codes or [])) or current_issue_codes
    unknown_issue_codes = sorted(set(decision_issue_codes) - set(current_issue_codes))
    if unknown_issue_codes:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "cad_operator_proof_issue_codes_unknown",
                "context": {
                    "file_id": file_container.id,
                    "issue_codes": unknown_issue_codes,
                },
            },
        )

    expires_at = _normalize_optional_iso_datetime(payload.expires_at)
    action = next(
        key for key, value in CAD_PROOF_DECISION_ACTIONS.items() if value == decision
    )
    entry = _log_cad_change(
        db,
        file_container,
        action,
        {
            "decision": decision,
            "scope": scope,
            "comment": comment,
            "reason_code": reason_code,
            "issue_codes": decision_issue_codes,
            "proof_fingerprint": operator_proof.get("proof_fingerprint"),
            "proof_status": operator_proof.get("status"),
            "proof_gaps": operator_proof.get("proof_gaps") or [],
            "asset_quality_status": operator_proof.get("asset_quality_status"),
            "mismatch_status": operator_proof.get("mismatch_status"),
            "review_state": operator_proof.get("review_state"),
            "expires_at": expires_at,
            "links": {
                "proof_url": bundle.links.get("proof_url"),
                "proof_decisions_url": bundle.links.get("proof_decisions_url"),
                "export_url": f"/api/v1/cad/files/{file_container.id}/bom/export",
            },
        },
        user,
    )
    db.add(file_container)
    db.commit()

    return CadProofDecisionEntry(
        id=entry.id,
        decision=decision,
        scope=scope,
        comment=comment,
        reason_code=reason_code,
        issue_codes=decision_issue_codes,
        proof_fingerprint=str(operator_proof.get("proof_fingerprint") or "").strip() or None,
        proof_status=str(operator_proof.get("status") or "").strip() or None,
        proof_gaps=_dedupe_text(list(operator_proof.get("proof_gaps") or [])),
        asset_quality_status=str(operator_proof.get("asset_quality_status") or "").strip() or None,
        mismatch_status=str(operator_proof.get("mismatch_status") or "").strip() or None,
        review_state=str(operator_proof.get("review_state") or "").strip() or None,
        expires_at=expires_at,
        created_at=entry.created_at.isoformat(),
        user_id=user.id,
        is_current=True,
        covers_current_proof=bool(
            scope == "full_proof"
            or set(current_issue_codes).issubset(set(decision_issue_codes))
        ),
    )


@router.get("/files/{file_id}/bom/export")
def export_cad_bom_bundle(
    file_id: str,
    export_format: str = Query("zip", description="zip|json"),
    history_limit: int = Query(20, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    bundle = _build_cad_operator_bundle(
        file_container=file_container,
        db=db,
        history_limit=history_limit,
    )
    payload = bundle.model_dump(mode="json")
    fmt = (export_format or "").strip().lower()

    if fmt in {"json", "application/json"}:
        content = json.dumps(payload, ensure_ascii=False, default=str, indent=2).encode("utf-8")
        headers = {"Content-Disposition": f'attachment; filename="cad-bom-ops-{file_id}.json"'}
        return Response(content=content, media_type="application/json", headers=headers)

    if fmt != "zip":
        raise HTTPException(status_code=400, detail="Unsupported export format")

    cad_bom = bundle.cad_bom
    review = bundle.review
    history_entries = bundle.history
    history_rows = [entry.model_dump(mode="json") for entry in history_entries]
    proof_decision_rows = [entry.model_dump(mode="json") for entry in bundle.proof_decisions]
    recovery_rows = list(cad_bom.summary.get("recovery_actions") or [])
    issue_rows = [
        {"code": code}
        for code in (cad_bom.summary.get("issue_codes") or [])
    ]
    asset_quality_rows = [
        {"code": code}
        for code in (bundle.asset_quality.get("issue_codes") or [])
    ]
    asset_recovery_rows = list(bundle.asset_quality.get("recovery_actions") or [])
    mismatch_rows = list(cad_bom.mismatch.get("rows") or [])
    mismatch_issue_rows = [
        {"code": code}
        for code in (cad_bom.mismatch.get("issue_codes") or [])
    ]
    mismatch_recovery_rows = list(cad_bom.mismatch.get("recovery_actions") or [])
    bundle_bytes = _zip_bytes(
        files={
            "bundle.json": json.dumps(payload, ensure_ascii=False, default=str, indent=2).encode(
                "utf-8"
            ),
            "file.json": json.dumps(
                bundle.file.model_dump(mode="json"),
                ensure_ascii=False,
                default=str,
                indent=2,
            ).encode("utf-8"),
            "operator_proof.json": json.dumps(
                bundle.operator_proof,
                ensure_ascii=False,
                default=str,
                indent=2,
            ).encode("utf-8"),
            "active_decision.json": json.dumps(
                bundle.active_decision.model_dump(mode="json") if bundle.active_decision else {},
                ensure_ascii=False,
                default=str,
                indent=2,
            ).encode("utf-8"),
            "proof_decisions.json": json.dumps(
                proof_decision_rows,
                ensure_ascii=False,
                default=str,
                indent=2,
            ).encode("utf-8"),
            "viewer_readiness.json": json.dumps(
                bundle.viewer_readiness,
                ensure_ascii=False,
                default=str,
                indent=2,
            ).encode("utf-8"),
            "asset_quality.json": json.dumps(
                bundle.asset_quality,
                ensure_ascii=False,
                default=str,
                indent=2,
            ).encode("utf-8"),
            "summary.json": json.dumps(
                cad_bom.summary,
                ensure_ascii=False,
                default=str,
                indent=2,
            ).encode("utf-8"),
            "review.json": json.dumps(
                review.model_dump(mode="json"),
                ensure_ascii=False,
                default=str,
                indent=2,
            ).encode("utf-8"),
            "import_result.json": json.dumps(
                cad_bom.import_result,
                ensure_ascii=False,
                default=str,
                indent=2,
            ).encode("utf-8"),
            "bom.json": json.dumps(
                cad_bom.bom,
                ensure_ascii=False,
                default=str,
                indent=2,
            ).encode("utf-8"),
            "mismatch.json": json.dumps(
                cad_bom.mismatch,
                ensure_ascii=False,
                default=str,
                indent=2,
            ).encode("utf-8"),
            "live_bom.json": json.dumps(
                cad_bom.mismatch.get("live_bom") or {},
                ensure_ascii=False,
                default=str,
                indent=2,
            ).encode("utf-8"),
            "history.json": json.dumps(
                history_rows,
                ensure_ascii=False,
                default=str,
                indent=2,
            ).encode("utf-8"),
            "history.csv": _csv_bytes(
                rows=history_rows,
                columns=["id", "action", "created_at", "user_id", "payload"],
            ),
            "proof_decisions.csv": _csv_bytes(
                rows=proof_decision_rows,
                columns=[
                    "id",
                    "decision",
                    "scope",
                    "comment",
                    "reason_code",
                    "issue_codes",
                    "proof_fingerprint",
                    "proof_status",
                    "proof_gaps",
                    "asset_quality_status",
                    "mismatch_status",
                    "review_state",
                    "expires_at",
                    "created_at",
                    "user_id",
                    "is_current",
                    "covers_current_proof",
                ],
            ),
            "recovery_actions.csv": _csv_bytes(
                rows=recovery_rows,
                columns=["code", "label"],
            ),
            "issue_codes.csv": _csv_bytes(rows=issue_rows, columns=["code"]),
            "asset_quality_issue_codes.csv": _csv_bytes(
                rows=asset_quality_rows,
                columns=["code"],
            ),
            "asset_quality_recovery_actions.csv": _csv_bytes(
                rows=asset_recovery_rows,
                columns=["code", "label"],
            ),
            "mismatch_delta.csv": _csv_bytes(
                rows=mismatch_rows,
                columns=[
                    "line_key",
                    "parent_id",
                    "child_id",
                    "status",
                    "quantity_before",
                    "quantity_after",
                    "quantity_delta",
                    "uom_before",
                    "uom_after",
                    "severity",
                    "change_fields",
                ],
            ),
            "mismatch_rows.csv": _csv_bytes(
                rows=mismatch_rows,
                columns=[
                    "line_key",
                    "parent_id",
                    "child_id",
                    "status",
                    "quantity_before",
                    "quantity_after",
                    "quantity_delta",
                    "uom_before",
                    "uom_after",
                    "severity",
                    "change_fields",
                ],
            ),
            "mismatch_issue_codes.csv": _csv_bytes(
                rows=mismatch_issue_rows,
                columns=["code"],
            ),
            "mismatch_recovery_actions.csv": _csv_bytes(
                rows=mismatch_recovery_rows,
                columns=["code", "label"],
            ),
            "mismatch_delta_preview.json": json.dumps(
                cad_bom.mismatch.get("delta_preview") or {},
                ensure_ascii=False,
                default=str,
                indent=2,
            ).encode("utf-8"),
            "proof_manifest.json": json.dumps(
                bundle.proof_manifest,
                ensure_ascii=False,
                default=str,
                indent=2,
            ).encode("utf-8"),
            "README.txt": (
                "YuantusPLM CAD operator proof bundle\n"
                f"file_id={file_id}\n"
                f"exported_at={bundle.exported_at.isoformat()}\n"
                f"structured_bom_url=/api/v1/cad/files/{file_id}/bom\n"
                f"mismatch_url=/api/v1/cad/files/{file_id}/bom/mismatch\n"
                f"proof_url=/api/v1/cad/files/{file_id}/proof?history_limit={history_limit}\n"
                f"proof_decisions_url=/api/v1/cad/files/{file_id}/proof/decisions?history_limit={history_limit}\n"
                f"raw_bom_url={bundle.links['raw_bom_url'] or ''}\n"
                f"asset_quality_url=/api/v1/file/{file_id}/asset_quality\n"
                f"viewer_readiness_url=/api/v1/file/{file_id}/viewer_readiness\n"
                f"review_url=/api/v1/cad/files/{file_id}/review\n"
                f"history_url=/api/v1/cad/files/{file_id}/history?limit={history_limit}\n"
                f"reimport_url=/api/v1/cad/files/{file_id}/bom/reimport\n"
                f"operator_proof_status={bundle.operator_proof.get('status') or 'unavailable'}\n"
                f"decision_status={bundle.operator_proof.get('decision_status') or 'unavailable'}\n"
                f"active_decision_id={bundle.operator_proof.get('active_decision_id') or ''}\n"
                f"asset_quality_status={bundle.asset_quality.get('status') or 'unavailable'}\n"
                f"mismatch_status={cad_bom.mismatch.get('status') or 'unavailable'}\n"
                f"proof_manifest_file=proof_manifest.json\n"
            ).encode("utf-8"),
        }
    )
    headers = {"Content-Disposition": f'attachment; filename="cad-bom-ops-{file_id}.zip"'}
    return StreamingResponse(
        io.BytesIO(bundle_bytes),
        media_type="application/zip",
        headers=headers,
    )


@router.post("/files/{file_id}/bom/reimport", response_model=CadBomReimportResponse)
def reimport_cad_bom(
    file_id: str,
    payload: CadBomReimportRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadBomReimportResponse:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    item_id = _resolve_cad_bom_item_id(
        file_container=file_container,
        request_item_id=payload.item_id,
        db=db,
    )
    job_service = JobService(db)
    auth_header = request.headers.get("authorization")
    try:
        job = job_service.create_job(
            task_type="cad_bom",
            payload={
                "file_id": file_container.id,
                "item_id": item_id,
                "source_path": file_container.system_path,
                "cad_connector_id": file_container.cad_connector_id,
                "cad_format": file_container.cad_format,
                "document_type": file_container.document_type,
                "tenant_id": user.tenant_id,
                "org_id": user.org_id,
                "user_id": user.id,
                "roles": list(user.roles or []),
                "authorization": auth_header,
            },
            user_id=user.id,
            priority=27,
            dedupe=True,
        )
    except QuotaExceededError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc

    _log_cad_change(
        db,
        file_container,
        "cad_bom_reimport_requested",
        {"item_id": item_id, "job_id": job.id},
        user,
    )
    db.add(file_container)
    db.commit()

    return CadBomReimportResponse(
        file_id=file_container.id,
        item_id=item_id,
        job_id=job.id,
        job_status=job.status,
    )


@router.get("/files/{file_id}/properties", response_model=CadPropertiesResponse)
def get_cad_properties(
    file_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadPropertiesResponse:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    updated_at = file_container.cad_properties_updated_at
    return CadPropertiesResponse(
        file_id=file_container.id,
        properties=file_container.cad_properties or {},
        updated_at=updated_at.isoformat() if updated_at else None,
        source=file_container.cad_properties_source,
        cad_document_schema_version=file_container.cad_document_schema_version,
    )


@router.patch("/files/{file_id}/properties", response_model=CadPropertiesResponse)
def update_cad_properties(
    file_id: str,
    payload: CadPropertiesUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadPropertiesResponse:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    source = (payload.source or "manual").strip() or "manual"
    file_container.cad_properties = dict(payload.properties or {})
    file_container.cad_properties_source = source
    file_container.cad_properties_updated_at = datetime.utcnow()
    _log_cad_change(
        db,
        file_container,
        "cad_properties_update",
        {"properties": file_container.cad_properties, "source": source},
        user,
    )
    db.add(file_container)
    db.commit()

    updated_at = file_container.cad_properties_updated_at
    return CadPropertiesResponse(
        file_id=file_container.id,
        properties=file_container.cad_properties or {},
        updated_at=updated_at.isoformat() if updated_at else None,
        source=file_container.cad_properties_source,
        cad_document_schema_version=file_container.cad_document_schema_version,
    )


@router.get("/files/{file_id}/view-state", response_model=CadViewStateResponse)
def get_cad_view_state(
    file_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadViewStateResponse:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    state = file_container.cad_view_state or {}
    updated_at = file_container.cad_view_state_updated_at
    notes = state.get("notes") or []
    return CadViewStateResponse(
        file_id=file_container.id,
        hidden_entity_ids=state.get("hidden_entity_ids") or [],
        notes=_normalize_view_notes(notes),
        updated_at=updated_at.isoformat() if updated_at else None,
        source=file_container.cad_view_state_source,
        cad_document_schema_version=file_container.cad_document_schema_version,
    )


@router.patch("/files/{file_id}/view-state", response_model=CadViewStateResponse)
def update_cad_view_state(
    file_id: str,
    payload: CadViewStateUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadViewStateResponse:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    existing = file_container.cad_view_state or {}
    hidden_ids = (
        payload.hidden_entity_ids
        if payload.hidden_entity_ids is not None
        else existing.get("hidden_entity_ids")
    ) or []
    notes = (
        payload.notes
        if payload.notes is not None
        else existing.get("notes")
    ) or []
    notes_payload = _normalize_view_notes(notes)

    entity_ids: List[int] = []
    entity_ids.extend([int(eid) for eid in hidden_ids if isinstance(eid, int)])
    for note in notes_payload:
        entity_id = note.get("entity_id")
        if isinstance(entity_id, int):
            entity_ids.append(entity_id)
    _validate_entity_ids(file_container, entity_ids)

    source = (payload.source or file_container.cad_view_state_source or "manual").strip() or "manual"
    file_container.cad_view_state = {
        "hidden_entity_ids": hidden_ids,
        "notes": notes_payload,
    }
    file_container.cad_view_state_source = source
    file_container.cad_view_state_updated_at = datetime.utcnow()
    _log_cad_change(
        db,
        file_container,
        "cad_view_state_update",
        {
            "hidden_entity_ids": hidden_ids,
            "notes": notes_payload,
            "source": source,
            "refresh_preview": payload.refresh_preview,
        },
        user,
    )
    db.add(file_container)

    if payload.refresh_preview and file_container.is_cad_file():
        job_service = JobService(db)
        job_payload = {
            "file_id": file_container.id,
            "tenant_id": user.tenant_id,
            "org_id": user.org_id,
            "user_id": user.id,
        }
        try:
            job_service.create_job(
                task_type="cad_preview",
                payload=job_payload,
                user_id=user.id,
                priority=15,
                dedupe=True,
            )
        except QuotaExceededError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc

    db.commit()

    updated_at = file_container.cad_view_state_updated_at
    return CadViewStateResponse(
        file_id=file_container.id,
        hidden_entity_ids=hidden_ids,
        notes=notes_payload,
        updated_at=updated_at.isoformat() if updated_at else None,
        source=file_container.cad_view_state_source,
        cad_document_schema_version=file_container.cad_document_schema_version,
    )


@router.get("/files/{file_id}/review", response_model=CadReviewResponse)
def get_cad_review(
    file_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadReviewResponse:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")
    return _build_cad_review_response(file_container)


@router.post("/files/{file_id}/review", response_model=CadReviewResponse)
def update_cad_review(
    file_id: str,
    payload: CadReviewRequest,
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> CadReviewResponse:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    state = (payload.state or "").strip().lower()
    allowed_states = {"pending", "approved", "rejected"}
    if state not in allowed_states:
        raise HTTPException(status_code=400, detail=f"Invalid review state: {state}")

    file_container.cad_review_state = state
    file_container.cad_review_note = payload.note
    file_container.cad_review_by_id = user.id
    file_container.cad_reviewed_at = datetime.utcnow()
    _log_cad_change(
        db,
        file_container,
        "cad_review_update",
        {"state": state, "note": payload.note},
        user,
    )
    db.add(file_container)
    db.commit()

    reviewed_at = file_container.cad_reviewed_at
    return CadReviewResponse(
        file_id=file_container.id,
        state=file_container.cad_review_state,
        note=file_container.cad_review_note,
        reviewed_at=reviewed_at.isoformat() if reviewed_at else None,
        reviewed_by_id=file_container.cad_review_by_id,
    )


@router.get("/files/{file_id}/diff", response_model=CadDiffResponse)
def diff_cad_properties(
    file_id: str,
    other_file_id: str = Query(..., description="Compare against this file id"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadDiffResponse:
    file_container = db.get(FileContainer, file_id)
    other_container = db.get(FileContainer, other_file_id)
    if not file_container or not other_container:
        raise HTTPException(status_code=404, detail="File not found")

    before = file_container.cad_properties or {}
    after = other_container.cad_properties or {}
    return CadDiffResponse(
        file_id=file_container.id,
        other_file_id=other_container.id,
        properties=_diff_dicts(before, after),
        cad_document_schema_version={
            "from": file_container.cad_document_schema_version,
            "to": other_container.cad_document_schema_version,
        },
    )


@router.get("/files/{file_id}/history", response_model=CadChangeLogResponse)
def get_cad_history(
    file_id: str,
    limit: int = Query(50, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadChangeLogResponse:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")
    return CadChangeLogResponse(
        file_id=file_container.id,
        entries=_load_cad_history_entries(
            file_container=file_container,
            db=db,
            limit=limit,
        ),
    )


@router.get("/files/{file_id}/mesh-stats", response_model=CadMeshStatsResponse)
def get_cad_mesh_stats(
    file_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadMeshStatsResponse:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")
    if not file_container.cad_metadata_path:
        return CadMeshStatsResponse(
            file_id=file_container.id,
            stats={
                "available": False,
                "reason": "CAD metadata not available",
            },
        )

    payload = _load_cad_metadata_payload(file_container)
    if not payload or payload.get("kind") == "cad_attributes":
        return CadMeshStatsResponse(
            file_id=file_container.id,
            stats={
                "available": False,
                "reason": "CAD mesh metadata not available",
            },
        )
    if not any(
        key in payload
        for key in ("entities", "triangle_count", "triangles", "face_count", "faces", "bounds", "bbox")
    ):
        return CadMeshStatsResponse(
            file_id=file_container.id,
            stats={
                "available": False,
                "reason": "CAD mesh metadata not available",
                "raw_keys": sorted(payload.keys()),
            },
        )
    stats = _extract_mesh_stats(payload or {})
    stats.setdefault("available", True)
    return CadMeshStatsResponse(file_id=file_container.id, stats=stats)


@router.post("/import", response_model=CadImportResponse)
async def import_cad(
    response: Response,
    request: Request,
    file: UploadFile = File(...),
    item_id: Optional[str] = Form(default=None, description="Attach to an existing item id"),
    file_role: str = Form(default=FileRole.NATIVE_CAD.value, description="Attachment role"),
    author: Optional[str] = Form(default=None, description="File author"),
    source_system: Optional[str] = Form(default=None, description="Source system name"),
    source_version: Optional[str] = Form(default=None, description="Source system version"),
    document_version: Optional[str] = Form(default=None, description="Document version label"),
    cad_format: Optional[str] = Form(
        default=None,
        description="Override CAD format/vendor label (e.g., GSTARCAD, ZWCAD, HAOCHEN, ZHONGWANG)",
    ),
    cad_connector_id: Optional[str] = Form(
        default=None,
        description="Explicit connector id override (e.g., gstarcad, zwcad)",
    ),
    create_preview_job: bool = Form(default=True),
    create_geometry_job: Optional[bool] = Form(default=None),
    geometry_format: str = Form(default="gltf", description="obj|gltf|glb|stl"),
    create_extract_job: Optional[bool] = Form(
        default=None,
        description="Extract CAD attributes for sync (default: true)",
    ),
    create_bom_job: bool = Form(
        default=False,
        description="Extract BOM structure from CAD (connector)",
    ),
    auto_create_part: bool = Form(
        default=False,
        description="Auto-create Part when item_id is not provided",
    ),
    create_dedup_job: bool = Form(default=False),
    dedup_mode: str = Form(default="balanced", description="fast|balanced|precise"),
    dedup_index: bool = Form(
        default=False,
        description="Index drawing into Dedup Vision after search (recommended for first-time ingest)",
    ),
    create_ml_job: bool = Form(default=False, description="Call cad-ml-platform vision analyze"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    identity_db: Session = Depends(get_identity_db),
) -> CadImportResponse:
    """
    Import a CAD file: upload to storage, optionally attach to an item, then enqueue pipeline jobs.

    Jobs are created in `meta_conversion_jobs` and executed by `yuantus worker`.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    _validate_upload(file.filename, len(content))

    checksum = _calculate_checksum(content)
    existing = db.query(FileContainer).filter(FileContainer.checksum == checksum).first()
    is_duplicate = existing is not None

    def _append_quota_warning(message: str) -> None:
        if not message:
            return
        current = response.headers.get("X-Quota-Warning")
        response.headers["X-Quota-Warning"] = f"{current}; {message}" if current else message

    file_container: FileContainer
    if existing:
        file_service = FileService()
        if existing.system_path and not file_service.file_exists(existing.system_path):
            # Repair missing storage object for deduped uploads.
            file_service.upload_file(io.BytesIO(content), existing.system_path)
            existing.file_size = len(content)
            existing.mime_type = _get_mime_type(file.filename)
            db.add(existing)
            db.commit()
        file_container = existing
    else:
        quota_service = QuotaService(identity_db, meta_db=db)
        decisions = quota_service.evaluate(
            user.tenant_id, deltas={"files": 1, "storage_bytes": len(content)}
        )
        if decisions:
            if quota_service.mode == "soft":
                _append_quota_warning(QuotaService.build_warning(decisions))
            else:
                detail = {
                    "code": "QUOTA_EXCEEDED",
                    **QuotaService.build_error_payload(user.tenant_id, decisions),
                }
                raise HTTPException(status_code=429, detail=detail)

        file_id = str(uuid.uuid4())
        ext = Path(file.filename).suffix.lower()
        resolved = _resolve_cad_metadata(
            ext,
            cad_format,
            cad_connector_id,
            content=content,
            filename=file.filename,
            source_system=source_system,
        )
        final_format = resolved["cad_format"]
        document_type = resolved["document_type"]
        resolved_connector_id = resolved.get("connector_id")
        stored_filename = f"{file_id}{ext}"
        storage_key = f"{document_type}/{file_id[:2]}/{stored_filename}"

        file_service = FileService()
        file_service.upload_file(io.BytesIO(content), storage_key)

        file_container = FileContainer(
            id=file_id,
            filename=file.filename,
            file_type=ext.lstrip("."),
            mime_type=_get_mime_type(file.filename),
            file_size=len(content),
            checksum=checksum,
            system_path=storage_key,
            document_type=document_type,
            is_native_cad=final_format is not None,
            cad_format=final_format,
            cad_connector_id=resolved_connector_id,
            created_by_id=user.id,
            author=author,
            source_system=source_system,
            source_version=source_version,
            document_version=document_version,
        )
        db.add(file_container)
        db.commit()

    if auto_create_part and not item_id:
        part_type = db.get(ItemType, "Part")
        if not part_type:
            raise HTTPException(status_code=404, detail="Part ItemType not found")

        cad_service = CadService(db)
        file_service = FileService()
        try:
            extracted_attrs, _source = cad_service.extract_attributes_for_file(
                file_container,
                file_service=file_service,
                return_source=True,
            )
        except JobFatalError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        item_number, part_props = _build_auto_part_properties(
            part_type, extracted_attrs, file_container.filename
        )
        identity = str(user.id)
        roles = list(user.roles or [])
        if user.is_superuser and "superuser" not in roles:
            roles.append("superuser")
        engine = AMLEngine(db, identity_id=identity, roles=roles)
        existing_part = (
            db.query(Item)
            .filter(Item.item_type_id == "Part")
            .filter(_json_text(Item.properties["item_number"]) == item_number)
            .first()
        )
        if existing_part:
            item_id = existing_part.id
            updates = _build_missing_updates(existing_part.properties, part_props)
            if updates:
                aml_update = GenericItem(
                    id=item_id,
                    type="Part",
                    action=AMLAction.update,
                    properties=updates,
                )
                try:
                    engine.apply(aml_update)
                    db.commit()
                except PLMException as exc:
                    db.rollback()
                    raise HTTPException(status_code=exc.status_code, detail=exc.to_dict())
                except Exception as exc:
                    db.rollback()
                    raise HTTPException(status_code=400, detail=str(exc))
        else:
            aml = GenericItem(type="Part", action=AMLAction.add, properties=part_props)
            try:
                result = engine.apply(aml)
                db.commit()
            except PLMException as exc:
                db.rollback()
                raise HTTPException(status_code=exc.status_code, detail=exc.to_dict())
            except Exception as exc:
                db.rollback()
                raise HTTPException(status_code=400, detail=str(exc))
            item_id = result.get("id")
            if not item_id:
                raise HTTPException(status_code=500, detail="Auto Part creation failed")

    if create_bom_job and not item_id:
        raise HTTPException(
            status_code=400,
            detail="create_bom_job requires item_id or auto_create_part",
        )

    attachment_id: Optional[str] = None
    if item_id:
        item = db.get(Item, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        if item.current_version_id:
            from yuantus.meta_engine.version.models import ItemVersion

            ver = db.get(ItemVersion, item.current_version_id)
            if ver and ver.checked_out_by_id and ver.checked_out_by_id != user.id:
                raise HTTPException(
                    status_code=409,
                    detail=f"Version {ver.id} is checked out by another user",
                )

        existing_link = (
            db.query(ItemFile)
            .filter(ItemFile.item_id == item_id, ItemFile.file_id == file_container.id)
            .first()
        )
        if existing_link:
            existing_link.file_role = file_role
            db.add(existing_link)
            db.commit()
            attachment_id = existing_link.id
        else:
            link = ItemFile(
                item_id=item_id,
                file_id=file_container.id,
                file_role=file_role,
            )
            db.add(link)
            db.commit()
            attachment_id = link.id

    geometry_enabled = create_geometry_job
    if geometry_enabled is None:
        geometry_enabled = False

    planned_jobs = 0
    if create_preview_job and file_container.is_cad_file():
        planned_jobs += 1
    if geometry_enabled and file_container.is_cad_file():
        planned_jobs += 1
    extract_enabled = create_extract_job
    if extract_enabled is None:
        extract_enabled = bool(file_container.is_cad_file())
    if extract_enabled and file_container.is_cad_file():
        planned_jobs += 1
    if create_bom_job and file_container.is_cad_file():
        planned_jobs += 1
    if create_dedup_job and file_container.file_type in {"dwg", "dxf", "pdf", "png", "jpg", "jpeg"}:
        planned_jobs += 1
    if create_ml_job and file_container.file_type in {"pdf", "png", "jpg", "jpeg", "dwg", "dxf"}:
        planned_jobs += 1

    if planned_jobs:
        quota_service = QuotaService(identity_db, meta_db=db)
        decisions = quota_service.evaluate(
            user.tenant_id, deltas={"active_jobs": planned_jobs}
        )
        if decisions:
            if quota_service.mode == "soft":
                _append_quota_warning(QuotaService.build_warning(decisions))
            else:
                detail = {
                    "code": "QUOTA_EXCEEDED",
                    **QuotaService.build_error_payload(user.tenant_id, decisions),
                }
                raise HTTPException(status_code=429, detail=detail)

    jobs: List[CadImportJob] = []
    job_service = JobService(db)
    auth_header = request.headers.get("authorization")
    user_roles = list(user.roles or [])

    def _enqueue(task_type: str, payload: Dict[str, Any], priority: int) -> None:
        if item_id:
            payload = {**payload, "item_id": item_id}
        payload = {
            **payload,
            "file_id": file_container.id,
            "source_path": file_container.system_path,
            "cad_connector_id": file_container.cad_connector_id,
            "cad_format": file_container.cad_format,
            "document_type": file_container.document_type,
            "tenant_id": user.tenant_id,
            "org_id": user.org_id,
            "user_id": user.id,
            "roles": user_roles,
            "authorization": auth_header,
        }
        try:
            job = job_service.create_job(
                task_type=task_type,
                payload=payload,
                user_id=user.id,
                priority=priority,
                dedupe=True,
            )
        except QuotaExceededError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc
        jobs.append(CadImportJob(id=job.id, task_type=job.task_type, status=job.status))

    # Pipeline: preview -> geometry -> dedup -> ml
    if create_preview_job and file_container.is_cad_file():
        _enqueue("cad_preview", {"file_id": file_container.id}, priority=10)

    if geometry_enabled and file_container.is_cad_file():
        _enqueue(
            "cad_geometry",
            {"file_id": file_container.id, "target_format": geometry_format},
            priority=20,
        )

    if extract_enabled and file_container.is_cad_file():
        _enqueue("cad_extract", {"file_id": file_container.id}, priority=25)

    if create_bom_job and file_container.is_cad_file():
        _enqueue("cad_bom", {"file_id": file_container.id}, priority=27)

    # Dedup is most relevant for 2D drawings; keep it optional.
    if create_dedup_job and file_container.file_type in {"dwg", "dxf", "pdf", "png", "jpg", "jpeg"}:
        _enqueue(
            "cad_dedup_vision",
            {
                "file_id": file_container.id,
                "mode": dedup_mode,
                "user_name": user.username,
                "index": bool(dedup_index),
            },
            priority=30,
        )

    if create_ml_job and file_container.file_type in {"pdf", "png", "jpg", "jpeg", "dwg", "dxf"}:
        _enqueue(
            "cad_ml_vision",
            {"file_id": file_container.id},
            priority=40,
        )

    preview_url = f"/api/v1/file/{file_container.id}/preview" if file_container.preview_path else None
    geometry_url = f"/api/v1/file/{file_container.id}/geometry" if file_container.geometry_path else None
    cad_manifest_url = (
        f"/api/v1/file/{file_container.id}/cad_manifest"
        if file_container.cad_manifest_path
        else None
    )
    cad_document_url = (
        f"/api/v1/file/{file_container.id}/cad_document"
        if file_container.cad_document_path
        else None
    )
    cad_metadata_url = (
        f"/api/v1/file/{file_container.id}/cad_metadata"
        if file_container.cad_metadata_path
        else None
    )
    cad_bom_url = (
        f"/api/v1/file/{file_container.id}/cad_bom"
        if file_container.cad_bom_path
        else None
    )
    cad_dedup_url = (
        f"/api/v1/file/{file_container.id}/cad_dedup"
        if file_container.cad_dedup_path
        else None
    )
    cad_viewer_url = _build_cad_viewer_url(
        request,
        file_container.id,
        file_container.cad_manifest_path,
    )
    return CadImportResponse(
        file_id=file_container.id,
        filename=file_container.filename,
        checksum=file_container.checksum,
        is_duplicate=is_duplicate,
        item_id=item_id,
        attachment_id=attachment_id,
        jobs=jobs,
        download_url=f"/api/v1/file/{file_container.id}/download",
        preview_url=preview_url,
        geometry_url=geometry_url,
        cad_manifest_url=cad_manifest_url,
        cad_document_url=cad_document_url,
        cad_metadata_url=cad_metadata_url,
        cad_bom_url=cad_bom_url,
        cad_dedup_url=cad_dedup_url,
        cad_viewer_url=cad_viewer_url,
        cad_document_schema_version=file_container.cad_document_schema_version,
        cad_format=file_container.cad_format,
        cad_connector_id=file_container.cad_connector_id,
        document_type=file_container.document_type,
        is_native_cad=file_container.is_native_cad,
        author=file_container.author,
        source_system=file_container.source_system,
        source_version=file_container.source_version,
        document_version=file_container.document_version,
    )


@router.post("/{item_id}/checkout")
def checkout_document(
    item_id: str, mgr: CheckinManager = Depends(get_checkin_manager)
) -> Any:
    """
    Lock a document for editing.
    """
    try:
        item = mgr.checkout(item_id)
        # Commit handled by service or need manual commit?
        # Service flushes, but typically Router/Dependencies commit.
        # But CheckinManager commits/flushes?
        # CheckinManager.checkout does 'add' and 'flush'.
        # We need final commit.
        mgr.session.commit()
        return {
            "status": "success",
            "message": "Item locked.",
            "locked_by_id": item.locked_by_id,
        }
    except ValueError as e:
        mgr.session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        mgr.session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{item_id}/undo-checkout")
def undo_checkout(
    item_id: str, mgr: CheckinManager = Depends(get_checkin_manager)
) -> Any:
    try:
        mgr.undo_checkout(item_id)
        mgr.session.commit()
        return {"status": "success", "message": "Item unlocked."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{item_id}/checkin")
def checkin_document(
    item_id: str,
    response: Response,
    file: UploadFile = File(...),
    mgr: CheckinManager = Depends(get_checkin_manager),
    user: CurrentUser = Depends(get_current_user),
    identity_db: Session = Depends(get_identity_db),
) -> Any:
    """
    Upload new file version and unlock.
    """
    try:
        content = file.file.read()
        filename = file.filename

        quota_service = QuotaService(identity_db, meta_db=mgr.session)
        decisions = quota_service.evaluate(
            user.tenant_id, deltas={"files": 1, "storage_bytes": len(content)}
        )
        if decisions:
            if quota_service.mode == "soft":
                response.headers["X-Quota-Warning"] = QuotaService.build_warning(decisions)
            else:
                detail = {
                    "code": "QUOTA_EXCEEDED",
                    **QuotaService.build_error_payload(user.tenant_id, decisions),
                }
                raise HTTPException(status_code=429, detail=detail)

        new_item = mgr.checkin(item_id, content, filename)
        mgr.session.commit()

        return {
            "status": "success",
            "new_item_id": new_item.id,
            "generation": new_item.generation,
        }
    except ValueError as e:
        mgr.session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        mgr.session.rollback()
        raise
    except Exception as e:
        mgr.session.rollback()
        # Log error
        raise HTTPException(status_code=500, detail=str(e))
