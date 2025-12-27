from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from yuantus.config import get_settings
from yuantus.exceptions.handlers import QuotaExceededError
from yuantus.security.auth.models import AuthUser, Organization, TenantQuota


@dataclass(frozen=True)
class QuotaUsage:
    users: int
    orgs: int
    files: Optional[int] = None
    storage_bytes: Optional[int] = None
    active_jobs: Optional[int] = None
    processing_jobs: Optional[int] = None

    def to_dict(self) -> Dict[str, Optional[int]]:
        return {
            "users": self.users,
            "orgs": self.orgs,
            "files": self.files,
            "storage_bytes": self.storage_bytes,
            "active_jobs": self.active_jobs,
            "processing_jobs": self.processing_jobs,
        }


@dataclass(frozen=True)
class QuotaDecision:
    resource: str
    used: int
    limit: int
    requested: int

    def to_dict(self) -> Dict[str, int]:
        return {
            "resource": self.resource,
            "used": self.used,
            "limit": self.limit,
            "requested": self.requested,
            "remaining": self.limit - self.used,
        }


class QuotaService:
    def __init__(self, identity_db: Session, *, meta_db: Optional[Session] = None):
        self.identity_db = identity_db
        self.meta_db = meta_db
        self._mode = self._normalize_mode(get_settings().QUOTA_MODE)

    @property
    def mode(self) -> str:
        return self._mode

    def is_enabled(self) -> bool:
        return self._mode in {"soft", "enforce"}

    def is_enforce(self) -> bool:
        return self._mode == "enforce"

    def get_quota(self, tenant_id: str) -> Optional[TenantQuota]:
        return self.identity_db.get(TenantQuota, tenant_id)

    def upsert_quota(self, tenant_id: str, *, updates: Dict[str, Optional[int]]) -> TenantQuota:
        quota = self.identity_db.get(TenantQuota, tenant_id)
        if not quota:
            quota = TenantQuota(tenant_id=tenant_id)
            self.identity_db.add(quota)
        for key, value in updates.items():
            if hasattr(quota, key):
                setattr(quota, key, value)
        self.identity_db.flush()
        return quota

    def get_usage(self, tenant_id: str) -> QuotaUsage:
        users = (
            self.identity_db.query(func.count(AuthUser.id))
            .filter(AuthUser.tenant_id == tenant_id, AuthUser.is_active.is_(True))
            .scalar()
            or 0
        )
        orgs = (
            self.identity_db.query(func.count(Organization.id))
            .filter(Organization.tenant_id == tenant_id, Organization.is_active.is_(True))
            .scalar()
            or 0
        )

        files: Optional[int] = None
        storage_bytes: Optional[int] = None
        active_jobs: Optional[int] = None
        processing_jobs: Optional[int] = None

        if self.meta_db is not None:
            from yuantus.meta_engine.models.file import FileContainer
            from yuantus.meta_engine.models.job import ConversionJob, JobStatus

            files = (
                self.meta_db.query(func.count(FileContainer.id)).scalar() or 0
            )
            storage_bytes = (
                self.meta_db.query(func.coalesce(func.sum(FileContainer.file_size), 0))
                .scalar()
                or 0
            )
            active_jobs = (
                self.meta_db.query(func.count(ConversionJob.id))
                .filter(
                    ConversionJob.status.in_(
                        [JobStatus.PENDING.value, JobStatus.PROCESSING.value]
                    )
                )
                .scalar()
                or 0
            )
            processing_jobs = (
                self.meta_db.query(func.count(ConversionJob.id))
                .filter(ConversionJob.status == JobStatus.PROCESSING.value)
                .scalar()
                or 0
            )

        return QuotaUsage(
            users=users,
            orgs=orgs,
            files=files,
            storage_bytes=storage_bytes,
            active_jobs=active_jobs,
            processing_jobs=processing_jobs,
        )

    def evaluate(self, tenant_id: str, *, deltas: Dict[str, int]) -> List[QuotaDecision]:
        if not self.is_enabled():
            return []

        quota = self.get_quota(tenant_id)
        if not quota:
            return []

        usage = self.get_usage(tenant_id)
        decisions: List[QuotaDecision] = []

        for resource, requested in deltas.items():
            limit_attr = f"max_{resource}"
            if not hasattr(quota, limit_attr):
                continue
            limit = getattr(quota, limit_attr)
            if limit is None:
                continue

            used = getattr(usage, resource)
            if used is None:
                raise RuntimeError(f"Quota usage for {resource} requires meta_db")

            if used + requested > int(limit):
                decisions.append(
                    QuotaDecision(
                        resource=resource,
                        used=int(used),
                        limit=int(limit),
                        requested=int(requested),
                    )
                )
        return decisions

    def raise_if_exceeded(self, tenant_id: str, *, deltas: Dict[str, int]) -> None:
        if not self.is_enforce():
            return
        decisions = self.evaluate(tenant_id, deltas=deltas)
        if not decisions:
            return
        raise QuotaExceededError(self.build_error_payload(tenant_id, decisions))

    @staticmethod
    def build_error_payload(tenant_id: str, decisions: List[QuotaDecision]) -> Dict[str, object]:
        return {
            "tenant_id": tenant_id,
            "resources": [d.to_dict() for d in decisions],
        }

    @staticmethod
    def build_warning(decisions: List[QuotaDecision]) -> str:
        parts = []
        for decision in decisions:
            parts.append(
                f"{decision.resource} {decision.used + decision.requested}/{decision.limit}"
            )
        return "; ".join(parts)

    @staticmethod
    def _normalize_mode(raw: str) -> str:
        value = (raw or "disabled").strip().lower()
        if value not in {"disabled", "soft", "enforce"}:
            return "disabled"
        return value
