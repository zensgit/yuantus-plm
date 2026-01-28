"""
Relationship Service
关系管理服务
Phase 3.2
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from yuantus.config import get_settings
from yuantus.meta_engine.relationship.models import RelationshipType
from yuantus.meta_engine.models.item import Item  # Item model for relationship edges.
from yuantus.meta_engine.models.meta_schema import ItemType

logger = logging.getLogger(__name__)


class RelationshipService:
    """关系管理服务"""

    def __init__(self, session: Session):
        self.session = session
        self._relationship_item_type_cache: Dict[str, ItemType] = {}

    def _resolve_relationship_type(
        self, name: str
    ) -> tuple[Optional[RelationshipType], ItemType]:
        settings = get_settings()
        item_type = (
            self.session.query(ItemType)
            .filter((ItemType.id == name) | (ItemType.label == name))
            .first()
        )
        if item_type and item_type.is_relationship:
            cached = self._relationship_item_type_cache.get(item_type.id)
            if cached is not None:
                return None, cached
            self._relationship_item_type_cache[item_type.id] = item_type
            return None, item_type

        if not settings.RELATIONSHIP_TYPE_LEGACY_SEED_ENABLED:
            if item_type:
                raise ValueError(f"{name} is not a relationship ItemType")
            raise ValueError(
                f"Unknown relationship type: {name}. "
                "Legacy RelationshipType lookup is disabled."
            )

        rel_type = (
            self.session.query(RelationshipType)
            .filter((RelationshipType.name == name) | (RelationshipType.id == name))
            .first()
        )
        if rel_type:
            logger.warning(
                "RelationshipType %s is deprecated; use ItemType.is_relationship "
                "(legacy mode enabled).",
                rel_type.name,
            )
            item_type_id = rel_type.name
            cached = self._relationship_item_type_cache.get(item_type_id)
            if cached is not None:
                return rel_type, cached

            item_type = (
                self.session.query(ItemType)
                .filter(ItemType.id == item_type_id)
                .first()
            )
            if not item_type:
                item_type = ItemType(
                    id=item_type_id,
                    label=rel_type.label or rel_type.name,
                    is_relationship=True,
                    source_item_type_id=rel_type.source_item_type,
                    related_item_type_id=rel_type.related_item_type,
                )
                self.session.add(item_type)
                self.session.flush()
            else:
                if not item_type.is_relationship:
                    item_type.is_relationship = True
                if not item_type.source_item_type_id:
                    item_type.source_item_type_id = rel_type.source_item_type
                if not item_type.related_item_type_id:
                    item_type.related_item_type_id = rel_type.related_item_type

            self._relationship_item_type_cache[item_type_id] = item_type
            return rel_type, item_type

        if item_type:
            raise ValueError(f"{name} is not a relationship ItemType")
        raise ValueError(f"Unknown relationship type: {name}")

    def create_relationship(
        self,
        source_id: str,  # Item IDs are string
        related_id: str,  # Item IDs are string
        relationship_type_name: str,  # Changed from relationship_type to relationship_type_name to avoid confusion
        properties: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> Item:
        """
        创建关系

        Args:
            source_id: 源Item ID
            related_id: 目标Item ID
            relationship_type_name: 关系类型名称
            properties: 关系属性
            user_id: 创建者

        Returns:
            创建的关系实例
        """
        rel_type, rel_item_type = self._resolve_relationship_type(relationship_type_name)

        source_type_id = (
            rel_type.source_item_type
            if rel_type
            else rel_item_type.source_item_type_id
        )
        related_type_id = (
            rel_type.related_item_type
            if rel_type
            else rel_item_type.related_item_type_id
        )
        is_polymorphic = rel_type.is_polymorphic if rel_type else False
        max_quantity = rel_type.max_quantity if rel_type else None

        # 验证源和目标类型
        source = self.session.get(Item, source_id)
        related = self.session.get(Item, related_id)

        if not source or not related:
            raise ValueError("Source or related item not found")

        if source_type_id and source.item_type_id != source_type_id:
            raise ValueError(
                f"Source type mismatch: expected {source_type_id}, "
                f"got {source.item_type_id}"
            )

        # Handle polymorphic relationships
        if not is_polymorphic and related_type_id:
            if related.item_type_id != related_type_id:
                raise ValueError(
                    f"Related type mismatch: expected {related_type_id}, "
                    f"got {related.item_type_id}"
                )
        # If polymorphic, we might need a more complex check here,
        # e.g., checking inheritance tree, but for now strict type or no check.

        # 检查数量限制
        if max_quantity is not None:
            existing_count = (
                self.session.query(Item)
                .filter(
                    Item.source_id == source_id,
                    Item.item_type_id == rel_item_type.id,
                    Item.is_current.is_(True),
                )
                .count()
            )

            if existing_count >= max_quantity:
                raise ValueError(
                    f"Max relationship quantity ({max_quantity}) exceeded"
                )

        # 创建关系 (关系即 Item)
        import uuid

        relationship = Item(
            id=str(uuid.uuid4()),
            item_type_id=rel_item_type.id,
            config_id=str(uuid.uuid4()),
            generation=1,
            is_current=True,
            state="Active",
            source_id=source_id,
            related_id=related_id,
            properties=properties or {},
            created_by_id=user_id,
            permission_id=source.permission_id,
        )

        self.session.add(relationship)
        self.session.flush()  # Flush to get ID for newly created relationship (Item)

        return relationship

    def get_relationships(
        self,
        item_id: str,  # Item IDs are string
        direction: str = "outgoing",  # outgoing|incoming|both
        relationship_type_name: Optional[
            str
        ] = None,  # Changed to relationship_type_name
    ) -> List[Item]:
        """
        获取Item的关系

        Args:
            item_id: Item ID
            direction: 关系方向
            relationship_type_name: 可选的关系类型过滤

        Returns:
            关系列表
        """
        query = self.session.query(Item).filter(Item.is_current.is_(True))

        if direction == "outgoing":
            query = query.filter(Item.source_id == item_id)
        elif direction == "incoming":
            query = query.filter(Item.related_id == item_id)
        else:  # both
            query = query.filter(
                (Item.source_id == item_id) | (Item.related_id == item_id)
            )

        if relationship_type_name:
            _, rel_item_type = self._resolve_relationship_type(relationship_type_name)
            query = query.filter(Item.item_type_id == rel_item_type.id)

        return query.order_by(Item.created_at.asc()).all()

    def get_bom_tree(
        self, part_id: str, max_depth: int = 10  # Item IDs are string
    ) -> Dict[str, Any]:
        """
        获取BOM树结构

        Args:
            part_id: Part Item ID
            max_depth: 最大递归深度

        Returns:
            树形结构字典
        """
        return self._build_tree(part_id, "Part BOM", max_depth, 0)

    def _build_tree(
        self,
        item_id: str,  # Item IDs are string
        rel_type_name: str,  # Changed to rel_type_name
        max_depth: int,
        current_depth: int,
    ) -> Dict[str, Any]:
        """递归构建树"""
        item = self.session.get(Item, item_id)
        if not item:
            return {}

        node = {
            "id": item.id,
            "item_type": item.item_type_id,  # Use item_type_id
            "name": item.to_dict().get("name"),  # Use to_dict to get properties
            "children": [],
        }

        if current_depth >= max_depth:
            return node

        # 获取子关系
        relationships = self.get_relationships(
            item_id, direction="outgoing", relationship_type_name=rel_type_name
        )

        for rel in relationships:
            child_node = self._build_tree(
                rel.related_id, rel_type_name, max_depth, current_depth + 1
            )
            # Access properties directly from relationship.properties
            child_node["quantity"] = (
                rel.properties.get("quantity", 1) if rel.properties else 1
            )
            child_node["relationship_id"] = rel.id
            node["children"].append(child_node)

        return node
