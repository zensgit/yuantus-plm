"""
Generic Relationship Model (Deprecated for writes)

关系现在以 Item 形式存储在 meta_items 中（source_id/related_id）。
meta_relationships 仅保留为兼容层（只读）。
"""

from sqlalchemy import ForeignKey, String, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional, Dict, Any

from yuantus.models.base import Base  # Use the unified Base
from yuantus.meta_engine.models.item import (
    Item,
)  # For type hinting the relationship. This could be a circular import if Item imports back from here. Using string forward references might be safer if that happens.
from sqlalchemy import event
import os
import logging

logger = logging.getLogger(__name__)


class RelationshipType(Base):
    """
    关系类型定义
    定义source_type -> related_type的关系
    """

    __tablename__ = "meta_relationship_types"  # Use meta_ prefix for consistency

    id: Mapped[str] = mapped_column(
        String, primary_key=True
    )  # Assuming string ID for meta types
    name: Mapped[str] = mapped_column(String(100), unique=True)
    label: Mapped[str] = mapped_column(String(200))

    # 源和目标ItemType
    source_item_type: Mapped[str] = mapped_column(String(100), comment="源ItemType名称")
    related_item_type: Mapped[str] = mapped_column(
        String(100), comment="目标ItemType名称"
    )

    # 关系特性
    is_polymorphic: Mapped[bool] = mapped_column(
        default=False, comment="是否允许多态（related可以是子类型）"
    )
    cascade_delete: Mapped[bool] = mapped_column(
        default=False, comment="删除source时是否级联删除关系"
    )
    max_quantity: Mapped[Optional[int]] = mapped_column(
        nullable=True, comment="最大关系数量，null表示无限"
    )

    # 关系自身的属性定义（JSONB）
    property_definitions: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,  # Use SQLAlchemy JSON type, for PostgreSQL it will map to JSONB
        nullable=True,
        comment="关系自身的属性定义",
    )

    # 关系是否有自己的生命周期
    lifecycle_map_id: Mapped[Optional[str]] = (
        mapped_column(  # FK to meta_lifecycle_maps.id (String)
            ForeignKey("meta_lifecycle_maps.id"), nullable=True
        )
    )
    # relationship to LifecycleMap is usually managed in LifecycleMap side if bidirectional.
    # Here, unidirectional from RelationshipType to LifecycleMap.


class Relationship(Base):
    """
    通用关系实例
    关系本身是一个Item，可以有属性和生命周期

    NOTE:
    - meta_relationships 已标记为兼容只读层（Deprecated for writes）
    - 新关系请写入 meta_items（ItemType.is_relationship=True）
    """

    __tablename__ = "meta_relationships"  # Use meta_ prefix for consistency

    id: Mapped[str] = mapped_column(
        String, primary_key=True
    )  # Assuming string ID for meta items

    # 关系类型
    relationship_type_id: Mapped[str] = (
        mapped_column(  # FK to meta_relationship_types.id (String)
            ForeignKey("meta_relationship_types.id")
        )
    )
    relationship_type: Mapped["RelationshipType"] = relationship("RelationshipType")

    # 源和目标
    source_id: Mapped[str] = mapped_column(  # FK to meta_items.id (String)
        ForeignKey("meta_items.id", ondelete="CASCADE"), index=True
    )
    related_id: Mapped[str] = mapped_column(  # FK to meta_items.id (String)
        ForeignKey("meta_items.id", ondelete="CASCADE"), index=True
    )

    # 关系属性（如BOM中的数量、CAD文件类型等）
    properties: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True  # Use SQLAlchemy JSON type
    )

    # 排序
    sort_order: Mapped[int] = mapped_column(default=0)

    # 关系自己的状态（如果有生命周期）
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # 审计
    created_by_id: Mapped[Optional[int]] = (
        mapped_column(  # FK to rbac_users.id (Integer)
            ForeignKey("rbac_users.id"), nullable=True
        )
    )

    # 关系 (Use string for forward references if not imported at top)
    source_item: Mapped["Item"] = relationship(
        "Item",  # Forward reference to Item
        foreign_keys=[source_id],
        backref="outgoing_relationships",
    )
    related_item: Mapped["Item"] = relationship(
        "Item",  # Forward reference to Item
        foreign_keys=[related_id],
        backref="incoming_relationships",
    )


def _relationship_readonly_enabled() -> bool:
    return os.getenv("YUANTUS_RELATIONSHIP_READONLY", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _block_relationship_write(operation: str, target: "Relationship") -> None:
    if _relationship_readonly_enabled():
        logger.error(
            "Blocked %s on meta_relationships (deprecated). "
            "relationship_id=%s source_id=%s related_id=%s",
            operation,
            getattr(target, "id", None),
            getattr(target, "source_id", None),
            getattr(target, "related_id", None),
        )
        raise RuntimeError(
            "meta_relationships is deprecated for writes; "
            "use meta_items relationship items instead."
        )


def _block_insert(mapper, connection, target: "Relationship") -> None:  # pragma: no cover
    _block_relationship_write("insert", target)


def _block_update(mapper, connection, target: "Relationship") -> None:  # pragma: no cover
    _block_relationship_write("update", target)


def _block_delete(mapper, connection, target: "Relationship") -> None:  # pragma: no cover
    _block_relationship_write("delete", target)


event.listen(Relationship, "before_insert", _block_insert)
event.listen(Relationship, "before_update", _block_update)
event.listen(Relationship, "before_delete", _block_delete)
