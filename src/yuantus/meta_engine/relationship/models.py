"""
Generic Relationship Model
关系作为一等公民Item
Phase 3.1
"""

from sqlalchemy import ForeignKey, String, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional, Dict, Any

from yuantus.models.base import Base  # Use the unified Base
from yuantus.meta_engine.models.item import (
    Item,
)  # For type hinting the relationship. This could be a circular import if Item imports back from here. Using string forward references might be safer if that happens.


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
