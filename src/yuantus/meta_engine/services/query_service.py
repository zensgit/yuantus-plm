"""
AML Query Service (ADR-007)
增强的 AML 查询服务，支持 select/expand/depth 能力
"""

from typing import Any, Dict, List, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import String, and_, asc, cast, desc

from yuantus.meta_engine.schemas.aml import AMLQueryRequest, AMLQueryResponse
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.relationship.models import RelationshipType


class AMLQueryService:
    """
    增强的 AML 查询服务

    Features:
    - select: 字段选择，减少数据传输
    - expand: 关系展开，解决 N+1 问题
    - depth: 递归展开深度控制
    - 分页和排序
    """

    def __init__(self, session: Session):
        self.session = session
        self._expand_cache: Dict[str, Any] = {}

    def query(self, request: AMLQueryRequest) -> AMLQueryResponse:
        """
        执行 AML 增强查询

        Example:
            request = AMLQueryRequest(
                type="Part",
                where={"state": "Released"},
                select=["id", "number", "properties.weight"],
                expand=["bom_lines", "bom_lines.component"],
                depth=3,
                page=1,
                page_size=50
            )
        """
        # 1. 获取 ItemType
        item_type = self._get_item_type(request.type)
        if not item_type:
            return AMLQueryResponse(items=[], total=0)

        # 2. 构建基础查询
        base_query = self.session.query(Item).filter(Item.item_type_id == item_type.id)

        # 3. 应用 where 条件
        if request.where:
            base_query = self._apply_where(base_query, request.where)

        # 4. 获取总数 (分页前)
        total = base_query.count()

        # 5. 应用排序
        if request.order_by:
            base_query = self._apply_order(base_query, request.order_by)
        else:
            base_query = base_query.order_by(desc(Item.created_at))

        # 6. 应用分页
        offset = (request.page - 1) * request.page_size
        items = base_query.offset(offset).limit(request.page_size).all()

        # 7. 转换为字典
        result_items = [self._item_to_dict(item) for item in items]

        # 8. 应用 select (字段过滤)
        if request.select:
            result_items = [
                self._apply_select(item, request.select) for item in result_items
            ]

        # 9. 应用 expand (关系展开)
        if request.expand:
            result_items = self._apply_expand(
                result_items, request.expand, request.depth or 1
            )

        return AMLQueryResponse(
            items=result_items,
            total=total,
            page=request.page,
            page_size=request.page_size,
            has_more=(offset + len(items)) < total,
        )

    def get_by_id(
        self,
        item_type: str,
        item_id: str,
        select: Optional[List[str]] = None,
        expand: Optional[List[str]] = None,
        depth: int = 1,
    ) -> Optional[Dict[str, Any]]:
        """获取单个 Item"""
        item = (
            self.session.query(Item)
            .join(ItemType, Item.item_type_id == ItemType.id)
            .filter(ItemType.id == item_type)
            .filter(Item.id == item_id)
            .first()
        )

        if not item:
            return None

        result = self._item_to_dict(item)

        if select:
            result = self._apply_select(result, select)

        if expand:
            result = self._apply_expand([result], expand, depth)[0]

        return result

    def _get_item_type(self, type_name: str) -> Optional[ItemType]:
        """获取 ItemType"""
        return self.session.query(ItemType).filter(ItemType.id == type_name).first()

    def _json_text(self, expr):
        """
        Dialect-tolerant JSON scalar extraction.

        - PostgreSQL JSONB: supports .astext
        - SQLAlchemy 2.x JSON comparator: supports .as_string()
        """
        if hasattr(expr, "as_string"):
            return expr.as_string()
        if hasattr(expr, "astext"):
            return expr.astext
        return cast(expr, String)

    def _apply_where(self, query, where: Dict[str, Any]):
        """应用 where 条件"""
        conditions = []

        for key, value in where.items():
            if key.startswith("properties."):
                # JSONB 属性查询
                prop_key = key.replace("properties.", "")
                conditions.append(self._json_text(Item.properties[prop_key]) == str(value))
            elif key == "state":
                conditions.append(Item.state == value)
            elif key == "number":
                # number 存储在 properties JSONB 中
                conditions.append(self._json_text(Item.properties["number"]) == str(value))
            elif key == "name":
                # name 存储在 properties JSONB 中
                conditions.append(self._json_text(Item.properties["name"]) == str(value))
            elif key == "id":
                conditions.append(Item.id == value)
            elif key == "created_by_id":
                conditions.append(Item.created_by_id == value)
            elif key == "owner_id":
                conditions.append(Item.owner_id == value)
            elif isinstance(value, dict):
                # 操作符查询: {"$gt": 10, "$lt": 100}
                for op, op_value in value.items():
                    if op == "$gt":
                        conditions.append(
                            self._json_text(Item.properties[key]).cast(float) > op_value
                        )
                    elif op == "$lt":
                        conditions.append(
                            self._json_text(Item.properties[key]).cast(float) < op_value
                        )
                    elif op == "$gte":
                        conditions.append(
                            self._json_text(Item.properties[key]).cast(float) >= op_value
                        )
                    elif op == "$lte":
                        conditions.append(
                            self._json_text(Item.properties[key]).cast(float) <= op_value
                        )
                    elif op == "$ne":
                        conditions.append(self._json_text(Item.properties[key]) != str(op_value))
                    elif op == "$in":
                        conditions.append(
                            self._json_text(Item.properties[key]).in_([str(v) for v in op_value])
                        )
                    elif op == "$like":
                        conditions.append(
                            self._json_text(Item.properties[key]).like(f"%{op_value}%")
                        )

        if conditions:
            query = query.filter(and_(*conditions))

        return query

    def _apply_order(self, query, order_by: List[str]):
        """应用排序"""
        for order_spec in order_by:
            if ":" in order_spec:
                field, direction = order_spec.split(":")
            else:
                field, direction = order_spec, "asc"

            if field == "created_at":
                col = Item.created_at
            elif field == "updated_at" or field == "modified_at":
                col = Item.updated_at
            elif field == "number":
                # number 存储在 properties JSONB 中
                col = self._json_text(Item.properties["number"])
            elif field == "name":
                # name 存储在 properties JSONB 中
                col = self._json_text(Item.properties["name"])
            elif field == "state":
                col = Item.state
            elif field.startswith("properties."):
                prop_key = field.replace("properties.", "")
                col = self._json_text(Item.properties[prop_key])
            else:
                continue

            if direction.lower() == "desc":
                query = query.order_by(desc(col))
            else:
                query = query.order_by(asc(col))

        return query

    def _item_to_dict(self, item: Item) -> Dict[str, Any]:
        """Item 转字典"""
        props = item.properties or {}
        return {
            "id": item.id,
            "type": item.item_type_id,
            "number": props.get("number"),
            "name": props.get("name"),
            "revision": props.get("revision"),
            "generation": item.generation,
            "state": item.state,
            "config_id": item.config_id,
            "is_current": item.is_current,
            "properties": props,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            "created_by_id": item.created_by_id,
            "modified_by_id": item.modified_by_id,
            "owner_id": item.owner_id,
        }

    def _apply_select(
        self, item: Dict[str, Any], select_fields: List[str]
    ) -> Dict[str, Any]:
        """应用字段选择"""
        result = {}

        for field in select_fields:
            if "." in field:
                # 嵌套字段: properties.weight
                parts = field.split(".")
                value = item
                for part in parts:
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        value = None
                        break
                # 设置嵌套值
                self._set_nested(result, parts, value)
            else:
                # 顶级字段
                if field in item:
                    result[field] = item[field]

        # 始终包含 id 和 type
        result["id"] = item.get("id")
        result["type"] = item.get("type")

        return result

    def _set_nested(self, obj: dict, parts: List[str], value: Any):
        """设置嵌套值"""
        for i, part in enumerate(parts[:-1]):
            if part not in obj:
                obj[part] = {}
            obj = obj[part]
        obj[parts[-1]] = value

    def _apply_expand(
        self, items: List[Dict[str, Any]], expand: List[str], max_depth: int
    ) -> List[Dict[str, Any]]:
        """
        应用关系展开

        expand 示例:
        - ["bom_lines"] -> 展开 bom_lines 关系
        - ["bom_lines.component"] -> 展开 bom_lines 及其 component
        - ["documents", "bom_lines.component.bom_lines"] -> 多路径展开
        """
        if max_depth <= 0 or not items:
            return items

        # 解析展开路径
        expand_tree = self._parse_expand_paths(expand)

        # 收集所有 item IDs
        item_ids = [item["id"] for item in items if item.get("id")]

        # 批量加载关系 (DataLoader 模式)
        for rel_name, sub_expand in expand_tree.items():
            self._expand_relation(items, item_ids, rel_name, sub_expand, max_depth)

        return items

    def _parse_expand_paths(self, expand: List[str]) -> Dict[str, List[str]]:
        """
        解析展开路径为树结构

        输入: ["bom_lines", "bom_lines.component", "documents"]
        输出: {
            "bom_lines": ["component"],
            "documents": []
        }
        """
        tree: Dict[str, Set[str]] = {}

        for path in expand:
            parts = path.split(".")
            root = parts[0]
            if root not in tree:
                tree[root] = set()
            if len(parts) > 1:
                tree[root].add(".".join(parts[1:]))

        return {k: list(v) for k, v in tree.items()}

    def _expand_relation(
        self,
        items: List[Dict[str, Any]],
        item_ids: List[str],
        rel_name: str,
        sub_expand: List[str],
        remaining_depth: int,
    ):
        """展开单个关系"""
        if remaining_depth <= 0:
            return

        # 查询关系类型
        rel_type = (
            self.session.query(RelationshipType)
            .filter((RelationshipType.name == rel_name) | (RelationshipType.id == rel_name))
            .first()
        )

        if not rel_type:
            # 尝试作为内置关系名处理
            self._expand_builtin_relation(
                items, item_ids, rel_name, sub_expand, remaining_depth
            )
            return

        # 批量查询关系
        relationships = (
            self.session.query(Item)
            .filter(Item.is_current.is_(True))
            .filter(Item.item_type_id == rel_type.name)
            .filter(Item.source_id.in_(item_ids))
            .all()
        )

        # 收集目标 IDs
        target_ids = [r.related_id for r in relationships if r.related_id]

        # 批量查询目标 Items
        if target_ids:
            target_items = (
                self.session.query(Item).filter(Item.id.in_(target_ids)).all()
            )
            target_map = {item.id: self._item_to_dict(item) for item in target_items}
        else:
            target_map = {}

        # 组织关系数据
        rel_by_source: Dict[str, List[Dict[str, Any]]] = {}
        for r in relationships:
            if not r.source_id or not r.related_id:
                continue
            if r.source_id not in rel_by_source:
                rel_by_source[r.source_id] = []
            if r.related_id in target_map:
                rel_item = target_map[r.related_id].copy()
                rel_item["_rel_properties"] = r.properties or {}
                rel_by_source[r.source_id].append(rel_item)

        # 添加到 items
        for item in items:
            item_id = item.get("id")
            item[rel_name] = rel_by_source.get(item_id, [])

        # 递归展开子关系
        if sub_expand and remaining_depth > 1:
            all_related_items = []
            for item in items:
                all_related_items.extend(item.get(rel_name, []))
            if all_related_items:
                self._apply_expand(all_related_items, sub_expand, remaining_depth - 1)

    def _expand_builtin_relation(
        self,
        items: List[Dict[str, Any]],
        item_ids: List[str],
        rel_name: str,
        sub_expand: List[str],
        remaining_depth: int,
    ):
        """展开内置关系 (bom_lines, documents 等)"""
        if rel_name == "bom_lines":
            self._expand_bom_lines(items, item_ids, sub_expand, remaining_depth)
        elif rel_name == "documents":
            self._expand_documents(items, item_ids, sub_expand, remaining_depth)
        elif rel_name == "files":
            self._expand_files(items, item_ids, sub_expand, remaining_depth)
        elif rel_name == "versions":
            self._expand_versions(items, item_ids, sub_expand, remaining_depth)

    def _expand_bom_lines(
        self,
        items: List[Dict[str, Any]],
        item_ids: List[str],
        sub_expand: List[str],
        remaining_depth: int,
    ):
        """展开 BOM 行"""
        from yuantus.models.bom import BOMLine

        # 批量查询 BOM Lines
        bom_lines = (
            self.session.query(BOMLine)
            .filter(BOMLine.parent_product_id.in_(item_ids))
            .all()
        )

        # 收集子组件 IDs
        component_ids = [bl.child_product_id for bl in bom_lines]

        # 批量查询子组件
        if component_ids:
            components = (
                self.session.query(Item).filter(Item.id.in_(component_ids)).all()
            )
            component_map = {c.id: self._item_to_dict(c) for c in components}
        else:
            component_map = {}

        # 组织 BOM 数据
        bom_by_parent: Dict[str, List[Dict[str, Any]]] = {}
        for bl in bom_lines:
            if bl.parent_product_id not in bom_by_parent:
                bom_by_parent[bl.parent_product_id] = []

            bom_item = {
                "id": str(bl.id),
                "quantity": bl.quantity,
                "unit": bl.unit,
                "sequence": bl.sequence,
                "find_number": bl.find_number,
            }

            # 添加 component 引用
            if "component" in sub_expand or any(
                s.startswith("component.") for s in sub_expand
            ):
                bom_item["component"] = component_map.get(bl.child_product_id)

            bom_by_parent[bl.parent_product_id].append(bom_item)

        # 添加到 items
        for item in items:
            item_id = item.get("id")
            item["bom_lines"] = bom_by_parent.get(item_id, [])

        # 递归展开 component 的子关系
        if remaining_depth > 1:
            component_sub_expand = [
                s.replace("component.", "")
                for s in sub_expand
                if s.startswith("component.")
            ]
            if component_sub_expand:
                all_components = []
                for item in items:
                    for bl in item.get("bom_lines", []):
                        if bl.get("component"):
                            all_components.append(bl["component"])
                if all_components:
                    self._apply_expand(
                        all_components, component_sub_expand, remaining_depth - 1
                    )

    def _expand_documents(
        self,
        items: List[Dict[str, Any]],
        item_ids: List[str],
        sub_expand: List[str],
        remaining_depth: int,
    ):
        """展开关联文档"""
        # 查询 Document 类型的关系
        from yuantus.meta_engine.models.file import ItemFile

        item_files = (
            self.session.query(ItemFile).filter(ItemFile.item_id.in_(item_ids)).all()
        )

        # 组织文档数据
        docs_by_item: Dict[str, List[Dict[str, Any]]] = {}
        for item_file in item_files:
            if item_file.item_id not in docs_by_item:
                docs_by_item[item_file.item_id] = []
            docs_by_item[item_file.item_id].append(
                {
                    "id": item_file.file_container_id,
                    "file_role": item_file.file_role,
                    "is_primary": item_file.is_primary,
                }
            )

        for item in items:
            item_id = item.get("id")
            item["documents"] = docs_by_item.get(item_id, [])

    def _expand_files(
        self,
        items: List[Dict[str, Any]],
        item_ids: List[str],
        sub_expand: List[str],
        remaining_depth: int,
    ):
        """展开文件"""
        from yuantus.meta_engine.models.file import FileContainer, ItemFile

        item_files = (
            self.session.query(ItemFile).filter(ItemFile.item_id.in_(item_ids)).all()
        )

        file_ids = [f.file_container_id for f in item_files]

        if file_ids:
            files = (
                self.session.query(FileContainer)
                .filter(FileContainer.id.in_(file_ids))
                .all()
            )
            file_map = {f.id: f for f in files}
        else:
            file_map = {}

        files_by_item: Dict[str, List[Dict[str, Any]]] = {}
        for item_file in item_files:
            if item_file.item_id not in files_by_item:
                files_by_item[item_file.item_id] = []
            fc = file_map.get(item_file.file_container_id)
            if fc:
                files_by_item[item_file.item_id].append(
                    {
                        "id": fc.id,
                        "filename": fc.filename,
                        "file_size": fc.file_size,
                        "mime_type": fc.mime_type,
                        "checksum": fc.checksum,
                        "file_role": item_file.file_role,
                        "is_primary": item_file.is_primary,
                    }
                )

        for item in items:
            item_id = item.get("id")
            item["files"] = files_by_item.get(item_id, [])

    def _expand_versions(
        self,
        items: List[Dict[str, Any]],
        item_ids: List[str],
        sub_expand: List[str],
        remaining_depth: int,
    ):
        """展开版本历史"""
        from yuantus.meta_engine.version.models import ItemVersion

        versions = (
            self.session.query(ItemVersion)
            .filter(ItemVersion.item_id.in_(item_ids))
            .order_by(ItemVersion.generation, ItemVersion.revision)
            .all()
        )

        versions_by_item: Dict[str, List[Dict[str, Any]]] = {}
        for v in versions:
            if v.item_id not in versions_by_item:
                versions_by_item[v.item_id] = []
            versions_by_item[v.item_id].append(
                {
                    "id": v.id,
                    "generation": v.generation,
                    "revision": v.revision,
                    "is_current": v.is_current,
                    "is_released": v.is_released,
                    "created_at": v.created_at.isoformat() if v.created_at else None,
                }
            )

        for item in items:
            item_id = item.get("id")
            item["versions"] = versions_by_item.get(item_id, [])
