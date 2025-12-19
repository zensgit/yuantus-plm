from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.permission.models import Access, Permission

permission_router = APIRouter(prefix="/meta", tags=["Permissions"])


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    roles = set(user.roles or [])
    if "admin" not in roles and "superuser" not in roles:
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


class PermissionCreateRequest(BaseModel):
    id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)


class PermissionUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)


class AccessUpsertRequest(BaseModel):
    identity_id: str = Field(..., min_length=1, max_length=200, description="Role name or user id")
    can_create: bool = Field(default=False)
    can_get: bool = Field(default=False)
    can_update: bool = Field(default=False)
    can_delete: bool = Field(default=False)
    can_discover: bool = Field(default=False)


class AccessUpdateRequest(BaseModel):
    can_create: Optional[bool] = None
    can_get: Optional[bool] = None
    can_update: Optional[bool] = None
    can_delete: Optional[bool] = None
    can_discover: Optional[bool] = None


class AccessResponse(BaseModel):
    id: str
    permission_id: str
    identity_id: str
    can_create: bool
    can_get: bool
    can_update: bool
    can_delete: bool
    can_discover: bool


class PermissionResponse(BaseModel):
    id: str
    name: str
    accesses: List[AccessResponse] = Field(default_factory=list)


class AssignPermissionRequest(BaseModel):
    permission_id: str = Field(..., min_length=1, max_length=100)


def _access_id(permission_id: str, identity_id: str) -> str:
    return f"{permission_id}:{identity_id}"


@permission_router.get("/permissions", response_model=Dict[str, Any])
def list_permissions(
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    perms = db.query(Permission).order_by(Permission.id.asc()).all()
    return {
        "total": len(perms),
        "items": [{"id": p.id, "name": p.name, "access_count": len(p.accesses or [])} for p in perms],
    }


@permission_router.post("/permissions", response_model=PermissionResponse)
def create_permission(
    req: PermissionCreateRequest,
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PermissionResponse:
    existing = db.get(Permission, req.id)
    if existing:
        raise HTTPException(status_code=409, detail="Permission already exists")
    perm = Permission(id=req.id, name=req.name)
    db.add(perm)
    db.commit()
    db.refresh(perm)
    return PermissionResponse(id=perm.id, name=perm.name, accesses=[])


@permission_router.get("/permissions/{permission_id}", response_model=PermissionResponse)
def get_permission(
    permission_id: str,
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PermissionResponse:
    perm = db.get(Permission, permission_id)
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    accesses = (
        db.query(Access)
        .filter(Access.permission_id == perm.id)
        .order_by(Access.identity_id.asc())
        .all()
    )
    return PermissionResponse(
        id=perm.id,
        name=perm.name,
        accesses=[
            AccessResponse(
                id=a.id,
                permission_id=a.permission_id,
                identity_id=a.identity_id,
                can_create=bool(a.can_create),
                can_get=bool(a.can_get),
                can_update=bool(a.can_update),
                can_delete=bool(a.can_delete),
                can_discover=bool(a.can_discover),
            )
            for a in accesses
        ],
    )


@permission_router.patch("/permissions/{permission_id}", response_model=PermissionResponse)
def update_permission(
    permission_id: str,
    req: PermissionUpdateRequest,
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PermissionResponse:
    perm = db.get(Permission, permission_id)
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    if req.name is not None:
        perm.name = req.name
    db.add(perm)
    db.commit()
    db.refresh(perm)
    return get_permission(permission_id, db=db)  # type: ignore[arg-type]


@permission_router.delete("/permissions/{permission_id}", response_model=Dict[str, Any])
def delete_permission(
    permission_id: str,
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    perm = db.get(Permission, permission_id)
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    db.delete(perm)
    db.commit()
    return {"ok": True, "id": permission_id}


@permission_router.post("/permissions/{permission_id}/accesses", response_model=AccessResponse)
def upsert_access(
    permission_id: str,
    req: AccessUpsertRequest,
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AccessResponse:
    perm = db.get(Permission, permission_id)
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")

    access_id = _access_id(permission_id, req.identity_id)
    access = db.get(Access, access_id)
    if not access:
        access = Access(
            id=access_id,
            permission_id=permission_id,
            identity_id=req.identity_id,
            can_create=bool(req.can_create),
            can_get=bool(req.can_get),
            can_update=bool(req.can_update),
            can_delete=bool(req.can_delete),
            can_discover=bool(req.can_discover),
        )
        db.add(access)
    else:
        access.identity_id = req.identity_id
        access.can_create = bool(req.can_create)
        access.can_get = bool(req.can_get)
        access.can_update = bool(req.can_update)
        access.can_delete = bool(req.can_delete)
        access.can_discover = bool(req.can_discover)
        db.add(access)
    db.commit()
    db.refresh(access)
    return AccessResponse(
        id=access.id,
        permission_id=access.permission_id,
        identity_id=access.identity_id,
        can_create=bool(access.can_create),
        can_get=bool(access.can_get),
        can_update=bool(access.can_update),
        can_delete=bool(access.can_delete),
        can_discover=bool(access.can_discover),
    )


@permission_router.patch("/permissions/{permission_id}/accesses/{access_id}", response_model=AccessResponse)
def update_access(
    permission_id: str,
    access_id: str,
    req: AccessUpdateRequest,
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AccessResponse:
    access = db.get(Access, access_id)
    if not access or access.permission_id != permission_id:
        raise HTTPException(status_code=404, detail="Access not found")
    if req.can_create is not None:
        access.can_create = bool(req.can_create)
    if req.can_get is not None:
        access.can_get = bool(req.can_get)
    if req.can_update is not None:
        access.can_update = bool(req.can_update)
    if req.can_delete is not None:
        access.can_delete = bool(req.can_delete)
    if req.can_discover is not None:
        access.can_discover = bool(req.can_discover)
    db.add(access)
    db.commit()
    db.refresh(access)
    return AccessResponse(
        id=access.id,
        permission_id=access.permission_id,
        identity_id=access.identity_id,
        can_create=bool(access.can_create),
        can_get=bool(access.can_get),
        can_update=bool(access.can_update),
        can_delete=bool(access.can_delete),
        can_discover=bool(access.can_discover),
    )


@permission_router.delete("/permissions/{permission_id}/accesses/{access_id}", response_model=Dict[str, Any])
def delete_access(
    permission_id: str,
    access_id: str,
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    access = db.get(Access, access_id)
    if not access or access.permission_id != permission_id:
        raise HTTPException(status_code=404, detail="Access not found")
    db.delete(access)
    db.commit()
    return {"ok": True, "id": access_id}


@permission_router.patch("/item-types/{item_type_id}/permission", response_model=Dict[str, Any])
def assign_item_type_permission(
    item_type_id: str,
    req: AssignPermissionRequest,
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    item_type = db.query(ItemType).filter(ItemType.id == item_type_id).first()
    if not item_type:
        raise HTTPException(status_code=404, detail="ItemType not found")
    perm = db.get(Permission, req.permission_id)
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")

    item_type.permission_id = perm.id
    db.add(item_type)
    db.commit()
    return {"ok": True, "item_type_id": item_type_id, "permission_id": perm.id}

