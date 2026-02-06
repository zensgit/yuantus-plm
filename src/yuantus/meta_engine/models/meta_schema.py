import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, JSON, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from yuantus.models.base import Base

# Ensure LifecycleMap is registered for ItemType.lifecycle_map relationship.
# Some unit tests instantiate mapped models without going through init_db(),
# so we need the class to be importable at mapper configuration time.
from yuantus.meta_engine.lifecycle.models import LifecycleMap  # noqa: F401


class ItemType(Base):
    """
    元模型定义表：定义系统中有哪些类型的对象
    e.g. "Part", "Document", "Part BOM"
    """

    __tablename__ = "meta_item_types"
    id = Column(String, primary_key=True)  # Name as ID: "Part"
    label = Column(String)
    description = Column(String)
    uuid = Column(
        String, default=lambda: str(uuid.uuid4()), comment="Stable UUID for ItemType"
    )

    # 核心标志位
    is_relationship = Column(Boolean, default=False)
    is_versionable = Column(Boolean, default=True)
    version_control_enabled = Column(
        Boolean, default=True
    )  # Alias or distinct? Using distinct as per design
    revision_scheme = Column(
        String(50), default="A-Z", comment="Revisioning scheme (e.g., A-Z, 1.2.3)"
    )

    permission_id = Column(String, nullable=True)
    lifecycle_map_id = Column(
        String, ForeignKey("meta_lifecycle_maps.id"), nullable=True
    )

    # Schema and Methods (JSON storage)
    properties_schema = Column(
        JSON().with_variant(JSONB, "postgresql"),
        comment="JSON Schema definition of properties",
    )

    ui_layout = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        comment="UI layout configuration (Form, List, Search)",
    )

    methods = Column(
        JSON().with_variant(JSONB, "postgresql"),
        comment="Server-side method definitions",
    )

    on_before_add_method_id = Column(String, nullable=True)
    on_after_update_method_id = Column(String, nullable=True)

    # 关系定义 (仅当 is_relationship=True 时有效)
    # 定义该关系连接的源类型和目标类型
    source_item_type_id = Column(
        String, ForeignKey("meta_item_types.id"), nullable=True
    )
    related_item_type_id = Column(
        String, ForeignKey("meta_item_types.id"), nullable=True
    )

    # 关联属性定义
    properties = relationship(
        "Property",
        back_populates="item_type",
        cascade="all, delete-orphan",
        foreign_keys="Property.item_type_id",
    )
    lifecycle_map = relationship("LifecycleMap", foreign_keys=[lifecycle_map_id])
    # permission = relationship("Permission", foreign_keys=[permission_id])


class Property(Base):
    """
    属性定义表：定义 ItemType 有哪些字段
    e.g. Part.cost, Part.weight
    """

    __tablename__ = "meta_properties"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))  # UUID
    item_type_id = Column(String, ForeignKey("meta_item_types.id"))

    name = Column(String, nullable=False)  # "cost"
    label = Column(String)  # "Cost ($)"

    # 数据类型: string, integer, float, boolean, date, item, list, json
    data_type = Column(String, default="string")

    length = Column(Integer)
    is_required = Column(Boolean, default=False)
    default_value = Column(String)

    # 新增 UI 相关元数据
    ui_type = Column(String(50), default="text", comment="Frontend UI widget type")
    ui_options = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        comment="Frontend UI widget options",
    )
    is_cad_synced = Column(
        Boolean, default=False, comment="True if this property is synced from CAD data"
    )
    default_value_expression = Column(
        Text, nullable=True, comment="Expression for dynamic default value"
    )

    # 如果 data_type="item"，这里指向关联的 ItemType ID (外键定义)
    data_source_id = Column(String, ForeignKey("meta_item_types.id"), nullable=True)

    item_type = relationship(
        "ItemType", back_populates="properties", foreign_keys=[item_type_id]
    )


# Alias for backward compatibility
PropertyDefinition = Property
