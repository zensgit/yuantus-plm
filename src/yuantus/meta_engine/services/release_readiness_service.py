from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from yuantus.config import get_settings
from yuantus.meta_engine.esign.service import ElectronicSignatureService
from yuantus.meta_engine.manufacturing.mbom_service import MBOMService
from yuantus.meta_engine.manufacturing.models import ManufacturingBOM, Routing
from yuantus.meta_engine.manufacturing.routing_service import RoutingService
from yuantus.meta_engine.models.baseline import Baseline
from yuantus.meta_engine.services.baseline_service import BaselineService


class ReleaseReadinessService:
    def __init__(self, session: Session):
        self.session = session

    def list_mboms(self, *, item_id: str, limit: int) -> List[ManufacturingBOM]:
        return (
            self.session.query(ManufacturingBOM)
            .filter(ManufacturingBOM.source_item_id == item_id)
            .order_by(ManufacturingBOM.created_at.desc())
            .limit(max(0, int(limit)))
            .all()
        )

    def list_routings(
        self,
        *,
        item_id: str,
        mbom_ids: List[str],
        limit: int,
    ) -> List[Routing]:
        q = self.session.query(Routing)
        clauses = []
        if item_id:
            clauses.append(Routing.item_id == item_id)
        if mbom_ids:
            clauses.append(Routing.mbom_id.in_(list(mbom_ids)))
        if clauses:
            q = q.filter(or_(*clauses))
        return (
            q.order_by(Routing.created_at.desc())
            .limit(max(0, int(limit)))
            .all()
        )

    def list_baselines(self, *, item_id: str, limit: int) -> List[Baseline]:
        return (
            self.session.query(Baseline)
            .filter(Baseline.root_item_id == item_id)
            .order_by(Baseline.created_at.desc())
            .limit(max(0, int(limit)))
            .all()
        )

    def get_esign_manifest_status(self, *, item_id: str) -> Optional[Dict[str, Any]]:
        settings = get_settings()
        secret = (getattr(settings, "ESIGN_SECRET_KEY", None) or settings.JWT_SECRET_KEY).strip()
        verify_keys = [secret]
        extra = (getattr(settings, "ESIGN_VERIFY_SECRET_KEYS", "") or "").strip()
        if extra:
            for key in extra.split(","):
                k = key.strip()
                if k and k not in verify_keys:
                    verify_keys.append(k)
        svc = ElectronicSignatureService(
            self.session,
            secret_key=secret,
            verify_secret_keys=verify_keys,
            auth_service=None,
        )
        return svc.get_manifest_status(item_id=item_id)

    def get_item_release_readiness(
        self,
        *,
        item_id: str,
        ruleset_id: str,
        mbom_limit: int,
        routing_limit: int,
        baseline_limit: int,
    ) -> Dict[str, Any]:
        generated_at = datetime.utcnow()

        mboms = self.list_mboms(item_id=item_id, limit=mbom_limit)
        mbom_ids = [m.id for m in mboms]
        routings = self.list_routings(item_id=item_id, mbom_ids=mbom_ids, limit=routing_limit)
        baselines = self.list_baselines(item_id=item_id, limit=baseline_limit)

        mbom_service = MBOMService(self.session)
        routing_service = RoutingService(self.session)
        baseline_service = BaselineService(self.session)

        resources: List[Dict[str, Any]] = []

        for mbom in mboms:
            diag = mbom_service.get_release_diagnostics(mbom.id, ruleset_id=ruleset_id)
            resources.append(
                {
                    "kind": "mbom_release",
                    "resource_type": "mbom",
                    "resource_id": mbom.id,
                    "name": getattr(mbom, "name", None),
                    "state": getattr(mbom, "state", None),
                    "ruleset_id": str(diag.get("ruleset_id") or ruleset_id),
                    "errors": diag.get("errors") or [],
                    "warnings": diag.get("warnings") or [],
                }
            )

        for routing in routings:
            diag = routing_service.get_release_diagnostics(routing.id, ruleset_id=ruleset_id)
            resources.append(
                {
                    "kind": "routing_release",
                    "resource_type": "routing",
                    "resource_id": routing.id,
                    "name": getattr(routing, "name", None),
                    "state": getattr(routing, "state", None),
                    "ruleset_id": str(diag.get("ruleset_id") or ruleset_id),
                    "errors": diag.get("errors") or [],
                    "warnings": diag.get("warnings") or [],
                }
            )

        for baseline in baselines:
            diag = baseline_service.get_release_diagnostics(baseline.id, ruleset_id=ruleset_id)
            resources.append(
                {
                    "kind": "baseline_release",
                    "resource_type": "baseline",
                    "resource_id": baseline.id,
                    "name": getattr(baseline, "name", None),
                    "state": getattr(baseline, "state", None),
                    "ruleset_id": str(diag.get("ruleset_id") or ruleset_id),
                    "errors": diag.get("errors") or [],
                    "warnings": diag.get("warnings") or [],
                }
            )

        error_count = sum(len(r.get("errors") or []) for r in resources)
        warning_count = sum(len(r.get("warnings") or []) for r in resources)
        resources_ok = sum(1 for r in resources if len(r.get("errors") or []) == 0)

        by_kind: Dict[str, Dict[str, int]] = {}
        for r in resources:
            kind = str(r.get("kind") or "")
            entry = by_kind.setdefault(
                kind,
                {"resources": 0, "ok_resources": 0, "error_count": 0, "warning_count": 0},
            )
            entry["resources"] += 1
            entry["error_count"] += len(r.get("errors") or [])
            entry["warning_count"] += len(r.get("warnings") or [])
            if len(r.get("errors") or []) == 0:
                entry["ok_resources"] += 1

        return {
            "item_id": item_id,
            "generated_at": generated_at,
            "ruleset_id": ruleset_id,
            "summary": {
                "ok": error_count == 0,
                "resources": len(resources),
                "ok_resources": int(resources_ok),
                "error_count": int(error_count),
                "warning_count": int(warning_count),
                "by_kind": by_kind,
            },
            "resources": resources,
            "esign_manifest": self.get_esign_manifest_status(item_id=item_id),
        }

