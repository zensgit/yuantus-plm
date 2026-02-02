from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.config import get_settings
from yuantus.database import get_db
from yuantus.security.auth.database import get_identity_db
from yuantus.security.auth.service import AuthService
from yuantus.meta_engine.esign.service import ElectronicSignatureService

esign_router = APIRouter(prefix="/esign", tags=["Electronic Signatures"])


class SigningReasonCreateRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=80)
    name: str = Field(..., min_length=1, max_length=200)
    meaning: str = Field(default="approved", max_length=50)
    description: Optional[str] = Field(default=None, max_length=2000)
    regulatory_reference: Optional[str] = Field(default=None, max_length=200)
    requires_password: bool = True
    requires_comment: bool = False
    item_type_id: Optional[str] = None
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    sequence: int = 0


class SigningReasonResponse(BaseModel):
    id: str
    code: str
    name: str
    meaning: str
    description: Optional[str]
    regulatory_reference: Optional[str]
    requires_password: bool
    requires_comment: bool
    item_type_id: Optional[str]
    from_state: Optional[str]
    to_state: Optional[str]
    sequence: int
    is_active: bool
    created_at: Optional[datetime]


class SignRequest(BaseModel):
    item_id: str = Field(..., min_length=1)
    meaning: str = Field(..., min_length=1, max_length=50)
    password: Optional[str] = Field(default=None, max_length=200)
    reason_id: Optional[str] = None
    reason_text: Optional[str] = Field(default=None, max_length=200)
    comment: Optional[str] = Field(default=None, max_length=2000)
    workflow_instance_id: Optional[str] = None
    workflow_activity_id: Optional[str] = None


class SignatureResponse(BaseModel):
    id: str
    item_id: str
    item_generation: int
    signer_id: int
    signer_username: str
    meaning: str
    reason_text: Optional[str]
    comment: Optional[str]
    signed_at: Optional[datetime]
    status: str


class VerifyResponse(BaseModel):
    signature_id: str
    is_valid: bool
    issues: List[str]
    signature: Dict[str, Any]


class RevokeRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class ManifestCreateRequest(BaseModel):
    item_id: str = Field(..., min_length=1)
    generation: int = Field(..., ge=1)
    required_signatures: List[Dict[str, Any]]


def _ensure_admin(user: CurrentUser) -> None:
    roles = set(user.roles or [])
    if not ("admin" in roles or "superuser" in roles or user.is_superuser):
        raise HTTPException(status_code=403, detail="Admin permission required")


def _service(db: Session, identity_db: Session) -> ElectronicSignatureService:
    settings = get_settings()
    secret = getattr(settings, "ESIGN_SECRET_KEY", None) or settings.JWT_SECRET_KEY
    return ElectronicSignatureService(
        db,
        secret_key=secret,
        auth_service=AuthService(identity_db),
    )


@esign_router.post("/reasons", response_model=SigningReasonResponse)
def create_signing_reason(
    req: SigningReasonCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    identity_db: Session = Depends(get_identity_db),
) -> SigningReasonResponse:
    _ensure_admin(user)
    service = _service(db, identity_db)
    reason = service.create_signing_reason(
        code=req.code,
        name=req.name,
        meaning=req.meaning,
        description=req.description,
        regulatory_reference=req.regulatory_reference,
        requires_password=req.requires_password,
        requires_comment=req.requires_comment,
        item_type_id=req.item_type_id,
        from_state=req.from_state,
        to_state=req.to_state,
        sequence=req.sequence,
    )
    return SigningReasonResponse(
        id=reason.id,
        code=reason.code,
        name=reason.name,
        meaning=reason.meaning,
        description=reason.description,
        regulatory_reference=reason.regulatory_reference,
        requires_password=bool(reason.requires_password),
        requires_comment=bool(reason.requires_comment),
        item_type_id=reason.item_type_id,
        from_state=reason.from_state,
        to_state=reason.to_state,
        sequence=reason.sequence or 0,
        is_active=bool(reason.is_active),
        created_at=reason.created_at,
    )


@esign_router.get("/reasons", response_model=Dict[str, Any])
def list_signing_reasons(
    item_type_id: Optional[str] = Query(None),
    from_state: Optional[str] = Query(None),
    to_state: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    _user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    identity_db: Session = Depends(get_identity_db),
) -> Dict[str, Any]:
    service = _service(db, identity_db)
    reasons = service.list_signing_reasons(
        item_type_id=item_type_id,
        from_state=from_state,
        to_state=to_state,
        include_inactive=include_inactive,
    )
    return {
        "items": [
            SigningReasonResponse(
                id=r.id,
                code=r.code,
                name=r.name,
                meaning=r.meaning,
                description=r.description,
                regulatory_reference=r.regulatory_reference,
                requires_password=bool(r.requires_password),
                requires_comment=bool(r.requires_comment),
                item_type_id=r.item_type_id,
                from_state=r.from_state,
                to_state=r.to_state,
                sequence=r.sequence or 0,
                is_active=bool(r.is_active),
                created_at=r.created_at,
            ).model_dump()
            for r in reasons
        ]
    }


@esign_router.post("/sign", response_model=SignatureResponse)
def sign_item(
    req: SignRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    identity_db: Session = Depends(get_identity_db),
) -> SignatureResponse:
    service = _service(db, identity_db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    client_info = {"user_agent": user_agent} if user_agent else None
    try:
        signature = service.sign(
            item_id=req.item_id,
            user_id=user.id,
            tenant_id=user.tenant_id,
            meaning=req.meaning,
            password=req.password,
            reason_id=req.reason_id,
            reason_text=req.reason_text,
            comment=req.comment,
            client_ip=client_ip,
            client_info=client_info,
            workflow_instance_id=req.workflow_instance_id,
            workflow_activity_id=req.workflow_activity_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SignatureResponse(
        id=signature.id,
        item_id=signature.item_id,
        item_generation=signature.item_generation,
        signer_id=signature.signer_id,
        signer_username=signature.signer_username,
        meaning=signature.meaning,
        reason_text=signature.reason_text,
        comment=signature.comment,
        signed_at=signature.signed_at,
        status=signature.status,
    )


@esign_router.post("/verify/{signature_id}", response_model=VerifyResponse)
def verify_signature(
    signature_id: str,
    _user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    identity_db: Session = Depends(get_identity_db),
) -> VerifyResponse:
    service = _service(db, identity_db)
    try:
        result = service.verify(signature_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return VerifyResponse(**result)


@esign_router.post("/revoke/{signature_id}", response_model=SignatureResponse)
def revoke_signature(
    signature_id: str,
    req: RevokeRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    identity_db: Session = Depends(get_identity_db),
) -> SignatureResponse:
    service = _service(db, identity_db)
    try:
        signature = service.revoke(
            signature_id=signature_id,
            revoked_by_id=user.id,
            reason=req.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SignatureResponse(
        id=signature.id,
        item_id=signature.item_id,
        item_generation=signature.item_generation,
        signer_id=signature.signer_id,
        signer_username=signature.signer_username,
        meaning=signature.meaning,
        reason_text=signature.reason_text,
        comment=signature.comment,
        signed_at=signature.signed_at,
        status=signature.status,
    )


@esign_router.get("/items/{item_id}/signatures", response_model=Dict[str, Any])
def list_signatures(
    item_id: str,
    generation: Optional[int] = Query(None),
    include_revoked: bool = Query(False),
    _user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    identity_db: Session = Depends(get_identity_db),
) -> Dict[str, Any]:
    service = _service(db, identity_db)
    signatures = service.get_signatures(
        item_id=item_id, generation=generation, include_revoked=include_revoked
    )
    return {"items": signatures}


@esign_router.post("/manifests", response_model=Dict[str, Any])
def create_manifest(
    req: ManifestCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    identity_db: Session = Depends(get_identity_db),
) -> Dict[str, Any]:
    _ensure_admin(user)
    service = _service(db, identity_db)
    manifest = service.create_manifest(
        item_id=req.item_id,
        generation=req.generation,
        required_signatures=req.required_signatures,
    )
    return {
        "id": manifest.id,
        "item_id": manifest.item_id,
        "item_generation": manifest.item_generation,
        "required_signatures": manifest.required_signatures or [],
        "is_complete": bool(manifest.is_complete),
        "created_at": manifest.created_at.isoformat() if manifest.created_at else None,
    }


@esign_router.get("/manifests/{item_id}", response_model=Dict[str, Any])
def get_manifest_status(
    item_id: str,
    generation: Optional[int] = Query(None),
    _user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    identity_db: Session = Depends(get_identity_db),
) -> Dict[str, Any]:
    service = _service(db, identity_db)
    status = service.get_manifest_status(item_id=item_id, generation=generation)
    if not status:
        raise HTTPException(status_code=404, detail="Manifest not found")
    return status
