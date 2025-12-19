"""
GraphQL Schema for Meta Engine (ADR-007)

Provides Query type and schema configuration for the GraphQL aggregation layer.
"""

from typing import List, Optional
import strawberry
from strawberry.types import Info
from strawberry.fastapi import GraphQLRouter
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func

from .types import (
    Part,
    PartConnection,
    PartEdge,
    PartFilter,
    Document,
    DocumentConnection,
    DocumentEdge,
    DocumentFilter,
    BOMLine,
    ExplodedBOMItem,
    ECO,
    ECOConnection,
    ECOEdge,
    ECOFilter,
    ECOStage,
    GenericItem,
    GenericItemConnection,
    GenericItemEdge,
    GenericItemFilter,
    PageInfo,
    User,
)
from .loaders import (
    _item_to_part,
    _item_to_document,
    _item_to_generic,
)


# ============================================================
# Query Type
# ============================================================


@strawberry.type
class Query:
    """
    GraphQL Query type for Meta Engine.

    Provides read-only access to stable core types:
    - Parts
    - Documents
    - BOMs
    - ECOs

    With GenericItem fallback for dynamic ItemTypes.
    """

    # --------------------------------------------------------
    # Part Queries
    # --------------------------------------------------------

    @strawberry.field
    async def part(self, info: Info, id: str) -> Optional[Part]:
        """
        Get a single Part by ID.
        """
        loader = info.context.get("part_loader")
        if not loader:
            return None
        return await loader.load(id)

    @strawberry.field
    async def parts(
        self,
        info: Info,
        filter: Optional[PartFilter] = None,
        first: int = 50,
        after: Optional[str] = None,
    ) -> PartConnection:
        """
        Get paginated Parts with optional filtering.
        """
        from yuantus.meta_engine.models.item import Item
        from yuantus.meta_engine.models.meta_schema import ItemType

        db: Session = info.context["db"]

        # Get Part ItemType IDs
        part_types = (
            db.execute(
                select(ItemType.id).where(
                    and_(
                        ItemType.is_relationship.is_(False),
                        or_(
                            ItemType.id.ilike("part%"),
                            ItemType.id.ilike("%part"),
                        ),
                    )
                )
            )
            .scalars()
            .all()
        )

        # Build query
        query = select(Item).where(
            Item.item_type_id.in_(part_types) if part_types else True
        )

        # Apply filters
        if filter:
            if filter.is_current is not None:
                query = query.where(Item.is_current == filter.is_current)
            if filter.state:
                query = query.where(Item.state == filter.state)
            if filter.number:
                # Search in properties JSONB
                query = query.where(Item.properties["number"].as_string() == filter.number)
            if filter.name_contains:
                query = query.where(
                    Item.properties["name"].as_string().ilike(f"%{filter.name_contains}%")
                )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar() or 0

        # Pagination
        offset = int(after) if after else 0
        query = query.offset(offset).limit(first + 1)

        items = db.execute(query).scalars().all()

        # Check for more
        has_next = len(items) > first
        if has_next:
            items = items[:-1]

        # Build edges
        edges = [
            PartEdge(
                node=_item_to_part(item),
                cursor=str(offset + i),
            )
            for i, item in enumerate(items)
        ]

        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=offset > 0,
            start_cursor=str(offset) if items else None,
            end_cursor=str(offset + len(items) - 1) if items else None,
            total_count=total_count,
        )

        return PartConnection(edges=edges, page_info=page_info)

    # --------------------------------------------------------
    # Document Queries
    # --------------------------------------------------------

    @strawberry.field
    async def document(self, info: Info, id: str) -> Optional[Document]:
        """
        Get a single Document by ID.
        """
        loader = info.context.get("document_loader")
        if not loader:
            return None
        return await loader.load(id)

    @strawberry.field
    async def documents(
        self,
        info: Info,
        filter: Optional[DocumentFilter] = None,
        first: int = 50,
        after: Optional[str] = None,
    ) -> DocumentConnection:
        """
        Get paginated Documents with optional filtering.
        """
        from yuantus.meta_engine.models.item import Item
        from yuantus.meta_engine.models.meta_schema import ItemType

        db: Session = info.context["db"]

        # Get Document ItemType IDs
        doc_types = (
            db.execute(
                select(ItemType.id).where(
                    and_(
                        ItemType.is_relationship.is_(False),
                        or_(
                            ItemType.id.ilike("document%"),
                            ItemType.id.ilike("%document"),
                        ),
                    )
                )
            )
            .scalars()
            .all()
        )

        # Build query
        query = select(Item).where(
            Item.item_type_id.in_(doc_types) if doc_types else True
        )

        # Apply filters
        if filter:
            if filter.is_current is not None:
                query = query.where(Item.is_current == filter.is_current)
            if filter.state:
                query = query.where(Item.state == filter.state)
            if filter.number:
                query = query.where(Item.properties["number"].as_string() == filter.number)
            if filter.name_contains:
                query = query.where(
                    Item.properties["name"].as_string().ilike(f"%{filter.name_contains}%")
                )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar() or 0

        # Pagination
        offset = int(after) if after else 0
        query = query.offset(offset).limit(first + 1)

        items = db.execute(query).scalars().all()

        # Check for more
        has_next = len(items) > first
        if has_next:
            items = items[:-1]

        # Build edges
        edges = [
            DocumentEdge(
                node=_item_to_document(item),
                cursor=str(offset + i),
            )
            for i, item in enumerate(items)
        ]

        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=offset > 0,
            start_cursor=str(offset) if items else None,
            end_cursor=str(offset + len(items) - 1) if items else None,
            total_count=total_count,
        )

        return DocumentConnection(edges=edges, page_info=page_info)

    # --------------------------------------------------------
    # BOM Queries
    # --------------------------------------------------------

    @strawberry.field
    async def bom_explode(
        self,
        info: Info,
        part_id: str,
        max_level: int = 10,
        include_properties: bool = False,
    ) -> List[ExplodedBOMItem]:
        """
        Explode BOM to flat list with level information.

        Args:
            part_id: Root part ID
            max_level: Maximum depth to explode (default 10)
            include_properties: Whether to include full properties (default False)
        """
        from yuantus.meta_engine.models.item import Item
        from yuantus.meta_engine.models.meta_schema import ItemType

        db: Session = info.context["db"]

        # Get BOM relationship ItemType
        bom_types = (
            db.execute(
                select(ItemType.id).where(
                    and_(
                        ItemType.is_relationship.is_(True),
                        ItemType.id.ilike("%bom%"),
                    )
                )
            )
            .scalars()
            .all()
        )

        result = []
        visited = set()

        def _explode(parent_id: str, level: int, path: List[str]):
            if level > max_level or parent_id in visited:
                return
            visited.add(parent_id)

            # Get BOM lines for this parent
            bom_items = (
                db.execute(
                    select(Item).where(
                        and_(
                            Item.source_id == parent_id,
                            Item.item_type_id.in_(bom_types) if bom_types else True,
                        )
                    )
                )
                .scalars()
                .all()
            )

            for item in bom_items:
                if not item.related_id:
                    continue

                # Get child item details
                child = db.get(Item, item.related_id)
                if not child:
                    continue

                child_props = child.properties or {}
                bom_props = item.properties or {}
                current_path = path + [item.related_id]

                result.append(
                    ExplodedBOMItem(
                        level=level,
                        path="/".join(current_path),
                        component_id=item.related_id,
                        component_number=child_props.get("number"),
                        component_name=child_props.get("name"),
                        quantity=float(bom_props.get("quantity", 1)),
                        unit=bom_props.get("unit") or bom_props.get("uom"),
                        find_number=bom_props.get("find_number"),
                        properties=bom_props if include_properties else None,
                    )
                )

                # Recurse
                _explode(item.related_id, level + 1, current_path)

        _explode(part_id, 1, [part_id])
        return result

    @strawberry.field
    async def bom_lines(
        self,
        info: Info,
        part_id: str,
        depth: int = 1,
    ) -> List[BOMLine]:
        """
        Get BOM lines for a part with specified depth.

        Args:
            part_id: Parent part ID
            depth: Expansion depth (default 1, just direct children)
        """
        loader = info.context.get("bom_lines_loader")
        if not loader:
            return []
        return await loader.load((part_id, depth))

    # --------------------------------------------------------
    # ECO Queries
    # --------------------------------------------------------

    @strawberry.field
    async def eco(self, info: Info, id: str) -> Optional[ECO]:
        """
        Get a single ECO by ID.
        """
        loader = info.context.get("eco_loader")
        if not loader:
            return None
        return await loader.load(id)

    @strawberry.field
    async def ecos(
        self,
        info: Info,
        filter: Optional[ECOFilter] = None,
        first: int = 50,
        after: Optional[str] = None,
    ) -> ECOConnection:
        """
        Get paginated ECOs with optional filtering.
        """
        from yuantus.meta_engine.models.eco import ECO as ECOModel

        db: Session = info.context["db"]

        # Build query
        query = select(ECOModel)

        # Apply filters
        if filter:
            if filter.state:
                query = query.where(ECOModel.state == filter.state)
            if filter.eco_type:
                query = query.where(ECOModel.eco_type == filter.eco_type)
            if filter.priority:
                query = query.where(ECOModel.priority == filter.priority)
            if filter.stage_id:
                query = query.where(ECOModel.stage_id == filter.stage_id)
            if filter.product_id:
                query = query.where(ECOModel.product_id == filter.product_id)

        # Order by created_at desc
        query = query.order_by(ECOModel.created_at.desc())

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar() or 0

        # Pagination
        offset = int(after) if after else 0
        query = query.offset(offset).limit(first + 1)

        ecos = db.execute(query).scalars().all()

        # Check for more
        has_next = len(ecos) > first
        if has_next:
            ecos = ecos[:-1]

        # Build edges

        edges = []
        for i, e in enumerate(ecos):
            edges.append(
                ECOEdge(
                    node=ECO(
                        id=e.id,
                        name=e.name,
                        eco_type=e.eco_type,
                        product_id=e.product_id,
                        stage_id=e.stage_id,
                        state=e.state,
                        kanban_state=e.kanban_state,
                        priority=e.priority,
                        description=e.description,
                        effectivity_date=e.effectivity_date,
                        created_at=e.created_at,
                        updated_at=e.updated_at,
                        created_by_id=e.created_by_id,
                    ),
                    cursor=str(offset + i),
                )
            )

        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=offset > 0,
            start_cursor=str(offset) if ecos else None,
            end_cursor=str(offset + len(ecos) - 1) if ecos else None,
            total_count=total_count,
        )

        return ECOConnection(edges=edges, page_info=page_info)

    @strawberry.field
    async def eco_stages(self, info: Info) -> List[ECOStage]:
        """
        Get all ECO stages.
        """
        from yuantus.meta_engine.models.eco import ECOStage as ECOStageModel

        db: Session = info.context["db"]

        stages = (
            db.execute(select(ECOStageModel).order_by(ECOStageModel.sequence))
            .scalars()
            .all()
        )

        return [
            ECOStage(
                id=s.id,
                name=s.name,
                sequence=s.sequence,
                is_blocking=s.is_blocking,
                approval_type=s.approval_type,
                min_approvals=s.min_approvals,
            )
            for s in stages
        ]

    # --------------------------------------------------------
    # Generic Item Queries (Dynamic ItemTypes)
    # --------------------------------------------------------

    @strawberry.field
    async def item(
        self,
        info: Info,
        type: str,
        id: str,
    ) -> Optional[GenericItem]:
        """
        Get a single item of any type by ID.

        Use this for dynamic ItemTypes not covered by Part/Document/ECO.
        """
        from yuantus.meta_engine.models.item import Item

        db: Session = info.context["db"]

        item = db.execute(
            select(Item).where(
                and_(
                    Item.id == id,
                    Item.item_type_id == type,
                )
            )
        ).scalar_one_or_none()

        if not item:
            return None

        return _item_to_generic(item)

    @strawberry.field
    async def items(
        self,
        info: Info,
        filter: GenericItemFilter,
        first: int = 50,
        after: Optional[str] = None,
    ) -> GenericItemConnection:
        """
        Get paginated items of any type.

        Use this for dynamic ItemTypes not covered by Part/Document/ECO.
        """
        from yuantus.meta_engine.models.item import Item

        db: Session = info.context["db"]

        # Build query
        query = select(Item).where(Item.item_type_id == filter.type)

        # Apply filters
        if filter.is_current is not None:
            query = query.where(Item.is_current == filter.is_current)
        if filter.state:
            query = query.where(Item.state == filter.state)
        if filter.number:
            query = query.where(Item.properties["number"].as_string() == filter.number)
        if filter.name_contains:
            query = query.where(
                Item.properties["name"]
                .as_string()
                .ilike(f"%{filter.name_contains}%")
            )
        if filter.properties:
            # Apply JSONB property filters
            for key, value in filter.properties.items():
                query = query.where(Item.properties[key].as_string() == str(value))

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar() or 0

        # Pagination
        offset = int(after) if after else 0
        query = query.offset(offset).limit(first + 1)

        items = db.execute(query).scalars().all()

        # Check for more
        has_next = len(items) > first
        if has_next:
            items = items[:-1]

        # Build edges
        edges = [
            GenericItemEdge(
                node=_item_to_generic(item),
                cursor=str(offset + i),
            )
            for i, item in enumerate(items)
        ]

        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=offset > 0,
            start_cursor=str(offset) if items else None,
            end_cursor=str(offset + len(items) - 1) if items else None,
            total_count=total_count,
        )

        return GenericItemConnection(edges=edges, page_info=page_info)

    # --------------------------------------------------------
    # User Query
    # --------------------------------------------------------

    @strawberry.field
    async def me(self, info: Info) -> Optional[User]:
        """
        Get current authenticated user.
        """
        user_id = info.context.get("user_id")
        if not user_id:
            return None

        loader = info.context.get("user_loader")
        if not loader:
            return None

        return await loader.load(user_id)


# ============================================================
# Schema Creation
# ============================================================


# Schema Version
SCHEMA_VERSION = "1.0.0"


@strawberry.type
class SchemaInfo:
    """GraphQL Schema information."""

    version: str
    description: str
    supported_types: List[str]


@strawberry.type
class QueryWithInfo(Query):
    """Extended Query with schema info."""

    @strawberry.field
    def schema_info(self) -> SchemaInfo:
        """
        Get GraphQL schema version and info.

        Supports versioned schema mechanism per ADR-007.
        """
        return SchemaInfo(
            version=SCHEMA_VERSION,
            description="PLM Meta Engine GraphQL API - Read-only aggregation layer",
            supported_types=[
                "Part",
                "Document",
                "BOMLine",
                "ECO",
                "GenericItem",
            ],
        )


# Create schema (read-only, no mutations per ADR-007)
schema = strawberry.Schema(query=QueryWithInfo)


def create_graphql_router(
    db_session_factory,
    debug: bool = False,
) -> GraphQLRouter:
    """
    Create GraphQL router with context.

    Args:
        db_session_factory: Factory function to create database sessions
        debug: Enable debug mode

    Returns:
        GraphQLRouter instance
    """
    from .loaders import create_data_loaders

    async def get_context(request):
        """Create GraphQL context with database session and data loaders."""
        db = db_session_factory()

        # Get user ID from request if available
        user_id = None
        if hasattr(request.state, "user_id"):
            user_id = request.state.user_id
        elif hasattr(request.state, "user"):
            user_id = getattr(request.state.user, "id", None)

        # Create context with data loaders
        context = {
            "request": request,
            "db": db,
            "user_id": user_id,
        }

        # Add all data loaders
        context.update(create_data_loaders(db))

        return context

    # Note: debug parameter removed - not supported in newer strawberry versions
    return GraphQLRouter(
        schema,
        context_getter=get_context,
    )
