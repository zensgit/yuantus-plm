# YuantusPLM 对标 Aras Innovator 详细开发方案

> 版本：v1.0
> 日期：2026-01-31
> 目标：使 YuantusPLM 达到并超越 Aras Innovator 核心能力

---

## 目录

1. [总体规划](#1-总体规划)
2. [Phase 1: 图纸去重闭环](#2-phase-1-图纸去重闭环)
3. [Phase 2: 配置管理 (Variant BOM)](#3-phase-2-配置管理-variant-bom)
4. [Phase 3: MBOM 与工艺路线](#4-phase-3-mbom-与工艺路线)
5. [Phase 4: 基线管理增强](#5-phase-4-基线管理增强)
6. [Phase 5: 高级搜索与报表](#6-phase-5-高级搜索与报表)
7. [Phase 6: 电子签名](#7-phase-6-电子签名)
8. [数据库迁移计划](#8-数据库迁移计划)
9. [验证计划](#9-验证计划)

---

## 1. 总体规划

### 1.1 时间线

| Phase | 名称 | 工期 | 依赖 |
|-------|------|------|------|
| P1 | 图纸去重闭环 | 3 周 | - |
| P2 | 配置管理 | 4 周 | - |
| P3 | MBOM 与工艺 | 5 周 | P2 |
| P4 | 基线管理增强 | 2 周 | - |
| P5 | 高级搜索与报表 | 3 周 | - |
| P6 | 电子签名 | 3 周 | - |

### 1.2 目录结构新增

```
src/yuantus/meta_engine/
├── dedup/                      # Phase 1: 图纸去重
│   ├── __init__.py
│   ├── models.py              # SimilarityRecord, DedupRule, DedupBatch
│   ├── service.py             # DedupService
│   ├── router.py              # API 端点
│   └── tasks.py               # 异步任务
├── configuration/              # Phase 2: 配置管理
│   ├── __init__.py
│   ├── models.py              # OptionSet, OptionItem, VariantRule
│   ├── service.py             # ConfigurationService
│   ├── validator.py           # 配置有效性校验
│   └── router.py
├── manufacturing/              # Phase 3: 制造
│   ├── __init__.py
│   ├── models.py              # MBOM, Routing, Operation
│   ├── mbom_service.py
│   ├── routing_service.py
│   └── router.py
├── baseline/                   # Phase 4: 基线增强
│   ├── __init__.py
│   ├── service.py             # BaselineService (增强)
│   └── router.py
├── reports/                    # Phase 5: 报表
│   ├── __init__.py
│   ├── engine.py
│   ├── templates/
│   └── router.py
└── esign/                      # Phase 6: 电子签名
    ├── __init__.py
    ├── models.py
    ├── service.py
    └── router.py
```

---

## 2. Phase 1: 图纸去重闭环

### 2.1 目标

将当前的"去重检测"升级为"去重管理闭环"：检测 → 存储 → 审核 → 关系建立 → 报表。

### 2.2 数据模型

#### `src/yuantus/meta_engine/dedup/models.py`

```python
"""
图纸去重数据模型
"""
from sqlalchemy import (
    Column, String, Float, Integer, ForeignKey, DateTime,
    Boolean, Text, JSON, Enum
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from yuantus.models.base import Base


class SimilarityStatus(str, enum.Enum):
    """相似性记录状态"""
    PENDING = "pending"           # 待审核
    CONFIRMED = "confirmed"       # 确认为重复
    REJECTED = "rejected"         # 确认为不同件
    MERGED = "merged"             # 已合并
    IGNORED = "ignored"           # 忽略


class DedupBatchStatus(str, enum.Enum):
    """批量去重任务状态"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SimilarityRecord(Base):
    """
    相似性记录表
    存储检测到的相似图纸关系
    """
    __tablename__ = "meta_similarity_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 源文件（被检测的文件）
    source_file_id = Column(String, ForeignKey("meta_files.id"), nullable=False, index=True)

    # 目标文件（相似的文件）
    target_file_id = Column(String, ForeignKey("meta_files.id"), nullable=False, index=True)

    # 相似度分数 (0.0 - 1.0)
    similarity_score = Column(Float, nullable=False)

    # 相似性类型
    similarity_type = Column(String, default="visual")  # visual, geometric, attribute

    # 检测方法
    detection_method = Column(String)  # phash, feature, combined

    # 检测参数（JSON）
    detection_params = Column(JSON().with_variant(JSONB, "postgresql"))

    # 状态
    status = Column(String, default=SimilarityStatus.PENDING.value, index=True)

    # 审核信息
    reviewed_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_comment = Column(Text, nullable=True)

    # 关联的 Item 关系 ID（如果已创建关系）
    relationship_item_id = Column(String, ForeignKey("meta_items.id"), nullable=True)

    # 批次 ID（如果来自批量检测）
    batch_id = Column(String, ForeignKey("meta_dedup_batches.id"), nullable=True)

    # 审计
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    source_file = relationship("FileContainer", foreign_keys=[source_file_id])
    target_file = relationship("FileContainer", foreign_keys=[target_file_id])
    reviewed_by = relationship("RBACUser", foreign_keys=[reviewed_by_id])


class DedupRule(Base):
    """
    去重规则配置表
    可按 ItemType 或全局配置不同的阈值和行为
    """
    __tablename__ = "meta_dedup_rules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    name = Column(String, nullable=False, unique=True)
    description = Column(Text)

    # 适用范围
    item_type_id = Column(String, ForeignKey("meta_item_types.id"), nullable=True)
    document_type = Column(String, nullable=True)  # 2d, 3d, all

    # 阈值配置
    phash_threshold = Column(Integer, default=10)
    feature_threshold = Column(Float, default=0.85)
    combined_threshold = Column(Float, default=0.80)

    # 检测模式
    detection_mode = Column(String, default="balanced")  # fast, balanced, thorough

    # 行为配置
    auto_create_relationship = Column(Boolean, default=False)
    auto_trigger_workflow = Column(Boolean, default=False)
    workflow_map_id = Column(String, ForeignKey("meta_workflow_maps.id"), nullable=True)

    # 排除规则（JSON 数组）
    exclude_patterns = Column(JSON().with_variant(JSONB, "postgresql"))

    # 优先级（数字越小优先级越高）
    priority = Column(Integer, default=100)

    # 启用状态
    is_active = Column(Boolean, default=True)

    # 审计
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)


class DedupBatch(Base):
    """
    批量去重任务表
    跟踪批量去重检测的执行状态
    """
    __tablename__ = "meta_dedup_batches"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    name = Column(String)
    description = Column(Text)

    # 范围配置
    scope_type = Column(String, default="all")  # all, item_type, folder, file_list
    scope_config = Column(JSON().with_variant(JSONB, "postgresql"))

    # 使用的规则
    rule_id = Column(String, ForeignKey("meta_dedup_rules.id"), nullable=True)

    # 状态
    status = Column(String, default=DedupBatchStatus.QUEUED.value, index=True)

    # 进度
    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)
    found_similarities = Column(Integer, default=0)

    # 执行信息
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    # 结果摘要（JSON）
    summary = Column(JSON().with_variant(JSONB, "postgresql"))

    # 审计
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)

    # Relationships
    rule = relationship("DedupRule", foreign_keys=[rule_id])
    created_by = relationship("RBACUser", foreign_keys=[created_by_id])
    records = relationship("SimilarityRecord", backref="batch", foreign_keys="SimilarityRecord.batch_id")
```

### 2.3 服务层

#### `src/yuantus/meta_engine/dedup/service.py`

```python
"""
图纸去重服务
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from yuantus.meta_engine.dedup.models import (
    SimilarityRecord, SimilarityStatus,
    DedupRule, DedupBatch, DedupBatchStatus
)
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.file_service import FileService
from yuantus.integrations.dedup_vision import DedupVisionClient
from yuantus.config import get_settings

logger = logging.getLogger(__name__)


class DedupService:
    """图纸去重服务"""

    def __init__(self, session: Session):
        self.session = session
        self.file_service = FileService()
        self.vision_client = DedupVisionClient()

    # ==================== 规则管理 ====================

    def create_rule(
        self,
        name: str,
        *,
        description: str = None,
        item_type_id: str = None,
        document_type: str = None,
        phash_threshold: int = 10,
        feature_threshold: float = 0.85,
        combined_threshold: float = 0.80,
        detection_mode: str = "balanced",
        auto_create_relationship: bool = False,
        auto_trigger_workflow: bool = False,
        workflow_map_id: str = None,
        exclude_patterns: List[str] = None,
        priority: int = 100,
        user_id: int = None,
    ) -> DedupRule:
        """创建去重规则"""
        rule = DedupRule(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            item_type_id=item_type_id,
            document_type=document_type,
            phash_threshold=phash_threshold,
            feature_threshold=feature_threshold,
            combined_threshold=combined_threshold,
            detection_mode=detection_mode,
            auto_create_relationship=auto_create_relationship,
            auto_trigger_workflow=auto_trigger_workflow,
            workflow_map_id=workflow_map_id,
            exclude_patterns=exclude_patterns or [],
            priority=priority,
            created_by_id=user_id,
        )
        self.session.add(rule)
        self.session.flush()
        return rule

    def get_applicable_rule(
        self,
        item_type_id: str = None,
        document_type: str = None,
    ) -> Optional[DedupRule]:
        """获取适用的去重规则（按优先级）"""
        query = self.session.query(DedupRule).filter(
            DedupRule.is_active == True
        )

        # 优先匹配具体的 ItemType
        if item_type_id:
            specific = query.filter(
                DedupRule.item_type_id == item_type_id
            ).order_by(DedupRule.priority).first()
            if specific:
                return specific

        # 匹配文档类型
        if document_type:
            doc_rule = query.filter(
                and_(
                    DedupRule.item_type_id.is_(None),
                    or_(
                        DedupRule.document_type == document_type,
                        DedupRule.document_type == "all"
                    )
                )
            ).order_by(DedupRule.priority).first()
            if doc_rule:
                return doc_rule

        # 返回全局默认规则
        return query.filter(
            DedupRule.item_type_id.is_(None),
            or_(DedupRule.document_type.is_(None), DedupRule.document_type == "all")
        ).order_by(DedupRule.priority).first()

    # ==================== 单文件去重检测 ====================

    def check_similarity(
        self,
        file_id: str,
        *,
        rule_id: str = None,
        max_results: int = 5,
        index_after_check: bool = False,
        user_id: int = None,
        authorization: str = None,
    ) -> Dict[str, Any]:
        """
        检测单个文件的相似性

        Args:
            file_id: 文件 ID
            rule_id: 指定使用的规则 ID
            max_results: 返回的最大相似结果数
            index_after_check: 检测后是否加入索引
            user_id: 操作用户 ID
            authorization: 外部服务授权 token

        Returns:
            {
                "file_id": str,
                "similarities": [...],
                "records_created": int,
                "rule_applied": str
            }
        """
        file_container = self.session.get(FileContainer, file_id)
        if not file_container:
            raise ValueError(f"File not found: {file_id}")

        # 获取适用规则
        rule = None
        if rule_id:
            rule = self.session.get(DedupRule, rule_id)
        if not rule:
            rule = self.get_applicable_rule(
                document_type=file_container.document_type
            )

        # 准备参数
        phash_threshold = rule.phash_threshold if rule else 10
        feature_threshold = rule.feature_threshold if rule else 0.85
        mode = rule.detection_mode if rule else "balanced"

        # 获取文件本地路径
        local_path = self._get_local_path(file_container)
        if not local_path:
            raise ValueError(f"Cannot access file: {file_id}")

        try:
            # 调用 DedupVision 服务
            result = self.vision_client.search_sync(
                file_path=local_path,
                mode=mode,
                phash_threshold=phash_threshold,
                feature_threshold=feature_threshold,
                max_results=max_results,
                exclude_self=True,
                authorization=authorization,
            )

            similarities = result.get("results") or []
            records_created = 0

            # 存储相似性记录
            for sim in similarities:
                target_file_id = sim.get("file_id")
                score = sim.get("score", 0)

                if not target_file_id or score < (rule.combined_threshold if rule else 0.80):
                    continue

                # 检查是否已存在记录
                existing = self.session.query(SimilarityRecord).filter(
                    or_(
                        and_(
                            SimilarityRecord.source_file_id == file_id,
                            SimilarityRecord.target_file_id == target_file_id
                        ),
                        and_(
                            SimilarityRecord.source_file_id == target_file_id,
                            SimilarityRecord.target_file_id == file_id
                        )
                    )
                ).first()

                if not existing:
                    record = SimilarityRecord(
                        id=str(uuid.uuid4()),
                        source_file_id=file_id,
                        target_file_id=target_file_id,
                        similarity_score=score,
                        similarity_type="visual",
                        detection_method=mode,
                        detection_params={
                            "phash_threshold": phash_threshold,
                            "feature_threshold": feature_threshold,
                        },
                        status=SimilarityStatus.PENDING.value,
                    )
                    self.session.add(record)
                    records_created += 1

                    # 自动创建关系（如果规则允许）
                    if rule and rule.auto_create_relationship:
                        rel_id = self._create_similarity_relationship(
                            file_id, target_file_id, score, user_id
                        )
                        record.relationship_item_id = rel_id

            # 索引到 DedupVision
            if index_after_check:
                try:
                    self.vision_client.index_add_sync(
                        file_path=local_path,
                        user_name=str(user_id) if user_id else "system",
                        upload_to_s3=False,
                        authorization=authorization,
                    )
                except Exception as e:
                    logger.warning(f"Failed to index file {file_id}: {e}")

            self.session.flush()

            return {
                "file_id": file_id,
                "similarities": similarities,
                "records_created": records_created,
                "rule_applied": rule.name if rule else None,
            }

        finally:
            # 清理临时文件（如果是从 S3 下载的）
            self._cleanup_temp_file(local_path, file_container)

    # ==================== 批量去重 ====================

    def create_batch(
        self,
        name: str,
        *,
        scope_type: str = "all",
        scope_config: Dict[str, Any] = None,
        rule_id: str = None,
        user_id: int = None,
    ) -> DedupBatch:
        """
        创建批量去重任务

        Args:
            name: 任务名称
            scope_type: 范围类型 (all, item_type, folder, file_list)
            scope_config: 范围配置
            rule_id: 使用的规则 ID
            user_id: 创建用户

        Returns:
            DedupBatch
        """
        batch = DedupBatch(
            id=str(uuid.uuid4()),
            name=name,
            scope_type=scope_type,
            scope_config=scope_config or {},
            rule_id=rule_id,
            status=DedupBatchStatus.QUEUED.value,
            created_by_id=user_id,
        )
        self.session.add(batch)
        self.session.flush()
        return batch

    def execute_batch(
        self,
        batch_id: str,
        *,
        authorization: str = None,
    ) -> Dict[str, Any]:
        """
        执行批量去重任务

        Note: 此方法应该在 Worker 中异步执行
        """
        batch = self.session.get(DedupBatch, batch_id)
        if not batch:
            raise ValueError(f"Batch not found: {batch_id}")

        batch.status = DedupBatchStatus.RUNNING.value
        batch.started_at = datetime.utcnow()
        self.session.flush()

        try:
            # 获取待处理文件列表
            files = self._get_batch_files(batch)
            batch.total_files = len(files)
            self.session.flush()

            found_count = 0

            for i, file_container in enumerate(files):
                try:
                    result = self.check_similarity(
                        file_container.id,
                        rule_id=batch.rule_id,
                        index_after_check=True,
                        authorization=authorization,
                    )
                    found_count += result.get("records_created", 0)
                except Exception as e:
                    logger.warning(f"Failed to check file {file_container.id}: {e}")

                batch.processed_files = i + 1
                batch.found_similarities = found_count
                self.session.flush()

            batch.status = DedupBatchStatus.COMPLETED.value
            batch.completed_at = datetime.utcnow()
            batch.summary = {
                "total_files": batch.total_files,
                "processed_files": batch.processed_files,
                "found_similarities": found_count,
            }

        except Exception as e:
            batch.status = DedupBatchStatus.FAILED.value
            batch.error_message = str(e)
            batch.completed_at = datetime.utcnow()

        self.session.flush()
        return batch.summary or {}

    # ==================== 相似性审核 ====================

    def review_similarity(
        self,
        record_id: str,
        status: str,
        *,
        comment: str = None,
        create_relationship: bool = False,
        user_id: int = None,
    ) -> SimilarityRecord:
        """
        审核相似性记录

        Args:
            record_id: 记录 ID
            status: 新状态 (confirmed, rejected, ignored)
            comment: 审核意见
            create_relationship: 是否创建关系（仅 confirmed 时有效）
            user_id: 审核人
        """
        record = self.session.get(SimilarityRecord, record_id)
        if not record:
            raise ValueError(f"Record not found: {record_id}")

        record.status = status
        record.review_comment = comment
        record.reviewed_by_id = user_id
        record.reviewed_at = datetime.utcnow()

        if status == SimilarityStatus.CONFIRMED.value and create_relationship:
            if not record.relationship_item_id:
                rel_id = self._create_similarity_relationship(
                    record.source_file_id,
                    record.target_file_id,
                    record.similarity_score,
                    user_id
                )
                record.relationship_item_id = rel_id

        self.session.flush()
        return record

    def get_pending_reviews(
        self,
        *,
        item_type_id: str = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[SimilarityRecord]:
        """获取待审核的相似性记录"""
        query = self.session.query(SimilarityRecord).filter(
            SimilarityRecord.status == SimilarityStatus.PENDING.value
        )

        if item_type_id:
            # 通过文件关联的 Item 过滤
            query = query.join(
                FileContainer,
                SimilarityRecord.source_file_id == FileContainer.id
            )
            # 这里需要更复杂的 join，简化处理

        return query.order_by(
            desc(SimilarityRecord.similarity_score),
            desc(SimilarityRecord.created_at)
        ).offset(offset).limit(limit).all()

    # ==================== 报表 ====================

    def generate_dedup_report(
        self,
        *,
        start_date: datetime = None,
        end_date: datetime = None,
        status: str = None,
        format: str = "json",
    ) -> Dict[str, Any]:
        """
        生成去重报告

        Returns:
            {
                "summary": {...},
                "by_status": {...},
                "top_duplicates": [...],
                "recent_batches": [...]
            }
        """
        query = self.session.query(SimilarityRecord)

        if start_date:
            query = query.filter(SimilarityRecord.created_at >= start_date)
        if end_date:
            query = query.filter(SimilarityRecord.created_at <= end_date)
        if status:
            query = query.filter(SimilarityRecord.status == status)

        total = query.count()

        # 按状态统计
        by_status = {}
        for s in SimilarityStatus:
            count = query.filter(SimilarityRecord.status == s.value).count()
            by_status[s.value] = count

        # 高相似度 TOP 10
        top_duplicates = query.filter(
            SimilarityRecord.status == SimilarityStatus.PENDING.value
        ).order_by(
            desc(SimilarityRecord.similarity_score)
        ).limit(10).all()

        # 最近批次
        recent_batches = self.session.query(DedupBatch).order_by(
            desc(DedupBatch.created_at)
        ).limit(5).all()

        return {
            "summary": {
                "total_records": total,
                "pending_review": by_status.get(SimilarityStatus.PENDING.value, 0),
                "confirmed_duplicates": by_status.get(SimilarityStatus.CONFIRMED.value, 0),
            },
            "by_status": by_status,
            "top_duplicates": [
                {
                    "id": r.id,
                    "source_file_id": r.source_file_id,
                    "target_file_id": r.target_file_id,
                    "score": r.similarity_score,
                }
                for r in top_duplicates
            ],
            "recent_batches": [
                {
                    "id": b.id,
                    "name": b.name,
                    "status": b.status,
                    "found_similarities": b.found_similarities,
                }
                for b in recent_batches
            ],
        }

    # ==================== 私有方法 ====================

    def _get_local_path(self, file_container: FileContainer) -> Optional[str]:
        """获取文件的本地路径（S3 时下载到临时目录）"""
        import os
        import tempfile
        from yuantus.config import get_settings

        settings = get_settings()

        if settings.STORAGE_TYPE == "local":
            return os.path.join(
                settings.LOCAL_STORAGE_PATH,
                file_container.system_path
            )

        # S3: 下载到临时文件
        suffix = f".{file_container.get_extension()}" if file_container.get_extension() else ""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        try:
            self.file_service.download_file(file_container.system_path, temp_file)
            temp_file.close()
            return temp_file.name
        except Exception:
            temp_file.close()
            os.unlink(temp_file.name)
            return None

    def _cleanup_temp_file(self, path: str, file_container: FileContainer) -> None:
        """清理临时文件"""
        import os
        from yuantus.config import get_settings

        settings = get_settings()
        if settings.STORAGE_TYPE != "local":
            if path and os.path.exists(path):
                os.unlink(path)

    def _get_batch_files(self, batch: DedupBatch) -> List[FileContainer]:
        """根据批次配置获取文件列表"""
        query = self.session.query(FileContainer)

        if batch.scope_type == "file_list":
            file_ids = batch.scope_config.get("file_ids", [])
            query = query.filter(FileContainer.id.in_(file_ids))
        elif batch.scope_type == "document_type":
            doc_type = batch.scope_config.get("document_type")
            if doc_type:
                query = query.filter(FileContainer.document_type == doc_type)
        # 可扩展更多范围类型

        return query.all()

    def _create_similarity_relationship(
        self,
        source_file_id: str,
        target_file_id: str,
        score: float,
        user_id: int = None,
    ) -> str:
        """创建相似图纸关系"""
        rel_id = str(uuid.uuid4())

        rel = Item(
            id=rel_id,
            item_type_id="Similar Drawing",  # 需要预先创建此 ItemType
            config_id=str(uuid.uuid4()),
            generation=1,
            is_current=True,
            state="Active",
            source_id=source_file_id,
            related_id=target_file_id,
            properties={
                "similarity_score": score,
                "detection_date": datetime.utcnow().isoformat(),
            },
            created_by_id=user_id,
        )
        self.session.add(rel)
        return rel_id
```

### 2.4 API 路由

#### `src/yuantus/meta_engine/dedup/router.py`

```python
"""
图纸去重 API 路由
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.database import get_db
from yuantus.meta_engine.dedup.service import DedupService
from yuantus.meta_engine.dedup.models import SimilarityStatus
from yuantus.api.dependencies.auth import get_current_user_optional

router = APIRouter(prefix="/dedup", tags=["dedup"])


# ==================== 请求/响应模型 ====================

class CreateRuleRequest(BaseModel):
    name: str
    description: Optional[str] = None
    item_type_id: Optional[str] = None
    document_type: Optional[str] = None
    phash_threshold: int = 10
    feature_threshold: float = 0.85
    combined_threshold: float = 0.80
    detection_mode: str = "balanced"
    auto_create_relationship: bool = False
    auto_trigger_workflow: bool = False
    workflow_map_id: Optional[str] = None
    exclude_patterns: Optional[List[str]] = None
    priority: int = 100


class CheckSimilarityRequest(BaseModel):
    file_id: str
    rule_id: Optional[str] = None
    max_results: int = Field(default=5, le=20)
    index_after_check: bool = False


class CreateBatchRequest(BaseModel):
    name: str
    scope_type: str = "all"
    scope_config: Optional[dict] = None
    rule_id: Optional[str] = None


class ReviewRequest(BaseModel):
    status: str  # confirmed, rejected, ignored
    comment: Optional[str] = None
    create_relationship: bool = False


class SimilarityRecordResponse(BaseModel):
    id: str
    source_file_id: str
    target_file_id: str
    similarity_score: float
    similarity_type: str
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 规则管理 ====================

@router.post("/rules")
def create_rule(
    request: CreateRuleRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    """创建去重规则"""
    service = DedupService(db)
    user_id = current_user.id if current_user else None
    rule = service.create_rule(
        **request.model_dump(),
        user_id=user_id,
    )
    return {"ok": True, "rule_id": rule.id}


@router.get("/rules")
def list_rules(
    db: Session = Depends(get_db),
    is_active: Optional[bool] = None,
):
    """获取去重规则列表"""
    from yuantus.meta_engine.dedup.models import DedupRule

    query = db.query(DedupRule)
    if is_active is not None:
        query = query.filter(DedupRule.is_active == is_active)

    rules = query.order_by(DedupRule.priority).all()
    return {
        "rules": [
            {
                "id": r.id,
                "name": r.name,
                "item_type_id": r.item_type_id,
                "document_type": r.document_type,
                "phash_threshold": r.phash_threshold,
                "feature_threshold": r.feature_threshold,
                "priority": r.priority,
                "is_active": r.is_active,
            }
            for r in rules
        ]
    }


# ==================== 单文件检测 ====================

@router.post("/check")
def check_similarity(
    request: CheckSimilarityRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    """检测单个文件的相似性"""
    service = DedupService(db)
    user_id = current_user.id if current_user else None

    try:
        result = service.check_similarity(
            request.file_id,
            rule_id=request.rule_id,
            max_results=request.max_results,
            index_after_check=request.index_after_check,
            user_id=user_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== 批量处理 ====================

@router.post("/batches")
def create_batch(
    request: CreateBatchRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    """创建批量去重任务"""
    service = DedupService(db)
    user_id = current_user.id if current_user else None

    batch = service.create_batch(
        request.name,
        scope_type=request.scope_type,
        scope_config=request.scope_config,
        rule_id=request.rule_id,
        user_id=user_id,
    )
    return {"ok": True, "batch_id": batch.id}


@router.get("/batches")
def list_batches(
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    limit: int = Query(default=20, le=100),
):
    """获取批量任务列表"""
    from yuantus.meta_engine.dedup.models import DedupBatch
    from sqlalchemy import desc

    query = db.query(DedupBatch)
    if status:
        query = query.filter(DedupBatch.status == status)

    batches = query.order_by(desc(DedupBatch.created_at)).limit(limit).all()
    return {
        "batches": [
            {
                "id": b.id,
                "name": b.name,
                "status": b.status,
                "total_files": b.total_files,
                "processed_files": b.processed_files,
                "found_similarities": b.found_similarities,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in batches
        ]
    }


@router.post("/batches/{batch_id}/execute")
def execute_batch(
    batch_id: str,
    db: Session = Depends(get_db),
):
    """
    执行批量去重任务
    Note: 生产环境应该通过 Job Queue 异步执行
    """
    service = DedupService(db)
    try:
        result = service.execute_batch(batch_id)
        return {"ok": True, "summary": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== 审核管理 ====================

@router.get("/pending")
def get_pending_reviews(
    db: Session = Depends(get_db),
    item_type_id: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
):
    """获取待审核的相似性记录"""
    service = DedupService(db)
    records = service.get_pending_reviews(
        item_type_id=item_type_id,
        limit=limit,
        offset=offset,
    )
    return {
        "records": [
            SimilarityRecordResponse.model_validate(r).model_dump()
            for r in records
        ]
    }


@router.post("/records/{record_id}/review")
def review_record(
    record_id: str,
    request: ReviewRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    """审核相似性记录"""
    service = DedupService(db)
    user_id = current_user.id if current_user else None

    if request.status not in ["confirmed", "rejected", "ignored"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    try:
        record = service.review_similarity(
            record_id,
            request.status,
            comment=request.comment,
            create_relationship=request.create_relationship,
            user_id=user_id,
        )
        return {"ok": True, "record_id": record.id, "status": record.status}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== 报表 ====================

@router.get("/report")
def get_dedup_report(
    db: Session = Depends(get_db),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[str] = None,
):
    """获取去重报告"""
    service = DedupService(db)
    report = service.generate_dedup_report(
        start_date=start_date,
        end_date=end_date,
        status=status,
    )
    return report
```

### 2.5 异步任务

#### `src/yuantus/meta_engine/dedup/tasks.py`

```python
"""
图纸去重异步任务
集成到现有 Job Worker
"""
from typing import Dict, Any
from sqlalchemy.orm import Session

from yuantus.meta_engine.dedup.service import DedupService
from yuantus.meta_engine.services.job_errors import JobFatalError


def dedup_batch_execute(payload: Dict[str, Any], session: Session) -> Dict[str, Any]:
    """
    执行批量去重任务

    Job payload:
    {
        "batch_id": str,
        "authorization": str (optional)
    }
    """
    batch_id = payload.get("batch_id")
    if not batch_id:
        raise JobFatalError("Missing batch_id")

    authorization = payload.get("authorization")

    service = DedupService(session)

    try:
        result = service.execute_batch(
            batch_id,
            authorization=authorization,
        )
        return {
            "ok": True,
            "batch_id": batch_id,
            "summary": result,
        }
    except ValueError as e:
        raise JobFatalError(str(e))


def dedup_single_check(payload: Dict[str, Any], session: Session) -> Dict[str, Any]:
    """
    单文件去重检测任务

    Job payload:
    {
        "file_id": str,
        "rule_id": str (optional),
        "index_after_check": bool,
        "authorization": str (optional)
    }
    """
    file_id = payload.get("file_id")
    if not file_id:
        raise JobFatalError("Missing file_id")

    service = DedupService(session)

    try:
        result = service.check_similarity(
            file_id,
            rule_id=payload.get("rule_id"),
            max_results=payload.get("max_results", 5),
            index_after_check=payload.get("index_after_check", False),
            user_id=payload.get("user_id"),
            authorization=payload.get("authorization"),
        )
        return result
    except ValueError as e:
        raise JobFatalError(str(e))
```

### 2.6 数据库迁移

#### `migrations/versions/p1_add_dedup_tables.py`

```python
"""Add dedup tables

Revision ID: p1_dedup_001
Revises: q1b2c3d4e6a5_add_cad_dedup_path
Create Date: 2026-01-31
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'p1_dedup_001'
down_revision = 'q1b2c3d4e6a5_add_cad_dedup_path'
branch_labels = None
depends_on = None


def upgrade():
    # DedupRule 表
    op.create_table(
        'meta_dedup_rules',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('item_type_id', sa.String(), sa.ForeignKey('meta_item_types.id'), nullable=True),
        sa.Column('document_type', sa.String(), nullable=True),
        sa.Column('phash_threshold', sa.Integer(), default=10),
        sa.Column('feature_threshold', sa.Float(), default=0.85),
        sa.Column('combined_threshold', sa.Float(), default=0.80),
        sa.Column('detection_mode', sa.String(), default='balanced'),
        sa.Column('auto_create_relationship', sa.Boolean(), default=False),
        sa.Column('auto_trigger_workflow', sa.Boolean(), default=False),
        sa.Column('workflow_map_id', sa.String(), nullable=True),
        sa.Column('exclude_patterns', postgresql.JSONB(), nullable=True),
        sa.Column('priority', sa.Integer(), default=100),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('rbac_users.id'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    # DedupBatch 表
    op.create_table(
        'meta_dedup_batches',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('scope_type', sa.String(), default='all'),
        sa.Column('scope_config', postgresql.JSONB(), nullable=True),
        sa.Column('rule_id', sa.String(), sa.ForeignKey('meta_dedup_rules.id'), nullable=True),
        sa.Column('status', sa.String(), default='queued', index=True),
        sa.Column('total_files', sa.Integer(), default=0),
        sa.Column('processed_files', sa.Integer(), default=0),
        sa.Column('found_similarities', sa.Integer(), default=0),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('summary', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('rbac_users.id'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # SimilarityRecord 表
    op.create_table(
        'meta_similarity_records',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('source_file_id', sa.String(), sa.ForeignKey('meta_files.id'), nullable=False, index=True),
        sa.Column('target_file_id', sa.String(), sa.ForeignKey('meta_files.id'), nullable=False, index=True),
        sa.Column('similarity_score', sa.Float(), nullable=False),
        sa.Column('similarity_type', sa.String(), default='visual'),
        sa.Column('detection_method', sa.String(), nullable=True),
        sa.Column('detection_params', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(), default='pending', index=True),
        sa.Column('reviewed_by_id', sa.Integer(), sa.ForeignKey('rbac_users.id'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_comment', sa.Text(), nullable=True),
        sa.Column('relationship_item_id', sa.String(), sa.ForeignKey('meta_items.id'), nullable=True),
        sa.Column('batch_id', sa.String(), sa.ForeignKey('meta_dedup_batches.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    # 创建索引
    op.create_index(
        'ix_similarity_source_target',
        'meta_similarity_records',
        ['source_file_id', 'target_file_id'],
    )


def downgrade():
    op.drop_table('meta_similarity_records')
    op.drop_table('meta_dedup_batches')
    op.drop_table('meta_dedup_rules')
```

---

## 3. Phase 2: 配置管理 (Variant BOM)

### 3.1 目标

实现产品配置管理，支持 150% BOM、选配项、变型规则。

### 3.2 数据模型

#### `src/yuantus/meta_engine/configuration/models.py`

```python
"""
配置管理数据模型
支持 Option Sets, Option Items, Variant Rules
"""
from sqlalchemy import (
    Column, String, Integer, ForeignKey, DateTime,
    Boolean, Text, JSON, Float
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from yuantus.models.base import Base


class OptionValueType(str, enum.Enum):
    """选项值类型"""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ITEM_REF = "item_ref"  # 引用其他 Item


class OptionSet(Base):
    """
    选项集定义
    例如：颜色、材料、电压等级
    """
    __tablename__ = "meta_option_sets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    label = Column(String)
    description = Column(Text)

    # 值类型
    value_type = Column(String, default=OptionValueType.STRING.value)

    # 是否允许多选
    allow_multiple = Column(Boolean, default=False)

    # 是否必选
    is_required = Column(Boolean, default=False)

    # 默认值
    default_value = Column(String, nullable=True)

    # 排序
    sequence = Column(Integer, default=0)

    # 适用的 ItemType（为空表示全局）
    item_type_id = Column(String, ForeignKey("meta_item_types.id"), nullable=True)

    # 状态
    is_active = Column(Boolean, default=True)

    # 审计
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)

    # Relationships
    options = relationship("OptionItem", back_populates="option_set", cascade="all, delete-orphan")


class OptionItem(Base):
    """
    选项值定义
    例如：红色、蓝色（属于"颜色"选项集）
    """
    __tablename__ = "meta_option_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    option_set_id = Column(String, ForeignKey("meta_option_sets.id"), nullable=False, index=True)

    # 值
    value = Column(String, nullable=False)  # 存储的值
    label = Column(String)  # 显示标签
    description = Column(Text)

    # 对于 item_ref 类型，关联的 Item ID
    ref_item_id = Column(String, ForeignKey("meta_items.id"), nullable=True)

    # 排序
    sequence = Column(Integer, default=0)

    # 附加属性（JSON）
    properties = Column(JSON().with_variant(JSONB, "postgresql"))

    # 状态
    is_active = Column(Boolean, default=True)

    # Relationships
    option_set = relationship("OptionSet", back_populates="options")


class VariantRule(Base):
    """
    变型规则
    定义当选择某些选项组合时，BOM 如何变化
    """
    __tablename__ = "meta_variant_rules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text)

    # 适用的父件
    parent_item_type_id = Column(String, ForeignKey("meta_item_types.id"), nullable=True)
    parent_item_id = Column(String, ForeignKey("meta_items.id"), nullable=True)

    # 条件表达式（JSON）
    # 格式: {"all": [{"option": "color", "value": "red"}, {"option": "voltage", "op": ">=", "value": 220}]}
    condition = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)

    # 动作类型
    action_type = Column(String, nullable=False)  # include, exclude, substitute, modify_qty

    # 动作目标
    target_item_id = Column(String, ForeignKey("meta_items.id"), nullable=True)
    target_relationship_id = Column(String, ForeignKey("meta_items.id"), nullable=True)

    # 动作参数
    action_params = Column(JSON().with_variant(JSONB, "postgresql"))
    # 例如: {"substitute_with": "item-123", "quantity_multiplier": 2.0}

    # 优先级
    priority = Column(Integer, default=100)

    # 状态
    is_active = Column(Boolean, default=True)

    # 审计
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)


class ProductConfiguration(Base):
    """
    产品配置实例
    记录一个具体产品的配置选择
    """
    __tablename__ = "meta_product_configurations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 关联的产品（通常是顶层 Part）
    product_item_id = Column(String, ForeignKey("meta_items.id"), nullable=False, index=True)

    # 配置名称（例如：标准版、高配版）
    name = Column(String, nullable=False)
    description = Column(Text)

    # 选项选择（JSON）
    # 格式: {"color": "red", "voltage": "220", "features": ["wifi", "bluetooth"]}
    selections = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)

    # 计算出的有效 BOM（缓存）
    effective_bom_cache = Column(JSON().with_variant(JSONB, "postgresql"))
    cache_updated_at = Column(DateTime(timezone=True))

    # 状态
    state = Column(String, default="draft")  # draft, released, obsolete

    # 版本
    version = Column(Integer, default=1)

    # 审计
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)
    released_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
```

### 3.3 服务层

#### `src/yuantus/meta_engine/configuration/service.py`

```python
"""
配置管理服务
"""
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
import uuid
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from yuantus.meta_engine.configuration.models import (
    OptionSet, OptionItem, VariantRule,
    ProductConfiguration, OptionValueType
)
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.bom_service import BOMService

logger = logging.getLogger(__name__)


class ConfigurationService:
    """配置管理服务"""

    def __init__(self, session: Session):
        self.session = session
        self.bom_service = BOMService(session)

    # ==================== Option Set 管理 ====================

    def create_option_set(
        self,
        name: str,
        *,
        label: str = None,
        description: str = None,
        value_type: str = "string",
        allow_multiple: bool = False,
        is_required: bool = False,
        default_value: str = None,
        item_type_id: str = None,
        user_id: int = None,
    ) -> OptionSet:
        """创建选项集"""
        option_set = OptionSet(
            id=str(uuid.uuid4()),
            name=name,
            label=label or name,
            description=description,
            value_type=value_type,
            allow_multiple=allow_multiple,
            is_required=is_required,
            default_value=default_value,
            item_type_id=item_type_id,
            created_by_id=user_id,
        )
        self.session.add(option_set)
        self.session.flush()
        return option_set

    def add_option_item(
        self,
        option_set_id: str,
        value: str,
        *,
        label: str = None,
        description: str = None,
        ref_item_id: str = None,
        sequence: int = 0,
        properties: Dict[str, Any] = None,
    ) -> OptionItem:
        """添加选项值"""
        option_item = OptionItem(
            id=str(uuid.uuid4()),
            option_set_id=option_set_id,
            value=value,
            label=label or value,
            description=description,
            ref_item_id=ref_item_id,
            sequence=sequence,
            properties=properties or {},
        )
        self.session.add(option_item)
        self.session.flush()
        return option_item

    def get_option_sets(
        self,
        item_type_id: str = None,
        include_global: bool = True,
    ) -> List[OptionSet]:
        """获取适用的选项集"""
        query = self.session.query(OptionSet).filter(
            OptionSet.is_active == True
        )

        conditions = []
        if item_type_id:
            conditions.append(OptionSet.item_type_id == item_type_id)
        if include_global:
            conditions.append(OptionSet.item_type_id.is_(None))

        if conditions:
            query = query.filter(or_(*conditions))

        return query.order_by(OptionSet.sequence, OptionSet.name).all()

    # ==================== Variant Rule 管理 ====================

    def create_variant_rule(
        self,
        name: str,
        condition: Dict[str, Any],
        action_type: str,
        *,
        description: str = None,
        parent_item_type_id: str = None,
        parent_item_id: str = None,
        target_item_id: str = None,
        target_relationship_id: str = None,
        action_params: Dict[str, Any] = None,
        priority: int = 100,
        user_id: int = None,
    ) -> VariantRule:
        """创建变型规则"""
        rule = VariantRule(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            parent_item_type_id=parent_item_type_id,
            parent_item_id=parent_item_id,
            condition=condition,
            action_type=action_type,
            target_item_id=target_item_id,
            target_relationship_id=target_relationship_id,
            action_params=action_params or {},
            priority=priority,
            created_by_id=user_id,
        )
        self.session.add(rule)
        self.session.flush()
        return rule

    def get_applicable_rules(
        self,
        parent_item_id: str = None,
        parent_item_type_id: str = None,
    ) -> List[VariantRule]:
        """获取适用的变型规则"""
        query = self.session.query(VariantRule).filter(
            VariantRule.is_active == True
        )

        conditions = []

        if parent_item_id:
            conditions.append(VariantRule.parent_item_id == parent_item_id)

        if parent_item_type_id:
            conditions.append(
                and_(
                    VariantRule.parent_item_id.is_(None),
                    VariantRule.parent_item_type_id == parent_item_type_id
                )
            )

        # 全局规则
        conditions.append(
            and_(
                VariantRule.parent_item_id.is_(None),
                VariantRule.parent_item_type_id.is_(None)
            )
        )

        query = query.filter(or_(*conditions))
        return query.order_by(VariantRule.priority).all()

    # ==================== 配置计算 ====================

    def evaluate_condition(
        self,
        condition: Dict[str, Any],
        selections: Dict[str, Any],
    ) -> bool:
        """
        评估条件表达式

        条件格式:
        - {"option": "color", "value": "red"}
        - {"option": "voltage", "op": ">=", "value": 220}
        - {"all": [...]}
        - {"any": [...]}
        - {"not": {...}}
        """
        if not condition:
            return True

        if "all" in condition:
            return all(
                self.evaluate_condition(c, selections)
                for c in condition["all"]
            )

        if "any" in condition:
            return any(
                self.evaluate_condition(c, selections)
                for c in condition["any"]
            )

        if "not" in condition:
            return not self.evaluate_condition(condition["not"], selections)

        # 简单条件
        option_key = condition.get("option")
        if not option_key:
            return False

        selected_value = selections.get(option_key)
        target_value = condition.get("value")
        op = condition.get("op", "eq")

        if selected_value is None:
            return condition.get("missing", False)

        # 多选情况
        if isinstance(selected_value, list):
            if op in ("eq", "=", "=="):
                return target_value in selected_value
            if op in ("ne", "!="):
                return target_value not in selected_value
            if op == "contains":
                return target_value in selected_value
            # 对于数值比较，取列表中的值
            selected_value = selected_value[0] if selected_value else None

        # 数值比较
        try:
            if op in (">", "gt"):
                return float(selected_value) > float(target_value)
            if op in (">=", "gte"):
                return float(selected_value) >= float(target_value)
            if op in ("<", "lt"):
                return float(selected_value) < float(target_value)
            if op in ("<=", "lte"):
                return float(selected_value) <= float(target_value)
        except (ValueError, TypeError):
            pass

        # 字符串比较
        if op in ("eq", "=", "=="):
            return str(selected_value) == str(target_value)
        if op in ("ne", "!="):
            return str(selected_value) != str(target_value)
        if op == "contains":
            return str(target_value) in str(selected_value)
        if op == "startswith":
            return str(selected_value).startswith(str(target_value))
        if op == "endswith":
            return str(selected_value).endswith(str(target_value))

        return False

    def get_effective_bom(
        self,
        product_item_id: str,
        selections: Dict[str, Any],
        *,
        levels: int = 10,
        effective_date: datetime = None,
    ) -> Dict[str, Any]:
        """
        根据配置选择计算有效 BOM

        Args:
            product_item_id: 产品 Item ID
            selections: 配置选择
            levels: BOM 展开层级
            effective_date: 有效日期

        Returns:
            过滤/修改后的 BOM 结构
        """
        # 获取 150% BOM（包含所有可选件）
        full_bom = self.bom_service.get_bom_structure(
            product_item_id,
            levels=levels,
            effective_date=effective_date,
            config_selection=None,  # 不在 BOM 层过滤
        )

        # 获取适用规则
        product = self.session.get(Item, product_item_id)
        rules = self.get_applicable_rules(
            parent_item_id=product_item_id,
            parent_item_type_id=product.item_type_id if product else None,
        )

        # 应用规则过滤和修改
        effective_bom = self._apply_rules_to_bom(
            full_bom, rules, selections
        )

        return effective_bom

    def _apply_rules_to_bom(
        self,
        bom: Dict[str, Any],
        rules: List[VariantRule],
        selections: Dict[str, Any],
    ) -> Dict[str, Any]:
        """递归应用规则到 BOM"""
        result = dict(bom)
        children = bom.get("children") or []
        filtered_children = []

        for child_entry in children:
            rel = child_entry.get("relationship") or {}
            child = child_entry.get("child") or {}
            rel_id = rel.get("id")
            child_id = child.get("id")

            # 检查是否应该排除
            should_exclude = False
            substitute_with = None
            qty_multiplier = 1.0

            for rule in rules:
                if not self.evaluate_condition(rule.condition, selections):
                    continue

                # 检查规则目标
                target_match = (
                    (rule.target_item_id and rule.target_item_id == child_id) or
                    (rule.target_relationship_id and rule.target_relationship_id == rel_id)
                )

                if not target_match and rule.target_item_id is None and rule.target_relationship_id is None:
                    # 全局规则，检查 BOM 行条件
                    rel_props = rel.get("properties") or {}
                    config_cond = rel_props.get("config_condition")
                    if config_cond:
                        target_match = self.bom_service._match_config_condition(
                            config_cond, selections
                        )

                if not target_match:
                    continue

                # 应用动作
                if rule.action_type == "exclude":
                    should_exclude = True
                    break
                elif rule.action_type == "include":
                    # include 规则：默认排除，匹配时包含
                    pass
                elif rule.action_type == "substitute":
                    params = rule.action_params or {}
                    substitute_with = params.get("substitute_with")
                elif rule.action_type == "modify_qty":
                    params = rule.action_params or {}
                    qty_multiplier = params.get("quantity_multiplier", 1.0)

            if should_exclude:
                continue

            # 处理替代
            if substitute_with:
                sub_item = self.session.get(Item, substitute_with)
                if sub_item:
                    child = sub_item.to_dict()
                    child_entry = dict(child_entry)
                    child_entry["child"] = child
                    child_entry["substituted_from"] = child_id

            # 处理数量修改
            if qty_multiplier != 1.0:
                rel = dict(rel)
                props = dict(rel.get("properties") or {})
                qty = props.get("quantity", 1)
                props["quantity"] = qty * qty_multiplier
                props["original_quantity"] = qty
                rel["properties"] = props
                child_entry = dict(child_entry)
                child_entry["relationship"] = rel

            # 递归处理子级
            if child.get("children"):
                child_entry = dict(child_entry)
                child_entry["child"] = self._apply_rules_to_bom(
                    child, rules, selections
                )

            filtered_children.append(child_entry)

        result["children"] = filtered_children
        return result

    # ==================== 配置实例管理 ====================

    def create_configuration(
        self,
        product_item_id: str,
        name: str,
        selections: Dict[str, Any],
        *,
        description: str = None,
        user_id: int = None,
    ) -> ProductConfiguration:
        """创建产品配置实例"""
        # 验证选择
        self.validate_selections(product_item_id, selections)

        config = ProductConfiguration(
            id=str(uuid.uuid4()),
            product_item_id=product_item_id,
            name=name,
            description=description,
            selections=selections,
            created_by_id=user_id,
        )
        self.session.add(config)
        self.session.flush()

        # 计算有效 BOM 并缓存
        self._update_effective_bom_cache(config)

        return config

    def validate_selections(
        self,
        product_item_id: str,
        selections: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        验证配置选择的有效性

        Returns:
            (is_valid, error_messages)
        """
        errors = []
        product = self.session.get(Item, product_item_id)
        if not product:
            return False, ["Product not found"]

        # 获取适用的选项集
        option_sets = self.get_option_sets(
            item_type_id=product.item_type_id,
            include_global=True,
        )

        for os in option_sets:
            value = selections.get(os.name)

            # 必填检查
            if os.is_required and value is None:
                errors.append(f"Option '{os.name}' is required")
                continue

            if value is None:
                continue

            # 获取有效选项值
            valid_values = {oi.value for oi in os.options if oi.is_active}

            # 多选处理
            if isinstance(value, list):
                if not os.allow_multiple and len(value) > 1:
                    errors.append(f"Option '{os.name}' does not allow multiple selections")
                for v in value:
                    if v not in valid_values:
                        errors.append(f"Invalid value '{v}' for option '{os.name}'")
            else:
                if value not in valid_values:
                    errors.append(f"Invalid value '{value}' for option '{os.name}'")

        return len(errors) == 0, errors

    def _update_effective_bom_cache(self, config: ProductConfiguration) -> None:
        """更新配置的有效 BOM 缓存"""
        effective_bom = self.get_effective_bom(
            config.product_item_id,
            config.selections,
        )
        config.effective_bom_cache = effective_bom
        config.cache_updated_at = datetime.utcnow()
        self.session.add(config)

    # ==================== 配置比较 ====================

    def compare_configurations(
        self,
        config_id_a: str,
        config_id_b: str,
    ) -> Dict[str, Any]:
        """
        比较两个配置的差异
        """
        config_a = self.session.get(ProductConfiguration, config_id_a)
        config_b = self.session.get(ProductConfiguration, config_id_b)

        if not config_a or not config_b:
            raise ValueError("Configuration not found")

        # 选项差异
        selection_diffs = []
        all_keys = set(config_a.selections.keys()) | set(config_b.selections.keys())
        for key in sorted(all_keys):
            val_a = config_a.selections.get(key)
            val_b = config_b.selections.get(key)
            if val_a != val_b:
                selection_diffs.append({
                    "option": key,
                    "config_a": val_a,
                    "config_b": val_b,
                })

        # BOM 差异
        bom_a = config_a.effective_bom_cache or self.get_effective_bom(
            config_a.product_item_id, config_a.selections
        )
        bom_b = config_b.effective_bom_cache or self.get_effective_bom(
            config_b.product_item_id, config_b.selections
        )

        bom_diff = self.bom_service.compare_bom_trees(bom_a, bom_b)

        return {
            "config_a": {
                "id": config_a.id,
                "name": config_a.name,
            },
            "config_b": {
                "id": config_b.id,
                "name": config_b.name,
            },
            "selection_differences": selection_diffs,
            "bom_differences": bom_diff,
        }
```

---

## 4. Phase 3: MBOM 与工艺路线

### 4.1 目标

实现制造 BOM (MBOM) 与工艺路线管理，支持 EBOM → MBOM 转换、工艺定义、工时计算。

### 4.2 数据模型

#### `src/yuantus/meta_engine/manufacturing/models.py`

```python
"""
制造管理数据模型
MBOM、工艺路线、工序定义
"""
from sqlalchemy import (
    Column, String, Integer, ForeignKey, DateTime,
    Boolean, Text, JSON, Float, Numeric
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from yuantus.models.base import Base


class BOMType(str, enum.Enum):
    """BOM 类型"""
    EBOM = "ebom"      # 工程 BOM
    MBOM = "mbom"      # 制造 BOM
    SBOM = "sbom"      # 服务 BOM


class OperationType(str, enum.Enum):
    """工序类型"""
    FABRICATION = "fabrication"      # 加工
    ASSEMBLY = "assembly"            # 装配
    INSPECTION = "inspection"        # 检验
    TREATMENT = "treatment"          # 处理（热处理等）
    PACKAGING = "packaging"          # 包装


class ManufacturingBOM(Base):
    """
    制造 BOM
    与 EBOM 分离，支持独立的制造结构
    """
    __tablename__ = "meta_manufacturing_boms"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 源 EBOM Item
    source_item_id = Column(String, ForeignKey("meta_items.id"), nullable=False, index=True)

    # MBOM 名称和版本
    name = Column(String, nullable=False)
    version = Column(String, default="1.0")
    revision = Column(Integer, default=1)

    # BOM 类型
    bom_type = Column(String, default=BOMType.MBOM.value)

    # 关联的工厂/产线（可选）
    plant_code = Column(String, nullable=True)
    line_code = Column(String, nullable=True)

    # 有效期
    effective_from = Column(DateTime(timezone=True), nullable=True)
    effective_to = Column(DateTime(timezone=True), nullable=True)

    # 状态
    state = Column(String, default="draft")  # draft, released, obsolete

    # 结构数据（JSON格式的完整BOM树）
    structure = Column(JSON().with_variant(JSONB, "postgresql"))

    # 审计
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)
    released_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)

    # Relationships
    routings = relationship("Routing", back_populates="mbom")


class MBOMLine(Base):
    """
    MBOM 行项目
    单独存储以便查询和管理
    """
    __tablename__ = "meta_mbom_lines"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    mbom_id = Column(String, ForeignKey("meta_manufacturing_boms.id"), nullable=False, index=True)

    # 父行 ID（用于层级结构）
    parent_line_id = Column(String, ForeignKey("meta_mbom_lines.id"), nullable=True)

    # 关联的 Item
    item_id = Column(String, ForeignKey("meta_items.id"), nullable=False, index=True)

    # 序号和层级
    sequence = Column(Integer, default=10)
    level = Column(Integer, default=0)

    # 数量和单位
    quantity = Column(Numeric(20, 6), default=1)
    unit = Column(String, default="EA")

    # 与 EBOM 的对应关系
    ebom_relationship_id = Column(String, ForeignKey("meta_items.id"), nullable=True)

    # 制造相关属性
    make_buy = Column(String, default="make")  # make, buy, phantom
    supply_type = Column(String, nullable=True)  # stock, direct, consignment

    # 操作点（在哪个工序使用）
    operation_id = Column(String, ForeignKey("meta_operations.id"), nullable=True)

    # 消耗时机
    backflush = Column(Boolean, default=False)  # 倒冲

    # 物料特性
    scrap_rate = Column(Float, default=0.0)  # 报废率
    fixed_quantity = Column(Boolean, default=False)  # 固定数量（不随产品数量变化）

    # 备注
    notes = Column(Text, nullable=True)

    # 附加属性
    properties = Column(JSON().with_variant(JSONB, "postgresql"))


class Routing(Base):
    """
    工艺路线
    定义生产一个产品需要经过的工序序列
    """
    __tablename__ = "meta_routings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 关联的 MBOM
    mbom_id = Column(String, ForeignKey("meta_manufacturing_boms.id"), nullable=True, index=True)

    # 或直接关联 Item（当不需要 MBOM 时）
    item_id = Column(String, ForeignKey("meta_items.id"), nullable=True, index=True)

    # 工艺路线标识
    name = Column(String, nullable=False)
    routing_code = Column(String, unique=True)
    version = Column(String, default="1.0")

    # 描述
    description = Column(Text, nullable=True)

    # 有效期
    effective_from = Column(DateTime(timezone=True), nullable=True)
    effective_to = Column(DateTime(timezone=True), nullable=True)

    # 主/备路线标识
    is_primary = Column(Boolean, default=True)

    # 工厂和产线
    plant_code = Column(String, nullable=True)
    line_code = Column(String, nullable=True)

    # 状态
    state = Column(String, default="draft")

    # 汇总数据（缓存）
    total_setup_time = Column(Float, default=0.0)  # 总准备时间
    total_run_time = Column(Float, default=0.0)    # 总运行时间
    total_labor_time = Column(Float, default=0.0)  # 总人工时间

    # 审计
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)

    # Relationships
    mbom = relationship("ManufacturingBOM", back_populates="routings")
    operations = relationship("Operation", back_populates="routing", order_by="Operation.sequence")


class Operation(Base):
    """
    工序定义
    工艺路线中的单个作业步骤
    """
    __tablename__ = "meta_operations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    routing_id = Column(String, ForeignKey("meta_routings.id"), nullable=False, index=True)

    # 工序编号和名称
    operation_number = Column(String, nullable=False)  # 如 10, 20, 30
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # 工序类型
    operation_type = Column(String, default=OperationType.FABRICATION.value)

    # 顺序
    sequence = Column(Integer, default=10)

    # 工作中心
    workcenter_id = Column(String, nullable=True)
    workcenter_code = Column(String, nullable=True)

    # 时间数据（分钟）
    setup_time = Column(Float, default=0.0)      # 准备时间
    run_time = Column(Float, default=0.0)        # 单件运行时间
    queue_time = Column(Float, default=0.0)      # 排队时间
    move_time = Column(Float, default=0.0)       # 转移时间
    wait_time = Column(Float, default=0.0)       # 等待时间

    # 人工时间
    labor_setup_time = Column(Float, default=0.0)
    labor_run_time = Column(Float, default=0.0)

    # 人员需求
    crew_size = Column(Integer, default=1)

    # 设备需求
    machines_required = Column(Integer, default=1)

    # 生产批量相关
    overlap_quantity = Column(Integer, nullable=True)  # 重叠数量
    transfer_batch = Column(Integer, nullable=True)    # 转移批量

    # 外协标识
    is_subcontracted = Column(Boolean, default=False)
    subcontractor_id = Column(String, nullable=True)

    # 检验要求
    inspection_required = Column(Boolean, default=False)
    inspection_plan_id = Column(String, nullable=True)

    # 工具/模具需求
    tooling_requirements = Column(JSON().with_variant(JSONB, "postgresql"))

    # 工艺文档
    work_instructions = Column(Text, nullable=True)
    document_ids = Column(JSON().with_variant(JSONB, "postgresql"))  # 关联的文档ID列表

    # 成本因素
    labor_cost_rate = Column(Float, nullable=True)
    overhead_rate = Column(Float, nullable=True)

    # 附加属性
    properties = Column(JSON().with_variant(JSONB, "postgresql"))

    # Relationships
    routing = relationship("Routing", back_populates="operations")


class WorkCenter(Base):
    """
    工作中心
    生产资源的逻辑分组
    """
    __tablename__ = "meta_workcenters"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 编码和名称
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # 所属工厂/产线
    plant_code = Column(String, nullable=True)
    department_code = Column(String, nullable=True)

    # 产能数据
    capacity_per_day = Column(Float, default=8.0)  # 每日产能（小时）
    efficiency = Column(Float, default=1.0)         # 效率系数
    utilization = Column(Float, default=0.9)        # 利用率

    # 资源数量
    machine_count = Column(Integer, default=1)
    worker_count = Column(Integer, default=1)

    # 成本中心
    cost_center = Column(String, nullable=True)
    labor_rate = Column(Float, nullable=True)
    overhead_rate = Column(Float, nullable=True)

    # 排程相关
    scheduling_type = Column(String, default="finite")  # finite, infinite
    queue_time_default = Column(Float, default=0.0)

    # 状态
    is_active = Column(Boolean, default=True)

    # 审计
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 4.3 服务层

#### `src/yuantus/meta_engine/manufacturing/mbom_service.py`

```python
"""
MBOM 服务
EBOM → MBOM 转换、制造结构管理
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_

from yuantus.meta_engine.manufacturing.models import (
    ManufacturingBOM, MBOMLine, BOMType
)
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.bom_service import BOMService

logger = logging.getLogger(__name__)


class MBOMService:
    """MBOM 管理服务"""

    def __init__(self, session: Session):
        self.session = session
        self.bom_service = BOMService(session)

    def create_mbom_from_ebom(
        self,
        source_item_id: str,
        name: str,
        *,
        version: str = "1.0",
        plant_code: str = None,
        effective_from: datetime = None,
        user_id: int = None,
        transformation_rules: Dict[str, Any] = None,
    ) -> ManufacturingBOM:
        """
        从 EBOM 创建 MBOM

        Args:
            source_item_id: 源 EBOM 顶层 Item ID
            name: MBOM 名称
            transformation_rules: 转换规则，例如：
                {
                    "collapse_phantom": True,     # 折叠虚拟件
                    "apply_scrap_rates": True,    # 应用报废率
                    "substitute_items": {...},    # 替代件映射
                    "exclude_items": [...],       # 排除的 Item
                }
        """
        # 获取 EBOM 结构
        ebom_structure = self.bom_service.get_bom_structure(
            source_item_id,
            levels=20,
            effective_date=effective_from,
        )

        # 应用转换规则
        mbom_structure = self._transform_ebom_to_mbom(
            ebom_structure,
            transformation_rules or {},
        )

        # 创建 MBOM
        mbom = ManufacturingBOM(
            id=str(uuid.uuid4()),
            source_item_id=source_item_id,
            name=name,
            version=version,
            bom_type=BOMType.MBOM.value,
            plant_code=plant_code,
            effective_from=effective_from,
            structure=mbom_structure,
            created_by_id=user_id,
        )
        self.session.add(mbom)
        self.session.flush()

        # 创建行项目
        self._create_mbom_lines(mbom.id, mbom_structure)

        return mbom

    def _transform_ebom_to_mbom(
        self,
        ebom: Dict[str, Any],
        rules: Dict[str, Any],
        level: int = 0,
    ) -> Dict[str, Any]:
        """递归转换 EBOM 到 MBOM 结构"""
        result = {
            "item": ebom.get("item") or ebom,
            "level": level,
            "children": [],
        }

        exclude_items = set(rules.get("exclude_items", []))
        substitute_map = rules.get("substitute_items", {})
        collapse_phantom = rules.get("collapse_phantom", True)

        children = ebom.get("children") or []
        for child_entry in children:
            rel = child_entry.get("relationship") or {}
            child = child_entry.get("child") or {}
            child_id = child.get("id")
            child_props = child.get("properties") or {}

            # 排除检查
            if child_id in exclude_items:
                continue

            # 替代检查
            if child_id in substitute_map:
                sub_id = substitute_map[child_id]
                sub_item = self.session.get(Item, sub_id)
                if sub_item:
                    child = sub_item.to_dict()
                    child_id = sub_id

            # 虚拟件处理
            make_buy = child_props.get("make_buy", "make")
            if collapse_phantom and make_buy == "phantom":
                # 折叠虚拟件：将其子级提升到当前层级
                phantom_children = child.get("children") or []
                for pc in phantom_children:
                    transformed = self._transform_ebom_to_mbom(
                        pc.get("child", pc),
                        rules,
                        level + 1,
                    )
                    # 合并数量
                    rel_props = rel.get("properties") or {}
                    pc_rel = pc.get("relationship") or {}
                    pc_props = pc_rel.get("properties") or {}
                    parent_qty = float(rel_props.get("quantity", 1))
                    child_qty = float(pc_props.get("quantity", 1))
                    transformed["quantity"] = parent_qty * child_qty
                    result["children"].append(transformed)
                continue

            # 正常转换
            transformed = self._transform_ebom_to_mbom(
                child_entry,
                rules,
                level + 1,
            )

            # 设置数量和属性
            rel_props = rel.get("properties") or {}
            transformed["quantity"] = float(rel_props.get("quantity", 1))
            transformed["unit"] = rel_props.get("unit", "EA")
            transformed["make_buy"] = make_buy
            transformed["ebom_relationship_id"] = rel.get("id")

            # 应用报废率
            if rules.get("apply_scrap_rates"):
                scrap = float(child_props.get("scrap_rate", 0))
                if scrap > 0:
                    transformed["scrap_rate"] = scrap
                    # 调整数量以补偿报废
                    transformed["quantity"] = transformed["quantity"] / (1 - scrap)

            result["children"].append(transformed)

        return result

    def _create_mbom_lines(
        self,
        mbom_id: str,
        structure: Dict[str, Any],
        parent_line_id: str = None,
        sequence_base: int = 10,
    ) -> None:
        """递归创建 MBOM 行项目"""
        item = structure.get("item") or {}
        item_id = item.get("id")

        if not item_id:
            return

        # 创建行
        line = MBOMLine(
            id=str(uuid.uuid4()),
            mbom_id=mbom_id,
            parent_line_id=parent_line_id,
            item_id=item_id,
            sequence=sequence_base,
            level=structure.get("level", 0),
            quantity=structure.get("quantity", 1),
            unit=structure.get("unit", "EA"),
            ebom_relationship_id=structure.get("ebom_relationship_id"),
            make_buy=structure.get("make_buy", "make"),
            scrap_rate=structure.get("scrap_rate", 0),
        )
        self.session.add(line)
        self.session.flush()

        # 递归处理子级
        children = structure.get("children") or []
        for i, child in enumerate(children):
            self._create_mbom_lines(
                mbom_id,
                child,
                parent_line_id=line.id,
                sequence_base=(i + 1) * 10,
            )

    def get_mbom_structure(
        self,
        mbom_id: str,
        *,
        include_operations: bool = False,
    ) -> Dict[str, Any]:
        """获取 MBOM 结构"""
        mbom = self.session.get(ManufacturingBOM, mbom_id)
        if not mbom:
            raise ValueError(f"MBOM not found: {mbom_id}")

        # 使用缓存的结构
        if mbom.structure:
            result = dict(mbom.structure)
            if include_operations:
                result = self._attach_operations(result, mbom_id)
            return result

        # 从行项目重建
        lines = self.session.query(MBOMLine).filter(
            MBOMLine.mbom_id == mbom_id
        ).order_by(MBOMLine.level, MBOMLine.sequence).all()

        return self._build_structure_from_lines(lines, include_operations)

    def _attach_operations(
        self,
        structure: Dict[str, Any],
        mbom_id: str,
    ) -> Dict[str, Any]:
        """附加工序信息到 MBOM 结构"""
        from yuantus.meta_engine.manufacturing.models import Routing, Operation

        # 获取关联的工艺路线
        routings = self.session.query(Routing).filter(
            Routing.mbom_id == mbom_id,
            Routing.state == "released",
        ).all()

        if not routings:
            return structure

        primary_routing = next((r for r in routings if r.is_primary), routings[0])

        # 获取工序
        operations = self.session.query(Operation).filter(
            Operation.routing_id == primary_routing.id
        ).order_by(Operation.sequence).all()

        structure["routing"] = {
            "id": primary_routing.id,
            "name": primary_routing.name,
            "operations": [
                {
                    "id": op.id,
                    "number": op.operation_number,
                    "name": op.name,
                    "type": op.operation_type,
                    "workcenter": op.workcenter_code,
                    "setup_time": op.setup_time,
                    "run_time": op.run_time,
                }
                for op in operations
            ],
        }

        return structure

    def compare_ebom_mbom(
        self,
        ebom_item_id: str,
        mbom_id: str,
    ) -> Dict[str, Any]:
        """
        比较 EBOM 和 MBOM 的差异
        用于同步检查
        """
        ebom = self.bom_service.get_bom_structure(ebom_item_id, levels=20)
        mbom_structure = self.get_mbom_structure(mbom_id)

        differences = {
            "added_in_mbom": [],
            "removed_from_ebom": [],
            "quantity_changed": [],
            "structure_changed": [],
        }

        # 构建 Item 映射
        ebom_items = self._flatten_structure(ebom)
        mbom_items = self._flatten_structure(mbom_structure)

        ebom_ids = set(ebom_items.keys())
        mbom_ids = set(mbom_items.keys())

        # 新增项
        for item_id in mbom_ids - ebom_ids:
            differences["added_in_mbom"].append(mbom_items[item_id])

        # 删除项
        for item_id in ebom_ids - mbom_ids:
            differences["removed_from_ebom"].append(ebom_items[item_id])

        # 数量变化
        for item_id in ebom_ids & mbom_ids:
            ebom_qty = ebom_items[item_id].get("quantity", 1)
            mbom_qty = mbom_items[item_id].get("quantity", 1)
            if abs(ebom_qty - mbom_qty) > 0.0001:
                differences["quantity_changed"].append({
                    "item_id": item_id,
                    "ebom_quantity": ebom_qty,
                    "mbom_quantity": mbom_qty,
                })

        return differences

    def _flatten_structure(
        self,
        structure: Dict[str, Any],
        result: Dict[str, Dict] = None,
    ) -> Dict[str, Dict]:
        """展平 BOM 结构为字典"""
        if result is None:
            result = {}

        item = structure.get("item") or structure
        item_id = item.get("id")
        if item_id:
            result[item_id] = {
                "item": item,
                "quantity": structure.get("quantity", 1),
                "level": structure.get("level", 0),
            }

        for child in structure.get("children") or []:
            child_struct = child.get("child") or child
            self._flatten_structure(child_struct, result)

        return result
```

#### `src/yuantus/meta_engine/manufacturing/routing_service.py`

```python
"""
工艺路线服务
工序定义、工时计算、成本估算
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_

from yuantus.meta_engine.manufacturing.models import (
    Routing, Operation, WorkCenter, OperationType
)

logger = logging.getLogger(__name__)


class RoutingService:
    """工艺路线服务"""

    def __init__(self, session: Session):
        self.session = session

    def create_routing(
        self,
        name: str,
        *,
        mbom_id: str = None,
        item_id: str = None,
        routing_code: str = None,
        version: str = "1.0",
        is_primary: bool = True,
        plant_code: str = None,
        user_id: int = None,
    ) -> Routing:
        """创建工艺路线"""
        if not mbom_id and not item_id:
            raise ValueError("Either mbom_id or item_id must be provided")

        routing = Routing(
            id=str(uuid.uuid4()),
            mbom_id=mbom_id,
            item_id=item_id,
            name=name,
            routing_code=routing_code or f"RTG-{uuid.uuid4().hex[:8].upper()}",
            version=version,
            is_primary=is_primary,
            plant_code=plant_code,
            created_by_id=user_id,
        )
        self.session.add(routing)
        self.session.flush()
        return routing

    def add_operation(
        self,
        routing_id: str,
        operation_number: str,
        name: str,
        *,
        operation_type: str = "fabrication",
        workcenter_code: str = None,
        setup_time: float = 0.0,
        run_time: float = 0.0,
        labor_setup_time: float = None,
        labor_run_time: float = None,
        crew_size: int = 1,
        is_subcontracted: bool = False,
        inspection_required: bool = False,
        work_instructions: str = None,
        sequence: int = None,
    ) -> Operation:
        """添加工序"""
        routing = self.session.get(Routing, routing_id)
        if not routing:
            raise ValueError(f"Routing not found: {routing_id}")

        # 自动计算序号
        if sequence is None:
            existing = self.session.query(Operation).filter(
                Operation.routing_id == routing_id
            ).count()
            sequence = (existing + 1) * 10

        operation = Operation(
            id=str(uuid.uuid4()),
            routing_id=routing_id,
            operation_number=operation_number,
            name=name,
            operation_type=operation_type,
            sequence=sequence,
            workcenter_code=workcenter_code,
            setup_time=setup_time,
            run_time=run_time,
            labor_setup_time=labor_setup_time or setup_time,
            labor_run_time=labor_run_time or run_time,
            crew_size=crew_size,
            is_subcontracted=is_subcontracted,
            inspection_required=inspection_required,
            work_instructions=work_instructions,
        )
        self.session.add(operation)
        self.session.flush()

        # 更新路线汇总
        self._update_routing_totals(routing_id)

        return operation

    def _update_routing_totals(self, routing_id: str) -> None:
        """更新工艺路线的汇总时间"""
        routing = self.session.get(Routing, routing_id)
        if not routing:
            return

        operations = self.session.query(Operation).filter(
            Operation.routing_id == routing_id
        ).all()

        routing.total_setup_time = sum(op.setup_time or 0 for op in operations)
        routing.total_run_time = sum(op.run_time or 0 for op in operations)
        routing.total_labor_time = sum(
            (op.labor_setup_time or 0) + (op.labor_run_time or 0)
            for op in operations
        )
        self.session.add(routing)

    def calculate_production_time(
        self,
        routing_id: str,
        quantity: int,
        *,
        include_queue: bool = True,
        include_move: bool = True,
    ) -> Dict[str, Any]:
        """
        计算生产时间

        Args:
            routing_id: 工艺路线 ID
            quantity: 生产数量
            include_queue: 是否包含排队时间
            include_move: 是否包含移动时间

        Returns:
            {
                "total_time": float,          # 总时间（分钟）
                "setup_time": float,          # 准备时间
                "run_time": float,            # 运行时间
                "queue_time": float,          # 排队时间
                "move_time": float,           # 移动时间
                "labor_time": float,          # 人工时间
                "operations": [...]           # 各工序明细
            }
        """
        operations = self.session.query(Operation).filter(
            Operation.routing_id == routing_id
        ).order_by(Operation.sequence).all()

        result = {
            "total_time": 0.0,
            "setup_time": 0.0,
            "run_time": 0.0,
            "queue_time": 0.0,
            "move_time": 0.0,
            "labor_time": 0.0,
            "operations": [],
        }

        for op in operations:
            op_setup = op.setup_time or 0
            op_run = (op.run_time or 0) * quantity
            op_queue = (op.queue_time or 0) if include_queue else 0
            op_move = (op.move_time or 0) if include_move else 0
            op_labor = (op.labor_setup_time or 0) + (op.labor_run_time or 0) * quantity

            op_total = op_setup + op_run + op_queue + op_move

            result["operations"].append({
                "operation_id": op.id,
                "operation_number": op.operation_number,
                "name": op.name,
                "setup_time": op_setup,
                "run_time": op_run,
                "queue_time": op_queue,
                "move_time": op_move,
                "labor_time": op_labor,
                "total_time": op_total,
            })

            result["setup_time"] += op_setup
            result["run_time"] += op_run
            result["queue_time"] += op_queue
            result["move_time"] += op_move
            result["labor_time"] += op_labor
            result["total_time"] += op_total

        return result

    def calculate_cost_estimate(
        self,
        routing_id: str,
        quantity: int,
        *,
        labor_rate: float = None,
        overhead_rate: float = None,
    ) -> Dict[str, Any]:
        """
        估算生产成本
        """
        time_calc = self.calculate_production_time(routing_id, quantity)

        operations = self.session.query(Operation).filter(
            Operation.routing_id == routing_id
        ).all()

        labor_cost = 0.0
        overhead_cost = 0.0

        for op in operations:
            op_labor_rate = op.labor_cost_rate or labor_rate or 50.0
            op_overhead_rate = op.overhead_rate or overhead_rate or 30.0

            op_labor_time = (op.labor_setup_time or 0) + (op.labor_run_time or 0) * quantity
            op_labor_cost = op_labor_time / 60 * op_labor_rate  # 转换为小时

            op_run_time = (op.setup_time or 0) + (op.run_time or 0) * quantity
            op_overhead_cost = op_run_time / 60 * op_overhead_rate

            labor_cost += op_labor_cost
            overhead_cost += op_overhead_cost

        return {
            "quantity": quantity,
            "labor_cost": round(labor_cost, 2),
            "overhead_cost": round(overhead_cost, 2),
            "total_cost": round(labor_cost + overhead_cost, 2),
            "cost_per_unit": round((labor_cost + overhead_cost) / quantity, 2) if quantity else 0,
            "time_summary": {
                "total_minutes": time_calc["total_time"],
                "total_hours": round(time_calc["total_time"] / 60, 2),
            },
        }

    def copy_routing(
        self,
        source_routing_id: str,
        new_name: str,
        *,
        new_mbom_id: str = None,
        new_item_id: str = None,
        new_version: str = None,
        user_id: int = None,
    ) -> Routing:
        """复制工艺路线"""
        source = self.session.get(Routing, source_routing_id)
        if not source:
            raise ValueError(f"Source routing not found: {source_routing_id}")

        # 创建新路线
        new_routing = Routing(
            id=str(uuid.uuid4()),
            mbom_id=new_mbom_id or source.mbom_id,
            item_id=new_item_id or source.item_id,
            name=new_name,
            routing_code=f"RTG-{uuid.uuid4().hex[:8].upper()}",
            version=new_version or source.version,
            is_primary=False,  # 复制的路线默认非主
            plant_code=source.plant_code,
            line_code=source.line_code,
            created_by_id=user_id,
        )
        self.session.add(new_routing)
        self.session.flush()

        # 复制工序
        source_ops = self.session.query(Operation).filter(
            Operation.routing_id == source_routing_id
        ).order_by(Operation.sequence).all()

        for op in source_ops:
            new_op = Operation(
                id=str(uuid.uuid4()),
                routing_id=new_routing.id,
                operation_number=op.operation_number,
                name=op.name,
                operation_type=op.operation_type,
                sequence=op.sequence,
                workcenter_code=op.workcenter_code,
                setup_time=op.setup_time,
                run_time=op.run_time,
                queue_time=op.queue_time,
                move_time=op.move_time,
                labor_setup_time=op.labor_setup_time,
                labor_run_time=op.labor_run_time,
                crew_size=op.crew_size,
                is_subcontracted=op.is_subcontracted,
                inspection_required=op.inspection_required,
                work_instructions=op.work_instructions,
                tooling_requirements=op.tooling_requirements,
                document_ids=op.document_ids,
            )
            self.session.add(new_op)

        self.session.flush()
        self._update_routing_totals(new_routing.id)

        return new_routing
```

### 4.4 数据库迁移

#### `migrations/versions/p3_add_manufacturing_tables.py`

```python
"""Add manufacturing tables

Revision ID: p3_mfg_001
Revises: p2_config_001
Create Date: 2026-02-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'p3_mfg_001'
down_revision = 'p2_config_001'
branch_labels = None
depends_on = None


def upgrade():
    # WorkCenter 工作中心
    op.create_table(
        'meta_workcenters',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('code', sa.String(), nullable=False, unique=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('plant_code', sa.String(), nullable=True),
        sa.Column('department_code', sa.String(), nullable=True),
        sa.Column('capacity_per_day', sa.Float(), default=8.0),
        sa.Column('efficiency', sa.Float(), default=1.0),
        sa.Column('utilization', sa.Float(), default=0.9),
        sa.Column('machine_count', sa.Integer(), default=1),
        sa.Column('worker_count', sa.Integer(), default=1),
        sa.Column('cost_center', sa.String(), nullable=True),
        sa.Column('labor_rate', sa.Float(), nullable=True),
        sa.Column('overhead_rate', sa.Float(), nullable=True),
        sa.Column('scheduling_type', sa.String(), default='finite'),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    # Manufacturing BOM
    op.create_table(
        'meta_manufacturing_boms',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('source_item_id', sa.String(), sa.ForeignKey('meta_items.id'), nullable=False, index=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('version', sa.String(), default='1.0'),
        sa.Column('revision', sa.Integer(), default=1),
        sa.Column('bom_type', sa.String(), default='mbom'),
        sa.Column('plant_code', sa.String(), nullable=True),
        sa.Column('line_code', sa.String(), nullable=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('state', sa.String(), default='draft'),
        sa.Column('structure', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('rbac_users.id'), nullable=True),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('released_by_id', sa.Integer(), sa.ForeignKey('rbac_users.id'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # MBOM Lines
    op.create_table(
        'meta_mbom_lines',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('mbom_id', sa.String(), sa.ForeignKey('meta_manufacturing_boms.id'), nullable=False, index=True),
        sa.Column('parent_line_id', sa.String(), sa.ForeignKey('meta_mbom_lines.id'), nullable=True),
        sa.Column('item_id', sa.String(), sa.ForeignKey('meta_items.id'), nullable=False, index=True),
        sa.Column('sequence', sa.Integer(), default=10),
        sa.Column('level', sa.Integer(), default=0),
        sa.Column('quantity', sa.Numeric(20, 6), default=1),
        sa.Column('unit', sa.String(), default='EA'),
        sa.Column('ebom_relationship_id', sa.String(), nullable=True),
        sa.Column('make_buy', sa.String(), default='make'),
        sa.Column('supply_type', sa.String(), nullable=True),
        sa.Column('operation_id', sa.String(), nullable=True),
        sa.Column('backflush', sa.Boolean(), default=False),
        sa.Column('scrap_rate', sa.Float(), default=0.0),
        sa.Column('fixed_quantity', sa.Boolean(), default=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('properties', postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # Routing 工艺路线
    op.create_table(
        'meta_routings',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('mbom_id', sa.String(), sa.ForeignKey('meta_manufacturing_boms.id'), nullable=True, index=True),
        sa.Column('item_id', sa.String(), sa.ForeignKey('meta_items.id'), nullable=True, index=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('routing_code', sa.String(), unique=True),
        sa.Column('version', sa.String(), default='1.0'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_primary', sa.Boolean(), default=True),
        sa.Column('plant_code', sa.String(), nullable=True),
        sa.Column('line_code', sa.String(), nullable=True),
        sa.Column('state', sa.String(), default='draft'),
        sa.Column('total_setup_time', sa.Float(), default=0.0),
        sa.Column('total_run_time', sa.Float(), default=0.0),
        sa.Column('total_labor_time', sa.Float(), default=0.0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('rbac_users.id'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # Operation 工序
    op.create_table(
        'meta_operations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('routing_id', sa.String(), sa.ForeignKey('meta_routings.id'), nullable=False, index=True),
        sa.Column('operation_number', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('operation_type', sa.String(), default='fabrication'),
        sa.Column('sequence', sa.Integer(), default=10),
        sa.Column('workcenter_id', sa.String(), nullable=True),
        sa.Column('workcenter_code', sa.String(), nullable=True),
        sa.Column('setup_time', sa.Float(), default=0.0),
        sa.Column('run_time', sa.Float(), default=0.0),
        sa.Column('queue_time', sa.Float(), default=0.0),
        sa.Column('move_time', sa.Float(), default=0.0),
        sa.Column('wait_time', sa.Float(), default=0.0),
        sa.Column('labor_setup_time', sa.Float(), default=0.0),
        sa.Column('labor_run_time', sa.Float(), default=0.0),
        sa.Column('crew_size', sa.Integer(), default=1),
        sa.Column('machines_required', sa.Integer(), default=1),
        sa.Column('overlap_quantity', sa.Integer(), nullable=True),
        sa.Column('transfer_batch', sa.Integer(), nullable=True),
        sa.Column('is_subcontracted', sa.Boolean(), default=False),
        sa.Column('subcontractor_id', sa.String(), nullable=True),
        sa.Column('inspection_required', sa.Boolean(), default=False),
        sa.Column('inspection_plan_id', sa.String(), nullable=True),
        sa.Column('tooling_requirements', postgresql.JSONB(), nullable=True),
        sa.Column('work_instructions', sa.Text(), nullable=True),
        sa.Column('document_ids', postgresql.JSONB(), nullable=True),
        sa.Column('labor_cost_rate', sa.Float(), nullable=True),
        sa.Column('overhead_rate', sa.Float(), nullable=True),
        sa.Column('properties', postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # 添加 MBOM Line 的 operation_id 外键
    op.create_foreign_key(
        'fk_mbom_line_operation',
        'meta_mbom_lines', 'meta_operations',
        ['operation_id'], ['id'],
    )


def downgrade():
    op.drop_constraint('fk_mbom_line_operation', 'meta_mbom_lines', type_='foreignkey')
    op.drop_table('meta_operations')
    op.drop_table('meta_routings')
    op.drop_table('meta_mbom_lines')
    op.drop_table('meta_manufacturing_boms')
    op.drop_table('meta_workcenters')
```

---

## 5. Phase 4: 基线管理增强

### 5.1 目标

增强基线管理功能，支持多类型基线、基线比较、基线验证和变更追踪。

### 5.2 数据模型

#### `src/yuantus/meta_engine/baseline/models.py`

```python
"""
基线管理增强数据模型
"""
from sqlalchemy import (
    Column, String, Integer, ForeignKey, DateTime,
    Boolean, Text, JSON
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from yuantus.models.base import Base


class BaselineType(str, enum.Enum):
    """基线类型"""
    DESIGN = "design"           # 设计基线
    FUNCTIONAL = "functional"   # 功能基线
    PRODUCT = "product"         # 产品基线
    RELEASE = "release"         # 发布基线
    MANUFACTURING = "manufacturing"  # 制造基线


class BaselineScope(str, enum.Enum):
    """基线范围"""
    PRODUCT = "product"     # 产品级（含完整 BOM）
    ASSEMBLY = "assembly"   # 装配级
    ITEM = "item"           # 单品级
    DOCUMENT = "document"   # 文档集


class Baseline(Base):
    """
    基线定义
    记录特定时间点的配置状态
    """
    __tablename__ = "meta_baselines"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 基线标识
    name = Column(String, nullable=False)
    baseline_number = Column(String, unique=True)
    description = Column(Text, nullable=True)

    # 类型和范围
    baseline_type = Column(String, default=BaselineType.PRODUCT.value)
    scope = Column(String, default=BaselineScope.PRODUCT.value)

    # 根 Item（基线的锚点）
    root_item_id = Column(String, ForeignKey("meta_items.id"), nullable=False, index=True)

    # 关联的 ECO（可选）
    eco_id = Column(String, ForeignKey("meta_items.id"), nullable=True)

    # 快照配置
    include_bom = Column(Boolean, default=True)
    include_documents = Column(Boolean, default=True)
    include_relationships = Column(Boolean, default=True)
    bom_levels = Column(Integer, default=20)

    # 有效日期（基线生效时间点）
    effective_date = Column(DateTime(timezone=True), nullable=True)

    # 状态
    state = Column(String, default="draft")  # draft, proposed, approved, released, obsolete

    # 验证状态
    is_validated = Column(Boolean, default=False)
    validation_errors = Column(JSON().with_variant(JSONB, "postgresql"))
    validated_at = Column(DateTime(timezone=True), nullable=True)
    validated_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)

    # 锁定状态
    is_locked = Column(Boolean, default=False)
    locked_at = Column(DateTime(timezone=True), nullable=True)

    # 审计
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)
    released_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)

    # Relationships
    members = relationship("BaselineMember", back_populates="baseline", cascade="all, delete-orphan")


class BaselineMember(Base):
    """
    基线成员
    基线中包含的具体版本
    """
    __tablename__ = "meta_baseline_members"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    baseline_id = Column(String, ForeignKey("meta_baselines.id"), nullable=False, index=True)

    # 成员 Item（具体版本）
    item_id = Column(String, ForeignKey("meta_items.id"), nullable=False, index=True)

    # Item 基本信息快照（便于查询）
    item_number = Column(String)
    item_revision = Column(String)
    item_generation = Column(Integer)
    item_type = Column(String)

    # BOM 层级
    level = Column(Integer, default=0)
    path = Column(String)  # 父级路径，如 "root/assy1/assy2"

    # 数量（如果是 BOM 成员）
    quantity = Column(String, nullable=True)

    # 包含类型
    member_type = Column(String, default="item")  # item, document, relationship

    # 状态快照
    item_state = Column(String)

    # Relationships
    baseline = relationship("Baseline", back_populates="members")


class BaselineComparison(Base):
    """
    基线比较结果
    存储两个基线之间的差异
    """
    __tablename__ = "meta_baseline_comparisons"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 比较的两个基线
    baseline_a_id = Column(String, ForeignKey("meta_baselines.id"), nullable=False)
    baseline_b_id = Column(String, ForeignKey("meta_baselines.id"), nullable=False)

    # 比较结果摘要
    added_count = Column(Integer, default=0)
    removed_count = Column(Integer, default=0)
    changed_count = Column(Integer, default=0)
    unchanged_count = Column(Integer, default=0)

    # 详细差异（JSON）
    differences = Column(JSON().with_variant(JSONB, "postgresql"))

    # 执行时间
    compared_at = Column(DateTime(timezone=True), server_default=func.now())
    compared_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
```

### 5.3 服务层

#### `src/yuantus/meta_engine/baseline/service.py`

```python
"""
基线管理服务
"""
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import uuid
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_

from yuantus.meta_engine.baseline.models import (
    Baseline, BaselineMember, BaselineComparison,
    BaselineType, BaselineScope
)
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.bom_service import BOMService

logger = logging.getLogger(__name__)


class BaselineService:
    """基线管理服务"""

    def __init__(self, session: Session):
        self.session = session
        self.bom_service = BOMService(session)

    def create_baseline(
        self,
        name: str,
        root_item_id: str,
        *,
        baseline_type: str = "product",
        scope: str = "product",
        description: str = None,
        effective_date: datetime = None,
        include_bom: bool = True,
        include_documents: bool = True,
        bom_levels: int = 20,
        eco_id: str = None,
        user_id: int = None,
        auto_populate: bool = True,
    ) -> Baseline:
        """
        创建基线

        Args:
            auto_populate: 是否自动填充基线成员
        """
        # 验证根 Item
        root_item = self.session.get(Item, root_item_id)
        if not root_item:
            raise ValueError(f"Root item not found: {root_item_id}")

        # 生成基线编号
        baseline_number = f"BL-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        baseline = Baseline(
            id=str(uuid.uuid4()),
            name=name,
            baseline_number=baseline_number,
            description=description,
            baseline_type=baseline_type,
            scope=scope,
            root_item_id=root_item_id,
            eco_id=eco_id,
            effective_date=effective_date or datetime.utcnow(),
            include_bom=include_bom,
            include_documents=include_documents,
            bom_levels=bom_levels,
            created_by_id=user_id,
        )
        self.session.add(baseline)
        self.session.flush()

        # 自动填充成员
        if auto_populate:
            self._populate_members(baseline)

        return baseline

    def _populate_members(self, baseline: Baseline) -> None:
        """填充基线成员"""
        root_item = self.session.get(Item, baseline.root_item_id)

        # 添加根 Item
        self._add_member(baseline, root_item, level=0, path="")

        # 如果包含 BOM，递归添加
        if baseline.include_bom:
            bom = self.bom_service.get_bom_structure(
                baseline.root_item_id,
                levels=baseline.bom_levels,
                effective_date=baseline.effective_date,
            )
            self._add_bom_members(baseline, bom, level=1, path=root_item.config_id or "root")

        # 如果包含文档，添加关联文档
        if baseline.include_documents:
            self._add_document_members(baseline, baseline.root_item_id)

    def _add_member(
        self,
        baseline: Baseline,
        item: Item,
        level: int,
        path: str,
        quantity: str = None,
        member_type: str = "item",
    ) -> BaselineMember:
        """添加基线成员"""
        member = BaselineMember(
            id=str(uuid.uuid4()),
            baseline_id=baseline.id,
            item_id=item.id,
            item_number=item.config_id,
            item_revision=item.properties.get("revision") if item.properties else None,
            item_generation=item.generation,
            item_type=item.item_type_id,
            level=level,
            path=path,
            quantity=quantity,
            member_type=member_type,
            item_state=item.state,
        )
        self.session.add(member)
        return member

    def _add_bom_members(
        self,
        baseline: Baseline,
        bom: Dict[str, Any],
        level: int,
        path: str,
    ) -> None:
        """递归添加 BOM 成员"""
        children = bom.get("children") or []
        for child_entry in children:
            rel = child_entry.get("relationship") or {}
            child_data = child_entry.get("child") or {}
            child_id = child_data.get("id")

            if not child_id:
                continue

            child_item = self.session.get(Item, child_id)
            if not child_item:
                continue

            # 获取数量
            rel_props = rel.get("properties") or {}
            quantity = str(rel_props.get("quantity", 1))

            # 构建路径
            child_path = f"{path}/{child_item.config_id or child_id}"

            # 添加成员
            self._add_member(
                baseline, child_item,
                level=level,
                path=child_path,
                quantity=quantity,
            )

            # 递归处理子级
            if child_data.get("children"):
                self._add_bom_members(
                    baseline,
                    child_data,
                    level=level + 1,
                    path=child_path,
                )

    def _add_document_members(self, baseline: Baseline, item_id: str) -> None:
        """添加文档成员"""
        # 查找关联的文档
        from yuantus.meta_engine.models.file import FileContainer

        docs = self.session.query(FileContainer).filter(
            FileContainer.item_id == item_id
        ).all()

        for doc in docs:
            # 文档作为特殊成员
            member = BaselineMember(
                id=str(uuid.uuid4()),
                baseline_id=baseline.id,
                item_id=doc.id,
                item_number=doc.filename,
                level=0,
                path="documents",
                member_type="document",
            )
            self.session.add(member)

    def validate_baseline(self, baseline_id: str, user_id: int = None) -> Dict[str, Any]:
        """
        验证基线完整性

        检查项：
        1. 所有成员是否存在
        2. 所有成员是否处于已发布状态
        3. BOM 结构是否完整
        4. 是否有循环引用
        """
        baseline = self.session.get(Baseline, baseline_id)
        if not baseline:
            raise ValueError(f"Baseline not found: {baseline_id}")

        errors = []
        warnings = []

        members = self.session.query(BaselineMember).filter(
            BaselineMember.baseline_id == baseline_id
        ).all()

        # 检查成员
        for member in members:
            item = self.session.get(Item, member.item_id)

            # 存在性检查
            if not item:
                errors.append({
                    "type": "missing_item",
                    "member_id": member.id,
                    "item_id": member.item_id,
                    "message": f"Item not found: {member.item_number}",
                })
                continue

            # 状态检查
            if item.state not in ("released", "approved"):
                warnings.append({
                    "type": "unreleased_item",
                    "member_id": member.id,
                    "item_id": member.item_id,
                    "item_state": item.state,
                    "message": f"Item {member.item_number} is not released (state: {item.state})",
                })

            # 版本一致性检查
            if item.generation != member.item_generation:
                warnings.append({
                    "type": "version_mismatch",
                    "member_id": member.id,
                    "expected_generation": member.item_generation,
                    "current_generation": item.generation,
                    "message": f"Item {member.item_number} version changed",
                })

        # 更新验证状态
        is_valid = len(errors) == 0
        baseline.is_validated = is_valid
        baseline.validation_errors = {"errors": errors, "warnings": warnings}
        baseline.validated_at = datetime.utcnow()
        baseline.validated_by_id = user_id
        self.session.add(baseline)

        return {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "validated_at": baseline.validated_at.isoformat(),
        }

    def compare_baselines(
        self,
        baseline_a_id: str,
        baseline_b_id: str,
        user_id: int = None,
    ) -> Dict[str, Any]:
        """
        比较两个基线的差异
        """
        baseline_a = self.session.get(Baseline, baseline_a_id)
        baseline_b = self.session.get(Baseline, baseline_b_id)

        if not baseline_a or not baseline_b:
            raise ValueError("Baseline not found")

        # 获取成员
        members_a = {
            m.item_id: m for m in self.session.query(BaselineMember).filter(
                BaselineMember.baseline_id == baseline_a_id
            ).all()
        }
        members_b = {
            m.item_id: m for m in self.session.query(BaselineMember).filter(
                BaselineMember.baseline_id == baseline_b_id
            ).all()
        }

        ids_a = set(members_a.keys())
        ids_b = set(members_b.keys())

        added = []      # 在 B 中新增
        removed = []    # 在 B 中删除
        changed = []    # 发生变化
        unchanged = []  # 未变化

        # 新增项
        for item_id in ids_b - ids_a:
            m = members_b[item_id]
            added.append({
                "item_id": item_id,
                "item_number": m.item_number,
                "revision": m.item_revision,
            })

        # 删除项
        for item_id in ids_a - ids_b:
            m = members_a[item_id]
            removed.append({
                "item_id": item_id,
                "item_number": m.item_number,
                "revision": m.item_revision,
            })

        # 变化项
        for item_id in ids_a & ids_b:
            ma = members_a[item_id]
            mb = members_b[item_id]

            if ma.item_generation != mb.item_generation or ma.item_revision != mb.item_revision:
                changed.append({
                    "item_id": item_id,
                    "item_number": ma.item_number,
                    "baseline_a": {
                        "revision": ma.item_revision,
                        "generation": ma.item_generation,
                    },
                    "baseline_b": {
                        "revision": mb.item_revision,
                        "generation": mb.item_generation,
                    },
                })
            else:
                unchanged.append({
                    "item_id": item_id,
                    "item_number": ma.item_number,
                })

        # 存储比较结果
        comparison = BaselineComparison(
            id=str(uuid.uuid4()),
            baseline_a_id=baseline_a_id,
            baseline_b_id=baseline_b_id,
            added_count=len(added),
            removed_count=len(removed),
            changed_count=len(changed),
            unchanged_count=len(unchanged),
            differences={
                "added": added,
                "removed": removed,
                "changed": changed,
            },
            compared_by_id=user_id,
        )
        self.session.add(comparison)
        self.session.flush()

        return {
            "comparison_id": comparison.id,
            "baseline_a": {"id": baseline_a.id, "name": baseline_a.name},
            "baseline_b": {"id": baseline_b.id, "name": baseline_b.name},
            "summary": {
                "added": len(added),
                "removed": len(removed),
                "changed": len(changed),
                "unchanged": len(unchanged),
            },
            "details": {
                "added": added,
                "removed": removed,
                "changed": changed,
            },
        }

    def release_baseline(
        self,
        baseline_id: str,
        user_id: int = None,
        force: bool = False,
    ) -> Baseline:
        """
        发布基线
        """
        baseline = self.session.get(Baseline, baseline_id)
        if not baseline:
            raise ValueError(f"Baseline not found: {baseline_id}")

        if baseline.state == "released":
            raise ValueError("Baseline is already released")

        # 验证
        if not force and not baseline.is_validated:
            validation = self.validate_baseline(baseline_id, user_id)
            if not validation["is_valid"]:
                raise ValueError(f"Baseline validation failed: {validation['errors']}")

        # 发布
        baseline.state = "released"
        baseline.is_locked = True
        baseline.locked_at = datetime.utcnow()
        baseline.released_at = datetime.utcnow()
        baseline.released_by_id = user_id
        self.session.add(baseline)

        return baseline

    def get_baseline_at_date(
        self,
        root_item_id: str,
        target_date: datetime,
        baseline_type: str = None,
    ) -> Optional[Baseline]:
        """
        获取指定日期有效的基线
        """
        query = self.session.query(Baseline).filter(
            Baseline.root_item_id == root_item_id,
            Baseline.state == "released",
            Baseline.effective_date <= target_date,
        )

        if baseline_type:
            query = query.filter(Baseline.baseline_type == baseline_type)

        return query.order_by(Baseline.effective_date.desc()).first()
```

---

## 6. Phase 5: 高级搜索与报表

### 6.1 目标

实现企业级搜索能力和可配置报表系统，支持全文搜索、保存查询、仪表板和导出功能。

### 6.2 数据模型

#### `src/yuantus/meta_engine/reports/models.py`

```python
"""
报表与查询数据模型
"""
from sqlalchemy import (
    Column, String, Integer, ForeignKey, DateTime,
    Boolean, Text, JSON
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from yuantus.models.base import Base


class ReportType(str, enum.Enum):
    """报表类型"""
    TABLE = "table"           # 表格报表
    CHART = "chart"           # 图表报表
    PIVOT = "pivot"           # 透视表
    DASHBOARD = "dashboard"   # 仪表板
    CROSSTAB = "crosstab"     # 交叉表


class ChartType(str, enum.Enum):
    """图表类型"""
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"
    AREA = "area"
    TREEMAP = "treemap"
    GAUGE = "gauge"


class SavedSearch(Base):
    """
    保存的搜索
    用户可以保存常用搜索条件
    """
    __tablename__ = "meta_saved_searches"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 搜索标识
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # 所有者
    owner_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    is_public = Column(Boolean, default=False)

    # 搜索范围
    item_type_id = Column(String, ForeignKey("meta_item_types.id"), nullable=True)

    # 搜索条件（JSON）
    criteria = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    # 格式: {
    #     "filters": [
    #         {"field": "state", "op": "eq", "value": "released"},
    #         {"field": "created_at", "op": "gte", "value": "2024-01-01"}
    #     ],
    #     "full_text": "search term",
    #     "sort": [{"field": "created_at", "order": "desc"}],
    #     "columns": ["config_id", "name", "state", "created_at"]
    # }

    # 显示配置
    display_columns = Column(JSON().with_variant(JSONB, "postgresql"))
    page_size = Column(Integer, default=25)

    # 使用统计
    use_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # 审计
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ReportDefinition(Base):
    """
    报表定义
    可重用的报表模板
    """
    __tablename__ = "meta_report_definitions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 报表标识
    name = Column(String, nullable=False)
    code = Column(String, unique=True)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)

    # 报表类型
    report_type = Column(String, default=ReportType.TABLE.value)

    # 数据源配置
    data_source = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    # 格式: {
    #     "type": "query",  # query, saved_search, custom
    #     "base_type": "Part",  # ItemType
    #     "joins": [...],
    #     "aggregations": [...],
    #     "filters": [...]
    # }

    # 显示配置
    layout = Column(JSON().with_variant(JSONB, "postgresql"))
    # 格式: {
    #     "columns": [...],
    #     "grouping": {...},
    #     "totals": {...},
    #     "chart_config": {...}
    # }

    # 参数定义（用户可输入的参数）
    parameters = Column(JSON().with_variant(JSONB, "postgresql"))
    # 格式: [
    #     {"name": "start_date", "type": "date", "required": true, "default": "today-30d"},
    #     {"name": "item_type", "type": "select", "options_source": "item_types"}
    # ]

    # 权限
    owner_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    is_public = Column(Boolean, default=False)
    allowed_roles = Column(JSON().with_variant(JSONB, "postgresql"))

    # 状态
    is_active = Column(Boolean, default=True)

    # 审计
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ReportExecution(Base):
    """
    报表执行记录
    """
    __tablename__ = "meta_report_executions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    report_id = Column(String, ForeignKey("meta_report_definitions.id"), nullable=False, index=True)

    # 执行参数
    parameters_used = Column(JSON().with_variant(JSONB, "postgresql"))

    # 执行状态
    status = Column(String, default="running")  # running, completed, failed
    error_message = Column(Text, nullable=True)

    # 执行统计
    row_count = Column(Integer, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)

    # 导出信息
    export_format = Column(String, nullable=True)  # csv, xlsx, pdf
    export_path = Column(String, nullable=True)

    # 审计
    executed_at = Column(DateTime(timezone=True), server_default=func.now())
    executed_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class Dashboard(Base):
    """
    仪表板定义
    """
    __tablename__ = "meta_dashboards"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 仪表板标识
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # 布局配置
    layout = Column(JSON().with_variant(JSONB, "postgresql"))
    # 格式: {
    #     "rows": [
    #         {"columns": [
    #             {"widget_id": "xxx", "width": 6},
    #             {"widget_id": "yyy", "width": 6}
    #         ]},
    #         ...
    #     ]
    # }

    # 小部件配置
    widgets = Column(JSON().with_variant(JSONB, "postgresql"))
    # 格式: [
    #     {
    #         "id": "xxx",
    #         "type": "chart",
    #         "title": "Items by State",
    #         "report_id": "report-123",
    #         "config": {...}
    #     }
    # ]

    # 刷新设置
    auto_refresh = Column(Boolean, default=False)
    refresh_interval = Column(Integer, default=300)  # 秒

    # 权限
    owner_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    is_public = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)

    # 审计
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
```

### 6.3 服务层

#### `src/yuantus/meta_engine/reports/search_service.py`

```python
"""
高级搜索服务
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import uuid
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text, func as sqla_func
from elasticsearch import Elasticsearch

from yuantus.meta_engine.reports.models import SavedSearch
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType, PropertyDefinition

logger = logging.getLogger(__name__)


class AdvancedSearchService:
    """高级搜索服务"""

    def __init__(self, session: Session, es_client: Elasticsearch = None):
        self.session = session
        self.es = es_client

    def search(
        self,
        *,
        item_type_id: str = None,
        filters: List[Dict[str, Any]] = None,
        full_text: str = None,
        sort: List[Dict[str, str]] = None,
        columns: List[str] = None,
        page: int = 1,
        page_size: int = 25,
        include_count: bool = True,
        user_id: int = None,
    ) -> Dict[str, Any]:
        """
        执行高级搜索

        Args:
            filters: 过滤条件列表
                [{"field": "state", "op": "eq", "value": "released"}]
            full_text: 全文搜索词
            sort: 排序配置
            columns: 返回的列
        """
        # 如果有全文搜索且有 ES，使用 ES
        if full_text and self.es:
            return self._search_with_elasticsearch(
                item_type_id=item_type_id,
                filters=filters,
                full_text=full_text,
                sort=sort,
                page=page,
                page_size=page_size,
            )

        # 否则使用 SQL
        return self._search_with_sql(
            item_type_id=item_type_id,
            filters=filters,
            full_text=full_text,
            sort=sort,
            columns=columns,
            page=page,
            page_size=page_size,
            include_count=include_count,
        )

    def _search_with_sql(
        self,
        *,
        item_type_id: str = None,
        filters: List[Dict[str, Any]] = None,
        full_text: str = None,
        sort: List[Dict[str, str]] = None,
        columns: List[str] = None,
        page: int = 1,
        page_size: int = 25,
        include_count: bool = True,
    ) -> Dict[str, Any]:
        """SQL 搜索"""
        query = self.session.query(Item)

        # 类型过滤
        if item_type_id:
            query = query.filter(Item.item_type_id == item_type_id)

        # 应用过滤条件
        if filters:
            for f in filters:
                query = self._apply_filter(query, f)

        # 全文搜索（简化版，使用 LIKE）
        if full_text:
            search_term = f"%{full_text}%"
            query = query.filter(
                or_(
                    Item.config_id.ilike(search_term),
                    Item.properties["name"].astext.ilike(search_term),
                    Item.properties["description"].astext.ilike(search_term),
                )
            )

        # 计数
        total = query.count() if include_count else None

        # 排序
        if sort:
            for s in sort:
                field = s.get("field", "created_at")
                order = s.get("order", "desc")

                if hasattr(Item, field):
                    col = getattr(Item, field)
                else:
                    # JSON 字段
                    col = Item.properties[field].astext

                if order == "desc":
                    query = query.order_by(col.desc())
                else:
                    query = query.order_by(col.asc())
        else:
            query = query.order_by(Item.created_at.desc())

        # 分页
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()

        # 格式化结果
        results = []
        for item in items:
            row = {
                "id": item.id,
                "config_id": item.config_id,
                "item_type_id": item.item_type_id,
                "generation": item.generation,
                "state": item.state,
                "is_current": item.is_current,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }

            # 添加属性
            if item.properties:
                if columns:
                    for col in columns:
                        if col in item.properties:
                            row[col] = item.properties[col]
                else:
                    row.update(item.properties)

            results.append(row)

        return {
            "items": results,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size if total else None,
        }

    def _apply_filter(self, query, filter_def: Dict[str, Any]):
        """应用单个过滤条件"""
        field = filter_def.get("field")
        op = filter_def.get("op", "eq")
        value = filter_def.get("value")

        if not field:
            return query

        # 确定列
        if hasattr(Item, field):
            column = getattr(Item, field)
        else:
            # JSON 字段
            column = Item.properties[field].astext

        # 应用操作符
        if op == "eq":
            return query.filter(column == value)
        elif op == "ne":
            return query.filter(column != value)
        elif op == "gt":
            return query.filter(column > value)
        elif op == "gte":
            return query.filter(column >= value)
        elif op == "lt":
            return query.filter(column < value)
        elif op == "lte":
            return query.filter(column <= value)
        elif op == "like":
            return query.filter(column.ilike(f"%{value}%"))
        elif op == "startswith":
            return query.filter(column.ilike(f"{value}%"))
        elif op == "endswith":
            return query.filter(column.ilike(f"%{value}"))
        elif op == "in":
            return query.filter(column.in_(value))
        elif op == "notin":
            return query.filter(~column.in_(value))
        elif op == "isnull":
            return query.filter(column.is_(None) if value else column.isnot(None))
        elif op == "between":
            return query.filter(column.between(value[0], value[1]))

        return query

    def _search_with_elasticsearch(
        self,
        *,
        item_type_id: str = None,
        filters: List[Dict[str, Any]] = None,
        full_text: str = None,
        sort: List[Dict[str, str]] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> Dict[str, Any]:
        """Elasticsearch 搜索"""
        must = []
        filter_clauses = []

        # 类型过滤
        if item_type_id:
            filter_clauses.append({"term": {"item_type_id": item_type_id}})

        # 全文搜索
        if full_text:
            must.append({
                "multi_match": {
                    "query": full_text,
                    "fields": ["config_id^3", "name^2", "description", "properties.*"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            })

        # 其他过滤条件
        if filters:
            for f in filters:
                es_filter = self._convert_filter_to_es(f)
                if es_filter:
                    filter_clauses.append(es_filter)

        # 构建查询
        es_query = {
            "bool": {
                "must": must if must else [{"match_all": {}}],
                "filter": filter_clauses,
            }
        }

        # 排序
        es_sort = []
        if sort:
            for s in sort:
                es_sort.append({s["field"]: {"order": s.get("order", "desc")}})
        else:
            es_sort.append({"created_at": {"order": "desc"}})

        # 执行搜索
        response = self.es.search(
            index="yuantus_items",
            body={
                "query": es_query,
                "sort": es_sort,
                "from": (page - 1) * page_size,
                "size": page_size,
            },
        )

        # 处理结果
        hits = response.get("hits", {})
        total = hits.get("total", {}).get("value", 0)

        items = []
        for hit in hits.get("hits", []):
            source = hit.get("_source", {})
            source["_score"] = hit.get("_score")
            items.append(source)

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size if total else 0,
        }

    def _convert_filter_to_es(self, filter_def: Dict[str, Any]) -> Optional[Dict]:
        """转换过滤条件为 ES 格式"""
        field = filter_def.get("field")
        op = filter_def.get("op", "eq")
        value = filter_def.get("value")

        if op == "eq":
            return {"term": {field: value}}
        elif op == "ne":
            return {"bool": {"must_not": {"term": {field: value}}}}
        elif op in ("gt", "gte", "lt", "lte"):
            return {"range": {field: {op: value}}}
        elif op == "like":
            return {"wildcard": {field: f"*{value}*"}}
        elif op == "in":
            return {"terms": {field: value}}
        elif op == "between":
            return {"range": {field: {"gte": value[0], "lte": value[1]}}}

        return None

    # ==================== 保存的搜索管理 ====================

    def save_search(
        self,
        name: str,
        criteria: Dict[str, Any],
        *,
        description: str = None,
        item_type_id: str = None,
        is_public: bool = False,
        display_columns: List[str] = None,
        user_id: int = None,
    ) -> SavedSearch:
        """保存搜索"""
        saved = SavedSearch(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            owner_id=user_id,
            is_public=is_public,
            item_type_id=item_type_id,
            criteria=criteria,
            display_columns=display_columns,
        )
        self.session.add(saved)
        self.session.flush()
        return saved

    def execute_saved_search(
        self,
        search_id: str,
        *,
        page: int = 1,
        page_size: int = None,
        user_id: int = None,
    ) -> Dict[str, Any]:
        """执行保存的搜索"""
        saved = self.session.get(SavedSearch, search_id)
        if not saved:
            raise ValueError(f"Saved search not found: {search_id}")

        # 更新使用统计
        saved.use_count = (saved.use_count or 0) + 1
        saved.last_used_at = datetime.utcnow()
        self.session.add(saved)

        # 执行搜索
        criteria = saved.criteria or {}
        return self.search(
            item_type_id=saved.item_type_id,
            filters=criteria.get("filters"),
            full_text=criteria.get("full_text"),
            sort=criteria.get("sort"),
            columns=saved.display_columns or criteria.get("columns"),
            page=page,
            page_size=page_size or saved.page_size or 25,
            user_id=user_id,
        )
```

#### `src/yuantus/meta_engine/reports/report_service.py`

```python
"""
报表服务
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import logging
import io
import csv

from sqlalchemy.orm import Session
from sqlalchemy import func as sqla_func, text

from yuantus.meta_engine.reports.models import (
    ReportDefinition, ReportExecution, ReportType
)
from yuantus.meta_engine.models.item import Item

logger = logging.getLogger(__name__)


class ReportService:
    """报表服务"""

    def __init__(self, session: Session):
        self.session = session

    def execute_report(
        self,
        report_id: str,
        parameters: Dict[str, Any] = None,
        *,
        export_format: str = None,
        user_id: int = None,
    ) -> Dict[str, Any]:
        """
        执行报表

        Args:
            report_id: 报表定义 ID
            parameters: 用户输入的参数
            export_format: 导出格式 (csv, xlsx, pdf)
        """
        report = self.session.get(ReportDefinition, report_id)
        if not report:
            raise ValueError(f"Report not found: {report_id}")

        # 创建执行记录
        execution = ReportExecution(
            id=str(uuid.uuid4()),
            report_id=report_id,
            parameters_used=parameters,
            executed_by_id=user_id,
        )
        self.session.add(execution)
        self.session.flush()

        start_time = datetime.utcnow()

        try:
            # 处理参数
            resolved_params = self._resolve_parameters(report, parameters)

            # 获取数据
            data = self._fetch_report_data(report, resolved_params)

            # 应用布局/格式化
            formatted = self._format_report_data(report, data)

            # 计算执行时间
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # 更新执行记录
            execution.status = "completed"
            execution.row_count = len(data.get("rows", []))
            execution.execution_time_ms = execution_time
            execution.completed_at = datetime.utcnow()

            # 导出
            if export_format:
                export_path = self._export_report(formatted, export_format, report.name)
                execution.export_format = export_format
                execution.export_path = export_path

            self.session.add(execution)

            return {
                "execution_id": execution.id,
                "report_name": report.name,
                "report_type": report.report_type,
                "data": formatted,
                "row_count": execution.row_count,
                "execution_time_ms": execution_time,
                "export_path": execution.export_path,
            }

        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            self.session.add(execution)
            raise

    def _resolve_parameters(
        self,
        report: ReportDefinition,
        user_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """解析报表参数"""
        resolved = {}
        param_defs = report.parameters or []

        for param_def in param_defs:
            name = param_def.get("name")
            param_type = param_def.get("type")
            required = param_def.get("required", False)
            default = param_def.get("default")

            # 获取用户输入或默认值
            value = (user_params or {}).get(name, default)

            # 必填检查
            if required and value is None:
                raise ValueError(f"Required parameter missing: {name}")

            # 类型转换
            if value is not None:
                if param_type == "date":
                    value = self._parse_date_param(value)
                elif param_type == "number":
                    value = float(value)
                elif param_type == "integer":
                    value = int(value)

            resolved[name] = value

        return resolved

    def _parse_date_param(self, value: str) -> datetime:
        """解析日期参数"""
        if value.startswith("today"):
            base = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            if "-" in value:
                days = int(value.split("-")[1].replace("d", ""))
                return base - timedelta(days=days)
            elif "+" in value:
                days = int(value.split("+")[1].replace("d", ""))
                return base + timedelta(days=days)
            return base
        return datetime.fromisoformat(value)

    def _fetch_report_data(
        self,
        report: ReportDefinition,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """获取报表数据"""
        data_source = report.data_source or {}
        source_type = data_source.get("type", "query")

        if source_type == "query":
            return self._fetch_query_data(data_source, params)
        elif source_type == "aggregation":
            return self._fetch_aggregation_data(data_source, params)
        else:
            raise ValueError(f"Unknown data source type: {source_type}")

    def _fetch_query_data(
        self,
        data_source: Dict[str, Any],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """获取查询数据"""
        base_type = data_source.get("base_type")
        filters = data_source.get("filters", [])

        query = self.session.query(Item)

        if base_type:
            query = query.filter(Item.item_type_id == base_type)

        # 应用过滤（替换参数）
        for f in filters:
            value = f.get("value")
            if isinstance(value, str) and value.startswith("$"):
                param_name = value[1:]
                value = params.get(param_name)
            if value is not None:
                query = self._apply_report_filter(query, f["field"], f.get("op", "eq"), value)

        items = query.all()

        rows = []
        for item in items:
            row = {
                "id": item.id,
                "config_id": item.config_id,
                "item_type_id": item.item_type_id,
                "state": item.state,
                "generation": item.generation,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            if item.properties:
                row.update(item.properties)
            rows.append(row)

        return {"rows": rows}

    def _fetch_aggregation_data(
        self,
        data_source: Dict[str, Any],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """获取聚合数据"""
        base_type = data_source.get("base_type")
        group_by = data_source.get("group_by", [])
        aggregations = data_source.get("aggregations", [])

        # 构建聚合查询
        select_cols = []
        group_cols = []

        for gb in group_by:
            if hasattr(Item, gb):
                col = getattr(Item, gb)
            else:
                col = Item.properties[gb].astext.label(gb)
            select_cols.append(col)
            group_cols.append(col)

        for agg in aggregations:
            agg_func = agg.get("func", "count")
            field = agg.get("field", "*")
            alias = agg.get("alias", f"{agg_func}_{field}")

            if agg_func == "count":
                select_cols.append(sqla_func.count().label(alias))
            elif agg_func == "sum":
                col = Item.properties[field].astext.cast(Float) if field != "*" else None
                if col:
                    select_cols.append(sqla_func.sum(col).label(alias))
            elif agg_func == "avg":
                col = Item.properties[field].astext.cast(Float)
                select_cols.append(sqla_func.avg(col).label(alias))

        query = self.session.query(*select_cols)

        if base_type:
            query = query.filter(Item.item_type_id == base_type)

        if group_cols:
            query = query.group_by(*group_cols)

        results = query.all()

        # 格式化结果
        columns = group_by + [a.get("alias", f"{a['func']}_{a.get('field', '*')}") for a in aggregations]
        rows = [dict(zip(columns, row)) for row in results]

        return {"rows": rows, "columns": columns}

    def _apply_report_filter(self, query, field: str, op: str, value):
        """应用报表过滤"""
        if hasattr(Item, field):
            column = getattr(Item, field)
        else:
            column = Item.properties[field].astext

        if op == "eq":
            return query.filter(column == value)
        elif op == "gte":
            return query.filter(column >= value)
        elif op == "lte":
            return query.filter(column <= value)
        elif op == "in":
            return query.filter(column.in_(value))

        return query

    def _format_report_data(
        self,
        report: ReportDefinition,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """格式化报表数据"""
        layout = report.layout or {}
        rows = data.get("rows", [])

        # 应用列过滤
        columns = layout.get("columns")
        if columns:
            rows = [{k: v for k, v in row.items() if k in columns} for row in rows]

        # 应用分组
        grouping = layout.get("grouping")
        if grouping:
            rows = self._apply_grouping(rows, grouping)

        # 计算汇总
        totals = layout.get("totals")
        summary = {}
        if totals:
            for total_def in totals:
                field = total_def.get("field")
                func = total_def.get("func", "sum")
                values = [r.get(field, 0) for r in data.get("rows", []) if r.get(field) is not None]
                if func == "sum":
                    summary[field] = sum(values)
                elif func == "avg":
                    summary[field] = sum(values) / len(values) if values else 0
                elif func == "count":
                    summary[field] = len(values)

        result = {
            "rows": rows,
            "columns": columns or (list(rows[0].keys()) if rows else []),
            "summary": summary,
        }

        # 图表配置
        chart_config = layout.get("chart_config")
        if chart_config and report.report_type == ReportType.CHART.value:
            result["chart"] = self._prepare_chart_data(data.get("rows", []), chart_config)

        return result

    def _apply_grouping(
        self,
        rows: List[Dict],
        grouping: Dict[str, Any],
    ) -> List[Dict]:
        """应用分组"""
        group_field = grouping.get("field")
        if not group_field:
            return rows

        grouped = {}
        for row in rows:
            key = row.get(group_field, "Unknown")
            if key not in grouped:
                grouped[key] = {"group": key, "items": [], "count": 0}
            grouped[key]["items"].append(row)
            grouped[key]["count"] += 1

        return list(grouped.values())

    def _prepare_chart_data(
        self,
        rows: List[Dict],
        chart_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """准备图表数据"""
        chart_type = chart_config.get("type", "bar")
        x_field = chart_config.get("x_field")
        y_field = chart_config.get("y_field")
        series_field = chart_config.get("series_field")

        labels = []
        datasets = []

        if series_field:
            # 多系列
            series_data = {}
            for row in rows:
                label = str(row.get(x_field, ""))
                series = str(row.get(series_field, "default"))
                value = row.get(y_field, 0)

                if label not in labels:
                    labels.append(label)
                if series not in series_data:
                    series_data[series] = {}
                series_data[series][label] = value

            for series_name, data in series_data.items():
                datasets.append({
                    "label": series_name,
                    "data": [data.get(l, 0) for l in labels],
                })
        else:
            # 单系列
            for row in rows:
                labels.append(str(row.get(x_field, "")))

            datasets.append({
                "label": y_field,
                "data": [row.get(y_field, 0) for row in rows],
            })

        return {
            "type": chart_type,
            "labels": labels,
            "datasets": datasets,
        }

    def _export_report(
        self,
        data: Dict[str, Any],
        format: str,
        report_name: str,
    ) -> str:
        """导出报表"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_name}_{timestamp}"

        if format == "csv":
            return self._export_csv(data, filename)
        elif format == "xlsx":
            return self._export_xlsx(data, filename)
        elif format == "pdf":
            return self._export_pdf(data, filename)

        raise ValueError(f"Unsupported export format: {format}")

    def _export_csv(self, data: Dict[str, Any], filename: str) -> str:
        """导出 CSV"""
        rows = data.get("rows", [])
        columns = data.get("columns", [])

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

        # 保存到文件系统或 S3
        export_path = f"/tmp/reports/{filename}.csv"
        with open(export_path, "w", encoding="utf-8") as f:
            f.write(output.getvalue())

        return export_path

    # ==================== 报表管理 ====================

    def create_report(
        self,
        name: str,
        report_type: str,
        data_source: Dict[str, Any],
        *,
        code: str = None,
        description: str = None,
        layout: Dict[str, Any] = None,
        parameters: List[Dict[str, Any]] = None,
        is_public: bool = False,
        user_id: int = None,
    ) -> ReportDefinition:
        """创建报表定义"""
        report = ReportDefinition(
            id=str(uuid.uuid4()),
            name=name,
            code=code or f"RPT-{uuid.uuid4().hex[:8].upper()}",
            description=description,
            report_type=report_type,
            data_source=data_source,
            layout=layout,
            parameters=parameters,
            is_public=is_public,
            owner_id=user_id,
            created_by_id=user_id,
        )
        self.session.add(report)
        self.session.flush()
        return report

    def get_standard_reports(self) -> List[Dict[str, Any]]:
        """获取预定义的标准报表列表"""
        return [
            {
                "id": "items_by_state",
                "name": "Items by State",
                "description": "Count of items grouped by state",
                "type": "chart",
            },
            {
                "id": "recent_changes",
                "name": "Recent Changes",
                "description": "Items changed in the last 30 days",
                "type": "table",
            },
            {
                "id": "dedup_summary",
                "name": "Deduplication Summary",
                "description": "Summary of duplicate detection results",
                "type": "dashboard",
            },
            {
                "id": "bom_cost_rollup",
                "name": "BOM Cost Rollup",
                "description": "Cost summary by BOM level",
                "type": "pivot",
            },
        ]
```

---

## 7. Phase 6: 电子签名

### 7.1 目标

实现符合 21 CFR Part 11 / EU Annex 11 的电子签名功能，支持审批签名、意义声明和审计追踪。

### 7.2 数据模型

#### `src/yuantus/meta_engine/esign/models.py`

```python
"""
电子签名数据模型
符合 21 CFR Part 11 / EU Annex 11
"""
from sqlalchemy import (
    Column, String, Integer, ForeignKey, DateTime,
    Boolean, Text, JSON, LargeBinary
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from yuantus.models.base import Base


class SignatureMeaning(str, enum.Enum):
    """签名意义"""
    AUTHORED = "authored"           # 作者
    REVIEWED = "reviewed"           # 审核
    APPROVED = "approved"           # 批准
    RELEASED = "released"           # 发布
    VERIFIED = "verified"           # 验证
    REJECTED = "rejected"           # 拒绝
    ACKNOWLEDGED = "acknowledged"   # 确认
    WITNESSED = "witnessed"         # 见证


class SignatureStatus(str, enum.Enum):
    """签名状态"""
    VALID = "valid"
    REVOKED = "revoked"
    EXPIRED = "expired"


class SigningReason(Base):
    """
    签名原因定义
    预定义的签名意义和说明
    """
    __tablename__ = "meta_signing_reasons"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 原因标识
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # 签名意义
    meaning = Column(String, default=SignatureMeaning.APPROVED.value)

    # 法规要求
    regulatory_reference = Column(String, nullable=True)  # 如 "21 CFR Part 11"

    # 适用的 ItemType（为空表示全局）
    item_type_id = Column(String, ForeignKey("meta_item_types.id"), nullable=True)

    # 适用的状态转换
    from_state = Column(String, nullable=True)
    to_state = Column(String, nullable=True)

    # 是否需要密码确认
    requires_password = Column(Boolean, default=True)

    # 是否需要评论
    requires_comment = Column(Boolean, default=False)

    # 排序
    sequence = Column(Integer, default=0)

    # 状态
    is_active = Column(Boolean, default=True)

    # 审计
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ElectronicSignature(Base):
    """
    电子签名记录
    不可变的签名证据
    """
    __tablename__ = "meta_electronic_signatures"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 签名对象
    item_id = Column(String, ForeignKey("meta_items.id"), nullable=False, index=True)
    item_generation = Column(Integer, nullable=False)  # 签名时的版本

    # 签名者
    signer_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=False)
    signer_username = Column(String, nullable=False)  # 快照
    signer_full_name = Column(String, nullable=False)  # 快照

    # 签名意义
    reason_id = Column(String, ForeignKey("meta_signing_reasons.id"), nullable=True)
    meaning = Column(String, nullable=False)
    reason_text = Column(String)  # 签名原因文本

    # 用户评论
    comment = Column(Text, nullable=True)

    # 签名时间
    signed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 签名验证
    signature_hash = Column(String, nullable=False)  # 签名哈希
    content_hash = Column(String, nullable=False)    # 签名内容哈希

    # 客户端信息
    client_ip = Column(String, nullable=True)
    client_info = Column(JSON().with_variant(JSONB, "postgresql"))  # 浏览器、设备等

    # 状态
    status = Column(String, default=SignatureStatus.VALID.value)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    revocation_reason = Column(Text, nullable=True)

    # 关联的工作流（如果通过工作流签名）
    workflow_instance_id = Column(String, nullable=True)
    workflow_activity_id = Column(String, nullable=True)


class SignatureManifest(Base):
    """
    签名清单
    记录一个 Item 版本的所有签名
    """
    __tablename__ = "meta_signature_manifests"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 签名对象
    item_id = Column(String, ForeignKey("meta_items.id"), nullable=False, index=True)
    item_generation = Column(Integer, nullable=False)

    # 签名要求
    required_signatures = Column(JSON().with_variant(JSONB, "postgresql"))
    # 格式: [
    #     {"meaning": "reviewed", "role": "Engineer", "required": true},
    #     {"meaning": "approved", "role": "Manager", "required": true}
    # ]

    # 完成状态
    is_complete = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # 清单哈希（用于验证完整性）
    manifest_hash = Column(String, nullable=True)

    # 审计
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SignatureAuditLog(Base):
    """
    签名审计日志
    记录所有签名相关操作
    """
    __tablename__ = "meta_signature_audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 操作类型
    action = Column(String, nullable=False)  # sign, verify, revoke, export

    # 关联签名
    signature_id = Column(String, ForeignKey("meta_electronic_signatures.id"), nullable=True)

    # 关联 Item
    item_id = Column(String, ForeignKey("meta_items.id"), nullable=True)

    # 操作者
    actor_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=False)
    actor_username = Column(String, nullable=False)

    # 操作详情
    details = Column(JSON().with_variant(JSONB, "postgresql"))

    # 结果
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

    # 时间戳
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # 客户端信息
    client_ip = Column(String, nullable=True)
```

### 7.3 服务层

#### `src/yuantus/meta_engine/esign/service.py`

```python
"""
电子签名服务
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import hashlib
import hmac
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_

from yuantus.meta_engine.esign.models import (
    ElectronicSignature, SigningReason, SignatureManifest,
    SignatureAuditLog, SignatureMeaning, SignatureStatus
)
from yuantus.meta_engine.models.item import Item

logger = logging.getLogger(__name__)


class ElectronicSignatureService:
    """电子签名服务"""

    def __init__(self, session: Session, secret_key: str):
        self.session = session
        self.secret_key = secret_key

    def sign(
        self,
        item_id: str,
        user_id: int,
        meaning: str,
        *,
        password: str = None,
        reason_id: str = None,
        reason_text: str = None,
        comment: str = None,
        client_ip: str = None,
        client_info: Dict[str, Any] = None,
        workflow_instance_id: str = None,
        workflow_activity_id: str = None,
    ) -> ElectronicSignature:
        """
        签署 Item

        Args:
            item_id: Item ID
            user_id: 签名者用户 ID
            meaning: 签名意义
            password: 用户密码（用于验证）
            reason_id: 签名原因 ID
            reason_text: 签名原因文本
            comment: 用户评论
        """
        # 获取 Item
        item = self.session.get(Item, item_id)
        if not item:
            raise ValueError(f"Item not found: {item_id}")

        # 获取用户
        from yuantus.meta_engine.models.user import User
        user = self.session.get(User, user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        # 验证密码
        if password:
            if not self._verify_password(user, password):
                self._log_audit(
                    "sign",
                    item_id=item_id,
                    actor_id=user_id,
                    actor_username=user.username,
                    success=False,
                    error_message="Invalid password",
                    client_ip=client_ip,
                )
                raise ValueError("Invalid password")

        # 获取签名原因
        if reason_id:
            reason = self.session.get(SigningReason, reason_id)
            if reason:
                reason_text = reason_text or reason.name
                if reason.requires_password and not password:
                    raise ValueError("Password required for this signature type")

        # 计算哈希
        content_hash = self._calculate_content_hash(item)
        signature_hash = self._calculate_signature_hash(
            item_id=item.id,
            item_generation=item.generation,
            user_id=user_id,
            meaning=meaning,
            content_hash=content_hash,
            timestamp=datetime.utcnow(),
        )

        # 创建签名记录
        signature = ElectronicSignature(
            id=str(uuid.uuid4()),
            item_id=item.id,
            item_generation=item.generation,
            signer_id=user_id,
            signer_username=user.username,
            signer_full_name=getattr(user, 'full_name', user.username),
            reason_id=reason_id,
            meaning=meaning,
            reason_text=reason_text,
            comment=comment,
            signature_hash=signature_hash,
            content_hash=content_hash,
            client_ip=client_ip,
            client_info=client_info,
            workflow_instance_id=workflow_instance_id,
            workflow_activity_id=workflow_activity_id,
        )
        self.session.add(signature)
        self.session.flush()

        # 更新清单
        self._update_manifest(item.id, item.generation)

        # 审计日志
        self._log_audit(
            "sign",
            signature_id=signature.id,
            item_id=item_id,
            actor_id=user_id,
            actor_username=user.username,
            details={
                "meaning": meaning,
                "reason": reason_text,
            },
            client_ip=client_ip,
        )

        return signature

    def verify(self, signature_id: str) -> Dict[str, Any]:
        """
        验证签名有效性
        """
        signature = self.session.get(ElectronicSignature, signature_id)
        if not signature:
            raise ValueError(f"Signature not found: {signature_id}")

        # 获取当前 Item
        item = self.session.get(Item, signature.item_id)

        issues = []
        is_valid = True

        # 检查签名状态
        if signature.status != SignatureStatus.VALID.value:
            is_valid = False
            issues.append(f"Signature status is {signature.status}")

        # 验证内容哈希（检查 Item 是否被修改）
        if item and item.generation == signature.item_generation:
            current_hash = self._calculate_content_hash(item)
            if current_hash != signature.content_hash:
                is_valid = False
                issues.append("Content has been modified since signing")

        # 验证签名哈希
        expected_hash = self._calculate_signature_hash(
            item_id=signature.item_id,
            item_generation=signature.item_generation,
            user_id=signature.signer_id,
            meaning=signature.meaning,
            content_hash=signature.content_hash,
            timestamp=signature.signed_at,
        )
        if expected_hash != signature.signature_hash:
            is_valid = False
            issues.append("Signature hash mismatch - possible tampering")

        # 审计
        self._log_audit(
            "verify",
            signature_id=signature_id,
            item_id=signature.item_id,
            actor_id=signature.signer_id,
            actor_username=signature.signer_username,
            details={"is_valid": is_valid, "issues": issues},
        )

        return {
            "signature_id": signature_id,
            "is_valid": is_valid,
            "issues": issues,
            "signature": {
                "id": signature.id,
                "signer": signature.signer_full_name,
                "meaning": signature.meaning,
                "signed_at": signature.signed_at.isoformat(),
                "status": signature.status,
            },
        }

    def revoke(
        self,
        signature_id: str,
        revoked_by_id: int,
        reason: str,
    ) -> ElectronicSignature:
        """
        撤销签名
        """
        signature = self.session.get(ElectronicSignature, signature_id)
        if not signature:
            raise ValueError(f"Signature not found: {signature_id}")

        if signature.status == SignatureStatus.REVOKED.value:
            raise ValueError("Signature is already revoked")

        signature.status = SignatureStatus.REVOKED.value
        signature.revoked_at = datetime.utcnow()
        signature.revoked_by_id = revoked_by_id
        signature.revocation_reason = reason
        self.session.add(signature)

        # 审计
        from yuantus.meta_engine.models.user import User
        revoker = self.session.get(User, revoked_by_id)

        self._log_audit(
            "revoke",
            signature_id=signature_id,
            item_id=signature.item_id,
            actor_id=revoked_by_id,
            actor_username=revoker.username if revoker else "unknown",
            details={"reason": reason},
        )

        return signature

    def get_signatures(
        self,
        item_id: str,
        generation: int = None,
        *,
        include_revoked: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        获取 Item 的签名列表
        """
        query = self.session.query(ElectronicSignature).filter(
            ElectronicSignature.item_id == item_id
        )

        if generation is not None:
            query = query.filter(ElectronicSignature.item_generation == generation)

        if not include_revoked:
            query = query.filter(ElectronicSignature.status == SignatureStatus.VALID.value)

        signatures = query.order_by(ElectronicSignature.signed_at).all()

        return [
            {
                "id": s.id,
                "signer_id": s.signer_id,
                "signer_name": s.signer_full_name,
                "meaning": s.meaning,
                "reason": s.reason_text,
                "comment": s.comment,
                "signed_at": s.signed_at.isoformat(),
                "status": s.status,
                "item_generation": s.item_generation,
            }
            for s in signatures
        ]

    def _calculate_content_hash(self, item: Item) -> str:
        """计算 Item 内容哈希"""
        content = f"{item.id}:{item.generation}:{item.config_id}:{item.state}"
        if item.properties:
            import json
            content += ":" + json.dumps(item.properties, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def _calculate_signature_hash(
        self,
        item_id: str,
        item_generation: int,
        user_id: int,
        meaning: str,
        content_hash: str,
        timestamp: datetime,
    ) -> str:
        """计算签名哈希（HMAC）"""
        message = f"{item_id}:{item_generation}:{user_id}:{meaning}:{content_hash}:{timestamp.isoformat()}"
        return hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

    def _verify_password(self, user, password: str) -> bool:
        """验证用户密码"""
        # 实际实现应该使用安全的密码验证
        # 这里简化处理
        if hasattr(user, 'check_password'):
            return user.check_password(password)
        return True  # 开发环境

    def _update_manifest(self, item_id: str, generation: int) -> None:
        """更新签名清单"""
        manifest = self.session.query(SignatureManifest).filter(
            SignatureManifest.item_id == item_id,
            SignatureManifest.item_generation == generation,
        ).first()

        if not manifest:
            return

        # 获取所有有效签名
        signatures = self.session.query(ElectronicSignature).filter(
            ElectronicSignature.item_id == item_id,
            ElectronicSignature.item_generation == generation,
            ElectronicSignature.status == SignatureStatus.VALID.value,
        ).all()

        # 检查是否满足要求
        required = manifest.required_signatures or []
        signed_meanings = {s.meaning for s in signatures}

        is_complete = all(
            req.get("meaning") in signed_meanings
            for req in required
            if req.get("required", False)
        )

        if is_complete and not manifest.is_complete:
            manifest.is_complete = True
            manifest.completed_at = datetime.utcnow()
            self.session.add(manifest)

    def _log_audit(
        self,
        action: str,
        *,
        signature_id: str = None,
        item_id: str = None,
        actor_id: int,
        actor_username: str,
        details: Dict[str, Any] = None,
        success: bool = True,
        error_message: str = None,
        client_ip: str = None,
    ) -> None:
        """记录审计日志"""
        log = SignatureAuditLog(
            id=str(uuid.uuid4()),
            action=action,
            signature_id=signature_id,
            item_id=item_id,
            actor_id=actor_id,
            actor_username=actor_username,
            details=details,
            success=success,
            error_message=error_message,
            client_ip=client_ip,
        )
        self.session.add(log)

    # ==================== 签名原因管理 ====================

    def create_signing_reason(
        self,
        code: str,
        name: str,
        meaning: str,
        *,
        description: str = None,
        regulatory_reference: str = None,
        requires_password: bool = True,
        requires_comment: bool = False,
        item_type_id: str = None,
        from_state: str = None,
        to_state: str = None,
    ) -> SigningReason:
        """创建签名原因"""
        reason = SigningReason(
            id=str(uuid.uuid4()),
            code=code,
            name=name,
            meaning=meaning,
            description=description,
            regulatory_reference=regulatory_reference,
            requires_password=requires_password,
            requires_comment=requires_comment,
            item_type_id=item_type_id,
            from_state=from_state,
            to_state=to_state,
        )
        self.session.add(reason)
        self.session.flush()
        return reason

    def get_applicable_reasons(
        self,
        item_type_id: str = None,
        from_state: str = None,
        to_state: str = None,
    ) -> List[SigningReason]:
        """获取适用的签名原因"""
        query = self.session.query(SigningReason).filter(
            SigningReason.is_active == True
        )

        # 过滤条件
        conditions = [SigningReason.item_type_id.is_(None)]
        if item_type_id:
            conditions.append(SigningReason.item_type_id == item_type_id)

        query = query.filter(or_(*conditions))

        if from_state:
            query = query.filter(
                or_(
                    SigningReason.from_state.is_(None),
                    SigningReason.from_state == from_state
                )
            )

        if to_state:
            query = query.filter(
                or_(
                    SigningReason.to_state.is_(None),
                    SigningReason.to_state == to_state
                )
            )

        return query.order_by(SigningReason.sequence).all()

    # ==================== 清单管理 ====================

    def create_manifest(
        self,
        item_id: str,
        generation: int,
        required_signatures: List[Dict[str, Any]],
    ) -> SignatureManifest:
        """创建签名清单"""
        manifest = SignatureManifest(
            id=str(uuid.uuid4()),
            item_id=item_id,
            item_generation=generation,
            required_signatures=required_signatures,
        )
        self.session.add(manifest)
        self.session.flush()
        return manifest

    def get_manifest_status(
        self,
        item_id: str,
        generation: int = None,
    ) -> Optional[Dict[str, Any]]:
        """获取签名清单状态"""
        item = self.session.get(Item, item_id)
        if not item:
            return None

        gen = generation or item.generation

        manifest = self.session.query(SignatureManifest).filter(
            SignatureManifest.item_id == item_id,
            SignatureManifest.item_generation == gen,
        ).first()

        if not manifest:
            return None

        # 获取已有签名
        signatures = self.get_signatures(item_id, gen)
        signed_meanings = {s["meaning"] for s in signatures}

        # 计算状态
        required = manifest.required_signatures or []
        status_list = []
        for req in required:
            meaning = req.get("meaning")
            status_list.append({
                "meaning": meaning,
                "role": req.get("role"),
                "required": req.get("required", False),
                "signed": meaning in signed_meanings,
                "signature": next(
                    (s for s in signatures if s["meaning"] == meaning),
                    None
                ),
            })

        return {
            "manifest_id": manifest.id,
            "item_id": item_id,
            "generation": gen,
            "is_complete": manifest.is_complete,
            "completed_at": manifest.completed_at.isoformat() if manifest.completed_at else None,
            "requirements": status_list,
        }
```

---

## 8. 数据库迁移计划

### 8.1 迁移执行顺序

```bash
# 1. Phase 1: 去重表
alembic upgrade p1_dedup_001

# 2. Phase 2: 配置管理表
alembic upgrade p2_config_001

# 3. Phase 3: 制造表
alembic upgrade p3_mfg_001

# 4. Phase 4: 基线表
alembic upgrade p4_baseline_001

# 5. Phase 5: 报表表
alembic upgrade p5_reports_001

# 6. Phase 6: 电子签名表
alembic upgrade p6_esign_001
```

### 8.2 回滚策略

```bash
# 回滚到特定版本
alembic downgrade <revision>

# 回滚上一步
alembic downgrade -1
```

---

## 9. 验证计划

### 9.1 单元测试

每个 Phase 需要完成以下测试：

```python
# tests/meta_engine/test_dedup_service.py
# tests/meta_engine/test_configuration_service.py
# tests/meta_engine/test_mbom_service.py
# tests/meta_engine/test_routing_service.py
# tests/meta_engine/test_baseline_service.py
# tests/meta_engine/test_search_service.py
# tests/meta_engine/test_report_service.py
# tests/meta_engine/test_esign_service.py
```

### 9.2 集成测试

```python
# tests/integration/test_dedup_workflow.py
# tests/integration/test_configuration_bom.py
# tests/integration/test_mbom_routing.py
# tests/integration/test_baseline_eco.py
# tests/integration/test_esign_workflow.py
```

### 9.3 性能测试

| 场景 | 目标 |
|------|------|
| 去重批量处理 1000 文件 | < 10 分钟 |
| 配置 BOM 计算 (500 层级) | < 5 秒 |
| MBOM 转换 (1000 行) | < 30 秒 |
| 基线创建 (2000 成员) | < 1 分钟 |
| 全文搜索响应 | < 500ms |
| 电子签名验证 | < 100ms |

---

## 10. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| ES 集群不可用 | 搜索功能降级 | 提供 SQL 降级方案 |
| 签名密钥泄露 | 安全风险 | HSM 集成 + 密钥轮换 |
| 数据迁移失败 | 数据丢失 | 完整备份 + 回滚脚本 |
| 性能不达标 | 用户体验差 | 预发布性能测试 |

---

