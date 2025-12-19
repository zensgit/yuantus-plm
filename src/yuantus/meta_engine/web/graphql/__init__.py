"""
GraphQL Meta Engine Integration (ADR-007 Phase 3)

Provides GraphQL aggregation layer for stable core types:
- Part (零部件)
- Document (文档)
- BOM (物料清单)
- ECO (变更管理)

With GenericItem fallback for dynamic ItemTypes.
"""

from .schema import schema, create_graphql_router
from .types import Part, Document, BOMLine, ECO, GenericItem

__all__ = [
    "schema",
    "create_graphql_router",
    "Part",
    "Document",
    "BOMLine",
    "ECO",
    "GenericItem",
]
