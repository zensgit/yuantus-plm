"""Deduplication domain service."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
import logging
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
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.models.job import ConversionJob, JobStatus
from yuantus.meta_engine.services.job_service import JobService


logger = logging.getLogger(__name__)


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

        auto_trigger_workflow = bool(payload.get("auto_trigger_workflow", False))
        workflow_map_id = payload.get("workflow_map_id")
        if isinstance(workflow_map_id, str):
            workflow_map_id = workflow_map_id.strip() or None

        if auto_trigger_workflow and not workflow_map_id:
            raise ValueError("workflow_map_id required when auto_trigger_workflow=true")

        if workflow_map_id:
            # Validate existence early to fail with HTTP 400 rather than a later runtime skip.
            from yuantus.meta_engine.workflow.models import WorkflowMap

            exists = (
                self.session.query(WorkflowMap.id)
                .filter(WorkflowMap.id == workflow_map_id)
                .first()
            )
            if not exists:
                raise ValueError(f"workflow_map_id not found: {workflow_map_id}")
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
            auto_trigger_workflow=auto_trigger_workflow,
            workflow_map_id=workflow_map_id,
            exclude_patterns=payload.get("exclude_patterns") or [],
            priority=payload.get("priority", 100),
            is_active=bool(payload.get("is_active", True)),
            created_by_id=user_id,
            # migrations schema doesn't guarantee a DB default; set explicitly.
            created_at=datetime.utcnow(),
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

        # Validate workflow requirements based on the _resulting_ state after patch.
        new_auto_trigger_workflow = bool(payload.get("auto_trigger_workflow", rule.auto_trigger_workflow))
        new_workflow_map_id = payload.get("workflow_map_id", rule.workflow_map_id)
        if isinstance(new_workflow_map_id, str):
            new_workflow_map_id = new_workflow_map_id.strip() or None

        if new_auto_trigger_workflow and not new_workflow_map_id:
            raise ValueError("workflow_map_id required when auto_trigger_workflow=true")

        if new_workflow_map_id:
            from yuantus.meta_engine.workflow.models import WorkflowMap

            exists = (
                self.session.query(WorkflowMap.id)
                .filter(WorkflowMap.id == new_workflow_map_id)
                .first()
            )
            if not exists:
                raise ValueError(f"workflow_map_id not found: {new_workflow_map_id}")

        # Normalize payload so stored IDs are trimmed / canonical.
        if "workflow_map_id" in payload and isinstance(payload["workflow_map_id"], str):
            payload["workflow_map_id"] = payload["workflow_map_id"].strip() or None
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
        order = [
            DedupRule.priority.asc(),
            DedupRule.created_at.is_(None).asc(),
            DedupRule.created_at.desc(),
            DedupRule.name.asc(),
        ]

        if item_type_id:
            specific = (
                q.filter(DedupRule.item_type_id == item_type_id)
                .order_by(*order)
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
                .order_by(*order)
                .first()
            )
            if doc_rule:
                return doc_rule

        return (
            q.filter(
                DedupRule.item_type_id.is_(None),
                or_(DedupRule.document_type.is_(None), DedupRule.document_type == "all"),
            )
            .order_by(*order)
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
        create_relationship: bool = False,
    ) -> SimilarityRecord:
        record.status = status
        record.review_comment = comment
        record.reviewed_by_id = reviewer_id
        record.reviewed_at = datetime.utcnow()

        if status == SimilarityStatus.CONFIRMED.value:
            rule = self._resolve_rule_for_record(record)
            if create_relationship or (rule and rule.auto_create_relationship):
                rel_id = self._create_equivalent_relationship(record, reviewer_id)
                if rel_id:
                    record.relationship_item_id = rel_id
            rel_item_id = record.relationship_item_id
            if (
                rule
                and bool(rule.auto_trigger_workflow)
                and rule.workflow_map_id
                and rel_item_id
            ):
                proc_id = self._start_workflow_for_item(
                    item_id=str(rel_item_id),
                    workflow_map_id=str(rule.workflow_map_id),
                    user_id=reviewer_id,
                )
                if proc_id:
                    self._annotate_relationship_workflow(
                        relationship_item_id=str(rel_item_id),
                        workflow_process_id=str(proc_id),
                        workflow_map_id=str(rule.workflow_map_id),
                    )

        self.session.add(record)
        self.session.flush()
        return record

    def _rule_id_expr(self):
        """Dialect-aware SQL expression for detection_params.rule_id (string)."""
        dialect = self.session.bind.dialect.name if self.session.bind else "unknown"
        if dialect == "postgresql":
            return func.jsonb_extract_path_text(SimilarityRecord.detection_params, "rule_id")
        if dialect == "sqlite":
            return func.json_extract(SimilarityRecord.detection_params, "$.rule_id")
        return None

    def generate_report(
        self,
        *,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days: int = 30,
        status: Optional[str] = None,
        rule_id: Optional[str] = None,
        batch_id: Optional[str] = None,
        latest_limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Generate a lightweight operational report for SimilarityRecords.
        """
        now = datetime.utcnow()
        end = end_date or now
        start = start_date or (end - timedelta(days=max(int(days), 0)))
        if start > end:
            raise ValueError("start_date must be <= end_date")

        conds = [
            SimilarityRecord.created_at >= start,
            SimilarityRecord.created_at <= end,
        ]
        if status:
            conds.append(SimilarityRecord.status == status)
        if batch_id:
            conds.append(SimilarityRecord.batch_id == batch_id)

        rule_expr = self._rule_id_expr()
        if rule_id and rule_expr is not None:
            conds.append(rule_expr == str(rule_id))

        total = (
            self.session.query(func.count(SimilarityRecord.id))
            .filter(*conds)
            .scalar()
            or 0
        )

        by_status_rows = (
            self.session.query(SimilarityRecord.status, func.count(SimilarityRecord.id))
            .filter(*conds)
            .group_by(SimilarityRecord.status)
            .all()
        )
        by_status: Dict[str, int] = {str(s): int(c) for s, c in by_status_rows if s}

        batch_rows = (
            self.session.query(SimilarityRecord.batch_id, func.count(SimilarityRecord.id))
            .filter(*conds)
            .group_by(SimilarityRecord.batch_id)
            .all()
        )
        by_batch_id: Dict[str, int] = {str(b): int(c) for b, c in batch_rows if b}
        no_batch = int(next((c for b, c in batch_rows if not b), 0))

        by_rule_id: Dict[str, int] = {}
        if rule_expr is not None:
            rule_rows = (
                self.session.query(rule_expr.label("rule_id"), func.count(SimilarityRecord.id))
                .filter(*conds)
                .group_by(rule_expr)
                .all()
            )
            by_rule_id = {str(r): int(c) for r, c in rule_rows if r}
        elif rule_id:
            raise ValueError("rule_id filter is not supported for this database dialect")

        day_expr = func.date(SimilarityRecord.created_at)
        day_rows = (
            self.session.query(
                day_expr.label("day"),
                SimilarityRecord.status,
                func.count(SimilarityRecord.id).label("count"),
            )
            .filter(*conds)
            .group_by(day_expr, SimilarityRecord.status)
            .order_by(day_expr.asc())
            .all()
        )
        by_day_map: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for day, st, count in day_rows:
            day_str = str(day)
            by_day_map[day_str][str(st)] += int(count or 0)
        by_day: List[Dict[str, Any]] = []
        for day_str in sorted(by_day_map.keys()):
            counts = dict(by_day_map[day_str])
            entry: Dict[str, Any] = {"day": day_str, "total": int(sum(counts.values()))}
            entry.update(counts)
            by_day.append(entry)

        latest: List[Dict[str, Any]] = []
        if latest_limit and latest_limit > 0:
            latest_records = (
                self.session.query(SimilarityRecord)
                .filter(*conds)
                .order_by(desc(SimilarityRecord.created_at))
                .limit(int(latest_limit))
                .all()
            )
            for r in latest_records:
                params = r.detection_params or {}
                latest.append(
                    {
                        "id": r.id,
                        "status": r.status,
                        "source_file_id": r.source_file_id,
                        "target_file_id": r.target_file_id,
                        "pair_key": r.pair_key,
                        "similarity_score": r.similarity_score,
                        "rule_id": params.get("rule_id"),
                        "batch_id": r.batch_id,
                        "relationship_item_id": r.relationship_item_id,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                        "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
                    }
                )

        return {
            "generated_at": now.isoformat() + "Z",
            "window": {
                "start_date": start.isoformat() + "Z",
                "end_date": end.isoformat() + "Z",
                "days": int(days),
            },
            "filters": {
                "status": status,
                "rule_id": rule_id,
                "batch_id": batch_id,
            },
            "total": int(total),
            "by_status": by_status,
            "by_batch_id": by_batch_id,
            "no_batch": no_batch,
            "by_rule_id": by_rule_id,
            "by_day": by_day,
            "latest": latest,
        }

    def list_records_for_export(
        self,
        *,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days: int = 30,
        status: Optional[str] = None,
        rule_id: Optional[str] = None,
        batch_id: Optional[str] = None,
        limit: int = 5000,
    ) -> List[Dict[str, Any]]:
        now = datetime.utcnow()
        end = end_date or now
        start = start_date or (end - timedelta(days=max(int(days), 0)))
        if start > end:
            raise ValueError("start_date must be <= end_date")

        conds = [
            SimilarityRecord.created_at >= start,
            SimilarityRecord.created_at <= end,
        ]
        if status:
            conds.append(SimilarityRecord.status == status)
        if batch_id:
            conds.append(SimilarityRecord.batch_id == batch_id)

        rule_expr = self._rule_id_expr()
        if rule_id and rule_expr is not None:
            conds.append(rule_expr == str(rule_id))
        elif rule_id:
            raise ValueError("rule_id filter is not supported for this database dialect")

        records = (
            self.session.query(SimilarityRecord)
            .filter(*conds)
            .order_by(desc(SimilarityRecord.created_at))
            .limit(int(limit))
            .all()
        )
        out: List[Dict[str, Any]] = []
        for r in records:
            params = r.detection_params or {}
            out.append(
                {
                    "id": r.id,
                    "status": r.status,
                    "source_file_id": r.source_file_id,
                    "target_file_id": r.target_file_id,
                    "pair_key": r.pair_key,
                    "similarity_score": r.similarity_score,
                    "rule_id": params.get("rule_id"),
                    "batch_id": r.batch_id,
                    "reviewed_by_id": r.reviewed_by_id,
                    "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
                    "relationship_item_id": r.relationship_item_id,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
            )
        return out

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
        rule_id: Optional[str] = None,
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

            # Apply rule thresholds to search results (important when upstream search API
            # doesn't enforce our thresholds, e.g. progressive v2).
            phash_distance = match.get("phash_distance")
            if phash_distance is None:
                levels = match.get("levels")
                if isinstance(levels, dict):
                    l1 = levels.get("l1")
                    if isinstance(l1, dict):
                        phash_distance = l1.get("phash_distance")
            if phash_distance is not None:
                try:
                    if int(phash_distance) > int(phash_threshold):
                        continue
                except (TypeError, ValueError):
                    pass

            feature_similarity = match.get("feature_similarity")
            if feature_similarity is None:
                levels = match.get("levels")
                if isinstance(levels, dict):
                    l2 = levels.get("l2")
                    if isinstance(l2, dict):
                        feature_similarity = l2.get("feature_similarity")
            if feature_similarity is not None:
                try:
                    if float(feature_similarity) < float(feature_threshold):
                        continue
                except (TypeError, ValueError):
                    pass

            pair_key = self._build_pair_key(source_file.id, target_file_id)
            record_values = {
                "id": str(uuid.uuid4()),
                "source_file_id": source_file.id,
                "target_file_id": target_file_id,
                "pair_key": pair_key,
                "similarity_score": score,
                "similarity_type": "visual",
                "detection_method": mode,
                "detection_params": {
                    "mode": mode,
                    "phash_threshold": phash_threshold,
                    "feature_threshold": feature_threshold,
                    "rule_id": rule_id,
                    "raw": match,
                },
                "status": SimilarityStatus.PENDING.value,
                "batch_id": batch_id,
                # migrations schema doesn't guarantee a DB default; set explicitly so reporting
                # and ordering works in both sqlite/postgresql.
                "created_at": datetime.utcnow(),
            }

            dialect = self.session.bind.dialect.name if self.session.bind else "unknown"
            # Concurrency-safe insert: avoid duplicate unordered pairs without raising.
            if dialect == "postgresql":
                from sqlalchemy.dialects.postgresql import insert as pg_insert

                stmt = (
                    pg_insert(SimilarityRecord)
                    .values(**record_values)
                    .on_conflict_do_nothing(index_elements=["pair_key"])
                )
                res = self.session.execute(stmt)
                if res.rowcount:
                    created += 1
            elif dialect == "sqlite":
                from sqlalchemy.dialects.sqlite import insert as sqlite_insert

                stmt = (
                    sqlite_insert(SimilarityRecord)
                    .values(**record_values)
                    .on_conflict_do_nothing(index_elements=["pair_key"])
                )
                res = self.session.execute(stmt)
                if res.rowcount:
                    created += 1
            else:
                existing = (
                    self.session.query(SimilarityRecord)
                    .filter(SimilarityRecord.pair_key == pair_key)
                    .first()
                )
                if existing:
                    continue
                self.session.add(SimilarityRecord(**record_values))
                created += 1

        if created:
            self.session.flush()
        return created

    def _resolve_rule_for_record(self, record: SimilarityRecord) -> Optional[DedupRule]:
        params = record.detection_params or {}
        rule_id = params.get("rule_id")
        if not rule_id:
            return None
        return self.get_rule(str(rule_id))

    def _resolve_item_for_file(self, file_id: str) -> Optional[Item]:
        item_file = (
            self.session.query(ItemFile)
            .filter(ItemFile.file_id == file_id)
            .order_by(ItemFile.created_at.desc())
            .first()
        )
        if not item_file:
            return None
        return self.session.get(Item, item_file.item_id)

    def _ensure_equivalent_item_type(self) -> None:
        type_id = "Part Equivalent"
        existing = self.session.query(ItemType).filter_by(id=type_id).first()
        if existing:
            return
        new_type = ItemType(
            id=type_id,
            label="Part Equivalent",
            description="Equivalent part relationship",
            is_relationship=True,
            is_versionable=False,
        )
        self.session.add(new_type)
        self.session.flush()

    def _create_equivalent_relationship(
        self, record: SimilarityRecord, user_id: Optional[int]
    ) -> Optional[str]:
        if record.relationship_item_id:
            return record.relationship_item_id
        source_item = self._resolve_item_for_file(record.source_file_id)
        target_item = self._resolve_item_for_file(record.target_file_id)
        if not source_item or not target_item:
            return None
        if source_item.item_type_id != "Part" or target_item.item_type_id != "Part":
            return None

        self._ensure_equivalent_item_type()

        existing = (
            self.session.query(Item)
            .filter(
                Item.item_type_id == "Part Equivalent",
                Item.is_current.is_(True),
                or_(
                    and_(
                        Item.source_id == source_item.id,
                        Item.related_id == target_item.id,
                    ),
                    and_(
                        Item.source_id == target_item.id,
                        Item.related_id == source_item.id,
                    ),
                ),
            )
            .first()
        )
        if existing:
            return existing.id

        rel = Item(
            id=str(uuid.uuid4()),
            item_type_id="Part Equivalent",
            config_id=str(uuid.uuid4()),
            generation=1,
            is_current=True,
            state="Active",
            source_id=source_item.id,
            related_id=target_item.id,
            properties={
                "similarity_record_id": record.id,
                "similarity_score": record.similarity_score,
            },
            created_by_id=user_id,
            created_at=datetime.utcnow(),
        )
        self.session.add(rel)
        self.session.flush()
        return rel.id

    def _start_workflow_for_item(
        self,
        *,
        item_id: str,
        workflow_map_id: str,
        user_id: Optional[int],
    ) -> Optional[str]:
        """
        Best-effort workflow trigger.

        Uses WorkflowService.start_workflow(map_name) internally; if the workflow map is missing
        or a process is already active, this is treated as a no-op.
        """
        if not item_id or not workflow_map_id:
            return None
        try:
            from yuantus.meta_engine.workflow.models import WorkflowMap
            from yuantus.meta_engine.workflow.service import WorkflowService
        except Exception:
            return None

        wf_map = self.session.get(WorkflowMap, workflow_map_id)
        if not wf_map:
            logger.warning("Dedup workflow map not found: %s", workflow_map_id)
            return None

        svc = WorkflowService(self.session)
        try:
            proc = svc.start_workflow(item_id, wf_map.name, int(user_id or 1))
        except Exception as exc:
            # ValueError is expected when an active process already exists for this item.
            logger.info(
                "Dedup workflow start skipped: item_id=%s workflow_map_id=%s error=%s",
                item_id,
                workflow_map_id,
                exc,
            )
            return None
        return proc.id

    def _annotate_relationship_workflow(
        self,
        *,
        relationship_item_id: str,
        workflow_process_id: str,
        workflow_map_id: str,
    ) -> None:
        rel = self.session.get(Item, relationship_item_id)
        if not rel:
            return
        props = dict(rel.properties or {})
        props.setdefault("workflow_map_id", workflow_map_id)
        props.setdefault("workflow_process_id", workflow_process_id)
        rel.properties = props
        self.session.add(rel)

    # -------------------- Helpers --------------------

    @staticmethod
    def _build_pair_key(file_id_a: str, file_id_b: str) -> str:
        """
        Stable unordered pair key for SimilarityRecord uniqueness.

        Format: "<min_uuid>|<max_uuid>" using lexical order on UUID strings.
        """
        a = str(file_id_a or "").strip()
        b = str(file_id_b or "").strip()
        if not a or not b:
            return f"{a}|{b}"
        return f"{a}|{b}" if a < b else f"{b}|{a}"

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
        index: bool = False,
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
                "index": bool(index),
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
                "index": bool(index),
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
