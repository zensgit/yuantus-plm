from sqlalchemy import (
    Column,
    String,
    Integer,
    ForeignKey,
    DateTime,
    Boolean,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from yuantus.models.base import Base
from yuantus.security.rbac.models import RBACUser
from yuantus.meta_engine.version.models import ItemVersion


class Item(Base):
    """
    万能对象表 (Single Table Inheritance 的变种)
    系统中所有的业务对象实例都存在这张表里。
    """

    __tablename__ = "meta_items"

    id = Column(String, primary_key=True)  # UUID

    # 核心元数据
    item_type_id = Column(String, ForeignKey("meta_item_types.id"), index=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 版本控制核心字段
    # config_id: 哪怕升版了，同一个对象的 config_id 永远不变 (Master ID)
    config_id = Column(String, index=True, nullable=False)
    generation = Column(Integer, default=1)  # 1, 2, 3...
    is_current = Column(Boolean, default=True)  # 只有最新版是 True [优化查询]

    state = Column(String)  # 生命周期状态 "Draft", "Released"
    current_state = Column(
        String, ForeignKey("meta_lifecycle_states.id"), nullable=True
    )  # 状态 ID

    # Version Control Integration
    is_versionable = Column(Boolean, default=True)
    # Circular dependency handled by use_alter=True
    current_version_id = Column(
        String,
        ForeignKey(
            "meta_item_versions.id", use_alter=True, name="fk_item_current_version"
        ),
        nullable=True,
    )

    # 新增审计字段
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("rbac_users.id", ondelete="SET NULL"), nullable=True
    )
    modified_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("rbac_users.id", ondelete="SET NULL"), nullable=True
    )
    owner_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("rbac_users.id", ondelete="SET NULL"), nullable=True
    )
    locked_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("rbac_users.id", ondelete="SET NULL"), nullable=True
    )

    # 关系
    created_by: Mapped[Optional["RBACUser"]] = relationship(
        "RBACUser", foreign_keys=[created_by_id]
    )
    modified_by: Mapped[Optional["RBACUser"]] = relationship(
        "RBACUser", foreign_keys=[modified_by_id]
    )
    owner: Mapped[Optional["RBACUser"]] = relationship(
        "RBACUser", foreign_keys=[owner_id]
    )
    permission_id = Column(String, nullable=True)

    # 关系专用字段 (仅 ItemType.is_relationship=True 时使用)
    # 实现了 "关系也是对象"
    source_id = Column(String, ForeignKey("meta_items.id"), index=True, nullable=True)
    related_id = Column(String, ForeignKey("meta_items.id"), index=True, nullable=True)
    # 动态属性 (JSONB)
    properties = Column(JSON().with_variant(JSONB, "postgresql"), default={})

    # Relationships
    versions = relationship(
        ItemVersion,
        backref="item",  # This backref is sufficient, avoiding circular import in ItemVersion
        foreign_keys=[ItemVersion.item_id],
        cascade="all, delete-orphan",
        order_by=[ItemVersion.generation, ItemVersion.revision],
    )

    current_version = relationship(
        "ItemVersion", foreign_keys=[current_version_id], post_update=True
    )

    def to_dict(self) -> dict:
        """Convert item to dictionary, merging static fields and dynamic properties"""
        data = {
            "id": self.id,
            "item_type_id": self.item_type_id,
            "config_id": self.config_id,
            "generation": self.generation,
            "is_current": self.is_current,
            "state": self.state,
            "current_state": self.current_state,
            "current_version_id": self.current_version_id,
            "created_by_id": self.created_by_id,
            "created_on": self.created_at.isoformat() if self.created_at else None,
            "modified_by_id": self.modified_by_id,
            "modified_on": self.updated_at.isoformat() if self.updated_at else None,
            "owner_id": self.owner_id,
            "permission_id": self.permission_id,
            "source_id": self.source_id,
            "related_id": self.related_id,
        }
        # Merge dynamic properties
        if self.properties:
            data.update(self.properties)
        return data
