"""Deduplication domain service."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple
import uuid

from sqlalchemy import and_, or_, desc, func
from sqlalchemy.orm import Session

from yuantus.meta_engine.dedup.models import (
    DedupBatch,
    DedupBatchStatus,
    DedupRule,
    SimilarityRecord,
    SimilarityStatus,
)
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.models.file import ItemFile
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.job import ConversionJob, JobStatus
from yuantus.meta_engine.services.job_service import JobService


class DedupService:
    """Service for dedup rules, records, and ingestion."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # -------------------- Rules --------------------

    def create_rule(self, payload: Dict[str, Any], *, user_id: Optional[int] = None) -> DedupRule:
        name = (payload.get("name") or "").strip()
        if not name:
            raise ValueError("Rule name required")
        existing = self.session.query(DedupRule).filter(DedupRule.name == name).first()
        if existing:
            raise ValueError("Rule name already exists")
        rule = DedupRule(
            id=payload.get("id") or str(uuid.uuid4()),
            name=name,
            description=payload.get("description"),
            item_type_id=payload.get("item_type_id"),
            document_type=payload.get("document_type"),
            phash_threshold=payload.get("phash_threshold", 10),
            feature_threshold=payload.get("feature_threshold", 0.85),
            combined_threshold=payload.get("combined_threshold", 0.80),
            detection_mode=payload.get("detection_mode", "balanced"),
            auto_create_relationship=bool(payload.get("auto_create_relationship", False)),
            auto_trigger_workflow=bool(payload.get("auto_trigger_workflow", False)),
            workflow_map_id=payload.get("workflow_map_id"),
            exclude_patterns=payload.get("exclude_patterns") or [],
            priority=payload.get("priority", 100),
            is_active=bool(payload.get("is_active", True)),
            created_by_id=user_id,
        )
        self.session.add(rule)
        self.session.flush()
        return rule

    def list_rules(self, *, include_inactive: bool = False) -> List[DedupRule]:
        q = self.session.query(DedupRule)
        if not include_inactive:
            q = q.filter(DedupRule.is_active.is_(True))
        return q.order_by(DedupRule.priority.asc(), DedupRule.name.asc()).all()

    def get_rule(self, rule_id: str) -> Optional[DedupRule]:
        return self.session.get(DedupRule, rule_id)

    def update_rule(self, rule: DedupRule, payload: Dict[str, Any]) -> DedupRule:
        if "name" in payload and payload["name"]:
            name = payload["name"].strip()
            existing = (
                self.session.query(DedupRule)
                .filter(DedupRule.name == name, DedupRule.id != rule.id)
                .first()
            )
            if existing:
                raise ValueError("Rule name already exists")
            rule.name = name
        for field in [
            "description",
            "item_type_id",
            "document_type",
            "phash_threshold",
            "feature_threshold",
            "combined_threshold",
            "detection_mode",
            "auto_create_relationship",
            "auto_trigger_workflow",
            "workflow_map_id",
            "exclude_patterns",
            "priority",
            "is_active",
        ]:
            if field in payload:
                setattr(rule, field, payload[field])
        self.session.add(rule)
        self.session.flush()
        return rule

    def deactivate_rule(self, rule: DedupRule) -> None:
        rule.is_active = False
        self.session.add(rule)
        self.session.flush()

    def get_applicable_rule(
        self, *, item_type_id: Optional[str] = None, document_type: Optional[str] = None
    ) -> Optional[DedupRule]:
        q = self.session.query(DedupRule).filter(DedupRule.is_active.is_(True))

        if item_type_id:
            specific = (
                q.filter(DedupRule.item_type_id == item_type_id)
                .order_by(DedupRule.priority.asc())
                .first()
            )
            if specific:
                return specific

        if document_type:
            doc_rule = (
                q.filter(
                    and_(
                        DedupRule.item_type_id.is_(None),
                        or_(
                            DedupRule.document_type == document_type,
                            DedupRule.document_type == "all",
                        ),
                    )
                )
                .order_by(DedupRule.priority.asc())
                .first()
            )
            if doc_rule:
                return doc_rule

        return (
            q.filter(
                DedupRule.item_type_id.is_(None),
                or_(DedupRule.document_type.is_(None), DedupRule.document_type == "all"),
            )
            .order_by(DedupRule.priority.asc())
            .first()
        )

    # -------------------- Records --------------------

    def list_records(
        self,
        *,
        status: Optional[str] = None,
        source_file_id: Optional[str] = None,
        target_file_id: Optional[str] = None,
        batch_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[SimilarityRecord], int]:
        q = self.session.query(SimilarityRecord)
        if status:
            q = q.filter(SimilarityRecord.status == status)
        if source_file_id:
            q = q.filter(SimilarityRecord.source_file_id == source_file_id)
        if target_file_id:
            q = q.filter(SimilarityRecord.target_file_id == target_file_id)
        if batch_id:
            q = q.filter(SimilarityRecord.batch_id == batch_id)

        total = q.count()
        items = (
            q.order_by(desc(SimilarityRecord.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
        return items, total

    def get_record(self, record_id: str) -> Optional[SimilarityRecord]:
        return self.session.get(SimilarityRecord, record_id)

    def review_record(
        self,
        record: SimilarityRecord,
        *,
        status: str,
        reviewer_id: Optional[int],
        comment: Optional[str] = None,
    ) -> SimilarityRecord:
        record.status = status
        record.review_comment = comment
        record.reviewed_by_id = reviewer_id
        record.reviewed_at = datetime.utcnow()
        self.session.add(record)
        self.session.flush()
        return record

    # -------------------- Ingestion --------------------

    def ingest_search_results(
        self,
        *,
        source_file: FileContainer,
        search: Dict[str, Any],
        mode: str,
        phash_threshold: int,
        feature_threshold: float,
        combined_threshold: float,
        batch_id: Optional[str] = None,
    ) -> int:
        matches = list(self._iter_search_matches(search))
        if not matches:
            return 0

        created = 0
        for match in matches:
            target_file_id = self._resolve_target_file_id(match)
            if not target_file_id or target_file_id == source_file.id:
                continue

            score = self._extract_score(match)
            if score is None:
                continue
            if score < combined_threshold:
                continue

            existing = self.session.query(SimilarityRecord).filter(
                or_(
                    and_(
                        SimilarityRecord.source_file_id == source_file.id,
                        SimilarityRecord.target_file_id == target_file_id,
                    ),
                    and_(
                        SimilarityRecord.source_file_id == target_file_id,
                        SimilarityRecord.target_file_id == source_file.id,
                    ),
                )
            ).first()
            if existing:
                continue

            record = SimilarityRecord(
                id=str(uuid.uuid4()),
                source_file_id=source_file.id,
                target_file_id=target_file_id,
                similarity_score=score,
                similarity_type="visual",
                detection_method=mode,
                detection_params={
                    "mode": mode,
                    "phash_threshold": phash_threshold,
                    "feature_threshold": feature_threshold,
                    "raw": match,
                },
                status=SimilarityStatus.PENDING.value,
                batch_id=batch_id,
            )
            self.session.add(record)
            created += 1

        if created:
            self.session.flush()
        return created

    # -------------------- Helpers --------------------

    def _iter_search_matches(self, search: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        for key in ("results", "duplicates", "similar", "matches"):
            val = search.get(key)
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        yield item
        # Some versions might nest under "search"
        nested = search.get("search")
        if isinstance(nested, dict):
            for key in ("results", "duplicates", "similar", "matches"):
                val = nested.get(key)
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, dict):
                            yield item

    def _extract_score(self, match: Dict[str, Any]) -> Optional[float]:
        for key in ("similarity", "score", "confidence"):
            val = match.get(key)
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):
                try:
                    return float(val)
                except ValueError:
                    continue
        return None

    def _resolve_target_file_id(self, match: Dict[str, Any]) -> Optional[str]:
        for key in ("file_id", "drawing_id", "id"):
            candidate = match.get(key)
            if candidate:
                candidate = str(candidate)
                if self.session.get(FileContainer, candidate):
                    return candidate

        for key in ("file_hash", "checksum", "sha256"):
            val = match.get(key)
            if not val:
                continue
            checksum = str(val)
            file_row = (
                self.session.query(FileContainer)
                .filter(FileContainer.checksum == checksum)
                .first()
            )
            if file_row:
                return file_row.id
        return None

    # -------------------- Batches --------------------

    def create_batch(self, payload: Dict[str, Any], *, user_id: Optional[int]) -> DedupBatch:
        batch = DedupBatch(
            id=payload.get("id") or str(uuid.uuid4()),
            name=payload.get("name"),
            description=payload.get("description"),
            scope_type=payload.get("scope_type", "all"),
            scope_config=payload.get("scope_config") or {},
            rule_id=payload.get("rule_id"),
            status=payload.get("status", DedupBatchStatus.QUEUED.value),
            created_by_id=user_id,
        )
        self.session.add(batch)
        self.session.flush()
        return batch

    def resolve_batch_files(
        self, batch: DedupBatch, *, limit: Optional[int] = None
    ) -> List[FileContainer]:
        scope_type = (batch.scope_type or "all").strip().lower()
        scope = batch.scope_config or {}

        query = self.session.query(FileContainer)

        if scope_type in {"file_list", "files"}:
            file_ids = scope.get("file_ids") or scope.get("files") or []
            if not file_ids:
                return []
            query = query.filter(FileContainer.id.in_(list(file_ids)))
        elif scope_type in {"document_type", "doc_type"}:
            doc_type = scope.get("document_type") or scope.get("doc_type")
            if not doc_type:
                return []
            query = query.filter(FileContainer.document_type == doc_type)
        elif scope_type in {"file_type", "extension"}:
            file_type = scope.get("file_type") or scope.get("extension")
            if not file_type:
                return []
            query = query.filter(FileContainer.file_type == str(file_type).lower())
        elif scope_type in {"item_type", "item_type_id"}:
            item_type_id = scope.get("item_type_id") or scope.get("item_type")
            if not item_type_id:
                return []
            query = (
                query.join(ItemFile, ItemFile.file_id == FileContainer.id)
                .join(Item, Item.id == ItemFile.item_id)
                .filter(Item.item_type_id == item_type_id)
            )
        elif scope_type in {"folder", "path_prefix"}:
            prefix = (
                scope.get("path_prefix")
                or scope.get("prefix")
                or scope.get("folder")
            )
            if not prefix:
                return []
            prefix = str(prefix).rstrip("/")
            query = query.filter(FileContainer.system_path.like(f"{prefix}/%"))
        else:
            # default: all files
            pass

        query = query.order_by(FileContainer.created_at.desc())
        if limit:
            query = query.limit(limit)
        return query.all()

    def run_batch(
        self,
        batch: DedupBatch,
        *,
        user_id: Optional[int],
        user_name: str,
        mode: Optional[str] = None,
        limit: Optional[int] = None,
        priority: int = 30,
        dedupe: bool = True,
        rule_id: Optional[str] = None,
    ) -> Tuple[int, List[str]]:
        effective_rule_id = rule_id or batch.rule_id
        rule = self.get_rule(effective_rule_id) if effective_rule_id else None
        effective_mode = mode or (rule.detection_mode if rule else "balanced")

        files = self.resolve_batch_files(batch, limit=limit)
        job_service = JobService(self.session)
        job_ids: List[str] = []

        for file in files:
            payload = {
                "file_id": file.id,
                "mode": effective_mode,
                "user_name": user_name,
                "batch_id": batch.id,
                "rule_id": rule.id if rule else None,
            }
            job = job_service.create_job(
                "cad_dedup_vision",
                payload,
                user_id=user_id,
                priority=priority,
                dedupe=dedupe,
            )
            job_ids.append(job.id)

        batch.status = DedupBatchStatus.RUNNING.value
        batch.started_at = datetime.utcnow()
        batch.total_files = len(files)
        batch.processed_files = len(job_ids)
        summary = dict(batch.summary or {})
        summary.update(
            {
                "jobs_created": len(job_ids),
                "mode": effective_mode,
                "rule_id": rule.id if rule else None,
            }
        )
        if limit:
            summary["limit"] = limit
        batch.summary = summary
        self.session.add(batch)
        self.session.flush()
        return len(job_ids), job_ids

    def refresh_batch(self, batch: DedupBatch) -> DedupBatch:
        found = (
            self.session.query(SimilarityRecord)
            .filter(SimilarityRecord.batch_id == batch.id)
            .count()
        )
        batch.found_similarities = found

        jobs = self._get_jobs_for_batch(batch.id)
        if jobs is not None:
            total = len(jobs)
            status_counts = {
                JobStatus.PENDING.value: 0,
                JobStatus.PROCESSING.value: 0,
                JobStatus.COMPLETED.value: 0,
                JobStatus.FAILED.value: 0,
                JobStatus.CANCELLED.value: 0,
            }
            for job in jobs:
                status_counts[job.status] = status_counts.get(job.status, 0) + 1

            batch.total_files = total
            batch.processed_files = (
                status_counts.get(JobStatus.COMPLETED.value, 0)
                + status_counts.get(JobStatus.FAILED.value, 0)
                + status_counts.get(JobStatus.CANCELLED.value, 0)
            )

            if status_counts.get(JobStatus.PENDING.value, 0) or status_counts.get(
                JobStatus.PROCESSING.value, 0
            ):
                batch.status = DedupBatchStatus.RUNNING.value
            elif status_counts.get(JobStatus.FAILED.value, 0):
                batch.status = DedupBatchStatus.FAILED.value
                batch.completed_at = datetime.utcnow()
            else:
                batch.status = DedupBatchStatus.COMPLETED.value
                batch.completed_at = datetime.utcnow()

            summary = dict(batch.summary or {})
            summary["job_status"] = status_counts
            batch.summary = summary

        self.session.add(batch)
        self.session.flush()
        return batch

    def _get_jobs_for_batch(self, batch_id: str) -> Optional[List[ConversionJob]]:
        if not batch_id:
            return []
        dialect = self.session.bind.dialect.name if self.session.bind else "unknown"
        query = self.session.query(ConversionJob).filter(
            ConversionJob.task_type == "cad_dedup_vision"
        )
        if dialect == "postgresql":
            return (
                query.filter(func.jsonb_extract_path_text(ConversionJob.payload, "batch_id") == batch_id)
                .order_by(ConversionJob.created_at.desc())
                .all()
            )
        jobs = query.order_by(ConversionJob.created_at.desc()).all()
        return [
            job
            for job in jobs
            if isinstance(job.payload, dict) and job.payload.get("batch_id") == batch_id
        ]
