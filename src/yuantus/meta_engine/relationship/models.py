"""
Legacy relationship ORM models (deprecated).

Kept as a thin re-export so runtime code can avoid importing legacy models
directly. Use ItemType relationships (meta_items) for new writes.
"""

from yuantus.meta_engine.relationship.legacy_models import (  # noqa: F401
    Relationship,
    RelationshipType,
    get_relationship_write_block_stats,
    simulate_relationship_write_block,
)

__all__ = [
    "Relationship",
    "RelationshipType",
    "get_relationship_write_block_stats",
    "simulate_relationship_write_block",
]
