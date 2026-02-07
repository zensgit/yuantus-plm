from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from yuantus.exceptions.handlers import PermissionError
from yuantus.meta_engine.esign.models import (
    ElectronicSignature,
    SignatureManifest,
    SignatureStatus,
)
from yuantus.meta_engine.models.baseline import Baseline, BaselineMember
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.baseline_service import BaselineService
from yuantus.meta_engine.services.bom_service import BOMService


@dataclass(frozen=True)
class CurrentUserView:
    """Small view of CurrentUser used by services (keeps imports minimal)."""

    id: int
    roles: List[str]
    is_superuser: bool = False


class ImpactAnalysisService:
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _is_admin(user: CurrentUserView) -> bool:
        roles = {str(r).lower() for r in (user.roles or [])}
        return bool(user.is_superuser) or ("admin" in roles) or ("superuser" in roles)

    def where_used_summary(
        self,
        *,
        item_id: str,
        recursive: bool,
        max_levels: int,
        limit: int,
    ) -> Dict[str, Any]:
        service = BOMService(self.session)
        parents = service.get_where_used(
            item_id=item_id,
            recursive=recursive,
            max_levels=max_levels,
        )
        hits: List[Dict[str, Any]] = []
        for entry in parents[: max(0, limit)]:
            rel = entry.get("relationship") or {}
            parent = entry.get("parent") or {}
            line = entry.get("line") or {}
            hits.append(
                {
                    "parent_id": parent.get("id"),
                    "parent_number": entry.get("parent_number"),
                    "parent_name": entry.get("parent_name"),
                    "relationship_id": rel.get("id"),
                    "level": entry.get("level") or 1,
                    "line": line,
                }
            )
        return {
            "total": len(parents),
            "hits": hits,
            "recursive": recursive,
            "max_levels": max_levels,
        }

    def _can_access_baseline(self, baseline: Baseline, *, user: CurrentUserView) -> bool:
        if self._is_admin(user):
            return True
        if baseline.created_by_id and int(baseline.created_by_id) == int(user.id):
            return True
        if not baseline.root_item_id:
            return False

        root = self.session.get(Item, baseline.root_item_id)
        if not root:
            return False
        service = BaselineService(self.session)
        try:
            service._ensure_can_read(root, str(user.id), list(user.roles or []))
            return True
        except PermissionError:
            return False

    def baselines_summary(
        self,
        *,
        item_id: str,
        user: CurrentUserView,
        limit: int,
    ) -> Dict[str, Any]:
        # Candidate cap: we keep this bounded to avoid expensive permission checks.
        # The `total` returned is "accessible total within the candidate window".
        candidate_limit = 500
        q = (
            self.session.query(Baseline)
            .join(BaselineMember, BaselineMember.baseline_id == Baseline.id)
            .filter(BaselineMember.item_id == item_id)
            .order_by(Baseline.created_at.desc())
            .limit(candidate_limit)
        )
        candidates = q.all()

        allowed: List[Dict[str, Any]] = []
        for baseline in candidates:
            if not self._can_access_baseline(baseline, user=user):
                continue
            allowed.append(
                {
                    "baseline_id": baseline.id,
                    "name": baseline.name,
                    "baseline_number": baseline.baseline_number,
                    "baseline_type": baseline.baseline_type,
                    "scope": baseline.scope,
                    "state": baseline.state,
                    "root_item_id": baseline.root_item_id,
                    "created_at": baseline.created_at,
                    "released_at": baseline.released_at,
                }
            )
        hits = allowed[: max(0, int(limit))]
        return {"total": len(allowed), "hits": hits}

    def esign_summary(
        self,
        *,
        item_id: str,
        limit: int,
    ) -> Dict[str, Any]:
        total = (
            self.session.query(func.count(ElectronicSignature.id))
            .filter(ElectronicSignature.item_id == item_id)
            .scalar()
            or 0
        )
        valid = (
            self.session.query(func.count(ElectronicSignature.id))
            .filter(
                ElectronicSignature.item_id == item_id,
                ElectronicSignature.status == SignatureStatus.VALID.value,
            )
            .scalar()
            or 0
        )
        revoked = (
            self.session.query(func.count(ElectronicSignature.id))
            .filter(
                ElectronicSignature.item_id == item_id,
                ElectronicSignature.status == SignatureStatus.REVOKED.value,
            )
            .scalar()
            or 0
        )
        expired = (
            self.session.query(func.count(ElectronicSignature.id))
            .filter(
                ElectronicSignature.item_id == item_id,
                ElectronicSignature.status == SignatureStatus.EXPIRED.value,
            )
            .scalar()
            or 0
        )

        latest = (
            self.session.query(ElectronicSignature)
            .filter(ElectronicSignature.item_id == item_id)
            .order_by(ElectronicSignature.signed_at.desc())
            .first()
        )
        latest_signed_at: Optional[datetime] = latest.signed_at if latest else None

        sigs = (
            self.session.query(ElectronicSignature)
            .filter(ElectronicSignature.item_id == item_id)
            .order_by(ElectronicSignature.signed_at.desc())
            .limit(max(0, int(limit)))
            .all()
        )
        latest_signatures = [
            {
                "id": s.id,
                "meaning": s.meaning,
                "status": s.status,
                "signed_at": s.signed_at,
                "signer_username": s.signer_username,
            }
            for s in sigs
        ]

        manifest = (
            self.session.query(SignatureManifest)
            .filter(SignatureManifest.item_id == item_id)
            .order_by(SignatureManifest.created_at.desc())
            .first()
        )
        latest_manifest = None
        if manifest:
            latest_manifest = {
                "id": manifest.id,
                "generation": int(manifest.item_generation),
                "is_complete": bool(manifest.is_complete),
                "completed_at": manifest.completed_at,
            }

        return {
            "total": int(total),
            "valid": int(valid),
            "revoked": int(revoked),
            "expired": int(expired),
            "latest_signed_at": latest_signed_at,
            "latest_signatures": latest_signatures,
            "latest_manifest": latest_manifest,
        }
