"""
Relationship Service
关系管理服务
Phase 3.2
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from yuantus.meta_engine.relationship.models import RelationshipType, Relationship
from yuantus.meta_engine.models.item import Item  # Item model for type hinting.


class RelationshipService:
    """关系管理服务"""

    def __init__(self, session: Session):
        self.session = session

    def create_relationship(
        self,
        source_id: str,  # Item IDs are string
        related_id: str,  # Item IDs are string
        relationship_type_name: str,  # Changed from relationship_type to relationship_type_name to avoid confusion
        properties: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> Relationship:
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
        # 获取关系类型
        rel_type = (
            self.session.query(RelationshipType)
            .filter(RelationshipType.name == relationship_type_name)
            .first()
        )

        if not rel_type:
            raise ValueError(f"Unknown relationship type: {relationship_type_name}")

        # 验证源和目标类型
        source = self.session.get(Item, source_id)
        related = self.session.get(Item, related_id)

        if not source or not related:
            raise ValueError("Source or related item not found")

        if (
            source.item_type_id != rel_type.source_item_type
        ):  # Using item_type_id for Item
            raise ValueError(
                f"Source type mismatch: expected {rel_type.source_item_type}, "
                f"got {source.item_type_id}"
            )

        # Handle polymorphic relationships
        if not rel_type.is_polymorphic:
            if (
                related.item_type_id != rel_type.related_item_type
            ):  # Using item_type_id for Item
                raise ValueError(
                    f"Related type mismatch: expected {rel_type.related_item_type}, "
                    f"got {related.item_type_id}"
                )
        # If polymorphic, we might need a more complex check here,
        # e.g., checking inheritance tree, but for now strict type or no check.

        # 检查数量限制
        if rel_type.max_quantity is not None:
            existing_count = (
                self.session.query(Relationship)
                .filter(
                    Relationship.source_id == source_id,
                    Relationship.relationship_type_id == rel_type.id,
                )
                .count()
            )

            if existing_count >= rel_type.max_quantity:
                raise ValueError(
                    f"Max relationship quantity ({rel_type.max_quantity}) exceeded"
                )

        # 创建关系
        relationship = Relationship(
            relationship_type=rel_type,  # Assign object directly if SQLAlchemy handles it
            source_id=source_id,
            related_id=related_id,
            properties=properties,
            created_by_id=user_id,
        )

        self.session.add(relationship)
        self.session.flush()  # Flush to get ID for newly created relationship

        return relationship

    def get_relationships(
        self,
        item_id: str,  # Item IDs are string
        direction: str = "outgoing",  # outgoing|incoming|both
        relationship_type_name: Optional[
            str
        ] = None,  # Changed to relationship_type_name
    ) -> List[Relationship]:
        """
        获取Item的关系

        Args:
            item_id: Item ID
            direction: 关系方向
            relationship_type_name: 可选的关系类型过滤

        Returns:
            关系列表
        """
        query = self.session.query(Relationship)

        if direction == "outgoing":
            query = query.filter(Relationship.source_id == item_id)
        elif direction == "incoming":
            query = query.filter(Relationship.related_id == item_id)
        else:  # both
            query = query.filter(
                (Relationship.source_id == item_id)
                | (Relationship.related_id == item_id)
            )

        if relationship_type_name:
            # Need to join with RelationshipType to filter by name
            query = query.join(RelationshipType).filter(
                RelationshipType.name == relationship_type_name
            )

        return query.order_by(Relationship.sort_order).all()

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
        # "Part_BOM" is a placeholder relationship type name from the plan
        return self._build_tree(part_id, "Part_BOM", max_depth, 0)

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
