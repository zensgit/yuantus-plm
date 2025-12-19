"""
GraphQL Type Definitions for Meta Engine (ADR-007)

Defines stable core types that map to Meta Engine Items:
- Part: Parts/Components
- Document: Documents with versioning
- BOMLine: BOM relationships
- ECO: Engineering Change Orders
- GenericItem: Fallback for dynamic ItemTypes
"""

from datetime import datetime
from typing import List, Optional
import strawberry
from strawberry.types import Info
from strawberry.scalars import JSON


# ============================================================
# Scalar Types
# ============================================================


@strawberry.type
class PageInfo:
    """Pagination information for connections."""

    has_next_page: bool
    has_previous_page: bool
    start_cursor: Optional[str]
    end_cursor: Optional[str]
    total_count: int


@strawberry.type
class User:
    """User reference type."""

    id: int
    username: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


@strawberry.type
class ItemVersion:
    """Item version information."""

    id: str
    item_id: str
    generation: int
    revision: str
    state: Optional[str]
    created_at: Optional[datetime]
    created_by_id: Optional[int]


# ============================================================
# Core Types: Part
# ============================================================


@strawberry.type
class Part:
    """
    Part GraphQL type (maps to Meta Engine Item with type Part).

    Provides strongly typed access to Part items while
    supporting dynamic properties via JSON.
    """

    id: str
    number: Optional[str]
    name: Optional[str]
    state: Optional[str]
    generation: int
    is_current: bool
    config_id: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    # Dynamic properties as JSON
    properties: Optional[JSON]

    @strawberry.field
    async def bom_lines(self, info: Info, depth: int = 1) -> List["BOMLine"]:
        """
        Get BOM lines for this part.

        Args:
            depth: Max depth for recursive BOM expansion (default 1)
        """
        loader = info.context.get("bom_lines_loader")
        if not loader:
            return []
        return await loader.load((self.id, depth))

    @strawberry.field
    async def documents(self, info: Info) -> List["Document"]:
        """Get documents related to this part."""
        loader = info.context.get("part_documents_loader")
        if not loader:
            return []
        return await loader.load(self.id)

    @strawberry.field
    async def versions(self, info: Info) -> List[ItemVersion]:
        """Get version history for this part."""
        loader = info.context.get("item_versions_loader")
        if not loader:
            return []
        return await loader.load(self.id)

    @strawberry.field
    async def created_by(self, info: Info) -> Optional[User]:
        """Get creator user."""
        loader = info.context.get("user_loader")
        if not loader or not hasattr(self, "created_by_id"):
            return None
        created_by_id = getattr(self, "created_by_id", None)
        if not created_by_id:
            return None
        return await loader.load(created_by_id)

    @strawberry.field
    async def where_used(self, info: Info, max_level: int = 5) -> List["WhereUsedItem"]:
        """Get where this part is used (reverse BOM lookup)."""
        loader = info.context.get("where_used_loader")
        if not loader:
            return []
        return await loader.load((self.id, max_level))


@strawberry.type
class PartConnection:
    """Part connection for pagination."""

    edges: List["PartEdge"]
    page_info: PageInfo


@strawberry.type
class PartEdge:
    """Part edge in connection."""

    node: Part
    cursor: str


# ============================================================
# Core Types: Document
# ============================================================


@strawberry.type
class Document:
    """
    Document GraphQL type (maps to Meta Engine Item with type Document).
    """

    id: str
    number: Optional[str]
    name: Optional[str]
    state: Optional[str]
    generation: int
    is_current: bool
    config_id: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    # Dynamic properties as JSON
    properties: Optional[JSON]

    @strawberry.field
    async def files(self, info: Info) -> List["FileAttachment"]:
        """Get file attachments for this document."""
        loader = info.context.get("document_files_loader")
        if not loader:
            return []
        return await loader.load(self.id)

    @strawberry.field
    async def versions(self, info: Info) -> List[ItemVersion]:
        """Get version history for this document."""
        loader = info.context.get("item_versions_loader")
        if not loader:
            return []
        return await loader.load(self.id)

    @strawberry.field
    async def related_parts(self, info: Info) -> List[Part]:
        """Get parts related to this document."""
        loader = info.context.get("document_parts_loader")
        if not loader:
            return []
        return await loader.load(self.id)


@strawberry.type
class FileAttachment:
    """File attachment for documents."""

    id: str
    filename: str
    file_type: Optional[str]
    file_size: Optional[int]
    storage_path: Optional[str]
    checksum: Optional[str]
    created_at: Optional[datetime]


@strawberry.type
class DocumentConnection:
    """Document connection for pagination."""

    edges: List["DocumentEdge"]
    page_info: PageInfo


@strawberry.type
class DocumentEdge:
    """Document edge in connection."""

    node: Document
    cursor: str


# ============================================================
# Core Types: BOM
# ============================================================


@strawberry.type
class BOMLine:
    """
    BOM Line GraphQL type.

    In Meta Engine, BOM is represented as relationship Items:
    - source_id → parent part
    - related_id → child part
    - properties stores quantity, unit, find_number, etc.
    """

    id: str
    parent_id: str
    child_id: str
    quantity: float
    unit: Optional[str]
    find_number: Optional[str]
    level: int = 1
    sequence: Optional[int]
    properties: Optional[JSON]

    @strawberry.field
    async def parent(self, info: Info) -> Optional[Part]:
        """Get parent part."""
        loader = info.context.get("part_loader")
        if not loader:
            return None
        return await loader.load(self.parent_id)

    @strawberry.field
    async def child(self, info: Info) -> Optional[Part]:
        """Get child component part."""
        loader = info.context.get("part_loader")
        if not loader:
            return None
        return await loader.load(self.child_id)

    @strawberry.field
    async def child_bom_lines(self, info: Info, depth: int = 1) -> List["BOMLine"]:
        """
        Get nested BOM lines for the child component.
        Supports recursive BOM expansion.
        """
        if depth <= 0:
            return []
        loader = info.context.get("bom_lines_loader")
        if not loader:
            return []
        return await loader.load((self.child_id, depth - 1))


@strawberry.type
class ExplodedBOMItem:
    """
    Exploded BOM item for flat BOM view.
    """

    level: int
    path: str
    component_id: str
    component_number: Optional[str]
    component_name: Optional[str]
    quantity: float
    unit: Optional[str]
    find_number: Optional[str]
    properties: Optional[JSON]


@strawberry.type
class WhereUsedItem:
    """Where-used result item."""

    level: int
    path: str
    parent_id: str
    parent_number: Optional[str]
    parent_name: Optional[str]
    quantity: float
    unit: Optional[str]


# ============================================================
# Core Types: ECO (Engineering Change Order)
# ============================================================


@strawberry.type
class ECOStage:
    """ECO stage definition."""

    id: str
    name: str
    sequence: int
    is_blocking: bool
    approval_type: str
    min_approvals: int


@strawberry.type
class ECOApproval:
    """ECO approval record."""

    id: str
    eco_id: str
    stage_id: str
    status: str
    user_id: Optional[int]
    comment: Optional[str]
    approved_at: Optional[datetime]
    created_at: Optional[datetime]


@strawberry.type
class ECOBOMChange:
    """ECO BOM change record."""

    id: str
    eco_id: str
    change_type: str
    parent_item_id: Optional[str]
    child_item_id: Optional[str]
    old_qty: Optional[float]
    new_qty: Optional[float]
    old_uom: Optional[str]
    new_uom: Optional[str]
    conflict: bool
    conflict_reason: Optional[str]


@strawberry.type
class ECO:
    """
    ECO (Engineering Change Order) GraphQL type.
    """

    id: str
    name: str
    eco_type: str
    product_id: Optional[str]
    stage_id: Optional[str]
    state: str
    kanban_state: Optional[str]
    priority: str
    description: Optional[str]
    effectivity_date: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    created_by_id: Optional[int]

    @strawberry.field
    async def product(self, info: Info) -> Optional[Part]:
        """Get the product being changed."""
        if not self.product_id:
            return None
        loader = info.context.get("part_loader")
        if not loader:
            return None
        return await loader.load(self.product_id)

    @strawberry.field
    async def stage(self, info: Info) -> Optional[ECOStage]:
        """Get current stage."""
        if not self.stage_id:
            return None
        loader = info.context.get("eco_stage_loader")
        if not loader:
            return None
        return await loader.load(self.stage_id)

    @strawberry.field
    async def approvals(self, info: Info) -> List[ECOApproval]:
        """Get approval records."""
        loader = info.context.get("eco_approvals_loader")
        if not loader:
            return []
        return await loader.load(self.id)

    @strawberry.field
    async def bom_changes(self, info: Info) -> List[ECOBOMChange]:
        """Get BOM change records."""
        loader = info.context.get("eco_bom_changes_loader")
        if not loader:
            return []
        return await loader.load(self.id)

    @strawberry.field
    async def created_by(self, info: Info) -> Optional[User]:
        """Get creator user."""
        if not self.created_by_id:
            return None
        loader = info.context.get("user_loader")
        if not loader:
            return None
        return await loader.load(self.created_by_id)


@strawberry.type
class ECOConnection:
    """ECO connection for pagination."""

    edges: List["ECOEdge"]
    page_info: PageInfo


@strawberry.type
class ECOEdge:
    """ECO edge in connection."""

    node: ECO
    cursor: str


# ============================================================
# Generic Types (Fallback for dynamic ItemTypes)
# ============================================================


@strawberry.type
class GenericItem:
    """
    Generic Item type for dynamic ItemTypes.

    Used when querying ItemTypes that are not mapped to
    strongly typed GraphQL types (Part, Document, etc.).
    """

    id: str
    type: str
    number: Optional[str]
    name: Optional[str]
    state: Optional[str]
    generation: int
    is_current: bool
    config_id: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    # All properties as JSON
    properties: Optional[JSON]

    # Relationship data as JSON
    relationships: Optional[JSON]

    @strawberry.field
    async def source_item(self, info: Info) -> Optional["GenericItem"]:
        """Get source item if this is a relationship."""
        loader = info.context.get("generic_item_loader")
        if not loader:
            return None
        source_id = getattr(self, "source_id", None)
        if not source_id:
            return None
        return await loader.load(source_id)

    @strawberry.field
    async def related_item(self, info: Info) -> Optional["GenericItem"]:
        """Get related item if this is a relationship."""
        loader = info.context.get("generic_item_loader")
        if not loader:
            return None
        related_id = getattr(self, "related_id", None)
        if not related_id:
            return None
        return await loader.load(related_id)


@strawberry.type
class GenericItemConnection:
    """Generic item connection for pagination."""

    edges: List["GenericItemEdge"]
    page_info: PageInfo


@strawberry.type
class GenericItemEdge:
    """Generic item edge in connection."""

    node: GenericItem
    cursor: str


# ============================================================
# Input Types
# ============================================================


@strawberry.input
class PartFilter:
    """Filter for Part queries."""

    number: Optional[str] = None
    name_contains: Optional[str] = None
    state: Optional[str] = None
    is_current: Optional[bool] = True


@strawberry.input
class DocumentFilter:
    """Filter for Document queries."""

    number: Optional[str] = None
    name_contains: Optional[str] = None
    state: Optional[str] = None
    is_current: Optional[bool] = True


@strawberry.input
class ECOFilter:
    """Filter for ECO queries."""

    state: Optional[str] = None
    eco_type: Optional[str] = None
    priority: Optional[str] = None
    stage_id: Optional[str] = None
    product_id: Optional[str] = None


@strawberry.input
class GenericItemFilter:
    """Filter for GenericItem queries."""

    type: str
    number: Optional[str] = None
    name_contains: Optional[str] = None
    state: Optional[str] = None
    is_current: Optional[bool] = True
    properties: Optional[JSON] = None
