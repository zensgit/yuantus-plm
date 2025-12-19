"""
Search Service
Handles indexing and searching of Items using Elasticsearch/OpenSearch.
Phase 9: Advanced Search
"""

import logging
from typing import Dict, Any, Optional

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

# Optional Elasticsearch dependency
try:
    from elasticsearch import Elasticsearch
except ImportError:
    Elasticsearch = None  # type: ignore

from yuantus.config import get_settings
from yuantus.meta_engine.models.item import Item

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self, session: Optional[Session] = None):
        self.session = session
        settings = get_settings()
        self.index_name = f"{settings.SEARCH_ENGINE_INDEX_PREFIX}-items"

        # Initialize client
        if Elasticsearch is None:
            self.client = None
            logger.warning("Elasticsearch library not installed. Search disabled.")
        elif settings.SEARCH_ENGINE_URL:
            auth = None
            if settings.SEARCH_ENGINE_USERNAME and settings.SEARCH_ENGINE_PASSWORD:
                auth = (
                    settings.SEARCH_ENGINE_USERNAME,
                    settings.SEARCH_ENGINE_PASSWORD,
                )

            self.client = Elasticsearch(
                hosts=[settings.SEARCH_ENGINE_URL], basic_auth=auth
            )
        else:
            self.client = None
            logger.warning("Search engine not configured.")

    def ensure_index(self):
        """Creates the index with mappings if it doesn't exist."""
        if not self.client:
            return

        if not self.client.indices.exists(index=self.index_name):
            # Define mapping for dynamic properties
            mapping = {
                "mappings": {
                    "properties": {
                        "id": {"type": "keyword"},
                        "item_type_id": {"type": "keyword"},
                        "config_id": {"type": "keyword"},
                        "state": {"type": "keyword"},
                        # Dynamic properties field (flattened or object)
                        # Here we use 'properties' as an object with dynamic templates
                        "properties": {"type": "object", "dynamic": True},
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"},
                    }
                }
            }
            self.client.indices.create(index=self.index_name, body=mapping)
            logger.info(f"Created search index: {self.index_name}")

    def index_item(self, item: Item):
        """Index or update an item document."""
        if not self.client:
            return

        # Convert item to searchable document
        doc = {
            "id": item.id,
            "item_type_id": item.item_type_id,
            "config_id": item.config_id,
            "state": item.state,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "properties": item.properties or {},
        }

        try:
            self.client.index(index=self.index_name, id=item.id, document=doc)
            logger.debug(f"Indexed item {item.id}")
        except Exception as e:
            logger.error(f"Failed to index item {item.id}: {e}")

    def delete_item(self, item_id: str):
        """Delete an item from the index."""
        if not self.client:
            return

        try:
            self.client.delete(index=self.index_name, id=item_id)
            logger.debug(f"Deleted item {item_id} from index")
        except Exception as e:
            logger.error(f"Failed to delete item {item_id} from index: {e}")

    def search(
        self, query_string: str, filters: Dict[str, Any] = None, limit: int = 20
    ) -> Dict[str, Any]:
        """
        Execute a search query.
        Args:
            query_string: Full-text search string.
            filters: Dictionary of exact match filters (e.g. {'item_type_id': 'Part'}).
        """
        if not self.client:
            return self._search_fallback_db(
                query_string=query_string, filters=filters or {}, limit=limit
            )

        # Build Query DSL
        must_clauses = []

        if query_string:
            must_clauses.append(
                {
                    "multi_match": {
                        "query": query_string,
                        "fields": [
                            "properties.*",
                            "id",
                            "state",
                        ],  # Search across all properties
                        "fuzziness": "AUTO",
                    }
                }
            )
        else:
            must_clauses.append({"match_all": {}})

        if filters:
            for key, value in filters.items():
                must_clauses.append({"term": {key: value}})

        body = {"query": {"bool": {"must": must_clauses}}, "size": limit}

        try:
            response = self.client.search(index=self.index_name, body=body)
            hits = response["hits"]["hits"]
            return {
                "total": response["hits"]["total"]["value"],
                "hits": [h["_source"] for h in hits],
            }
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    def _search_fallback_db(
        self, *, query_string: str, filters: Dict[str, Any], limit: int
    ) -> Dict[str, Any]:
        """
        DB fallback for local/dev environments without Elasticsearch.

        Returns the same shape as the ES implementation: {'hits': [...], 'total': N}.
        """
        if not self.session:
            return {"hits": [], "total": 0}

        stmt = select(Item)

        # Exact-match filters
        for key, value in (filters or {}).items():
            # Allow filtering by top-level columns (id, item_type_id, state, config_id, ...)
            if hasattr(Item, key):
                stmt = stmt.where(getattr(Item, key) == value)
                continue

            # Support "properties.<key>" and raw "<key>" as JSON property filters
            prop_key = key.split(".", 1)[1] if key.startswith("properties.") else key
            json_expr = Item.properties[prop_key]
            if hasattr(json_expr, "as_string"):
                stmt = stmt.where(json_expr.as_string() == str(value))
            elif hasattr(json_expr, "astext"):
                stmt = stmt.where(json_expr.astext == str(value))
            else:
                stmt = stmt.where(cast(json_expr, String) == str(value))

        # Simple full-text-ish matching (best-effort; not meant to replace ES)
        if query_string:
            like = f"%{query_string}%"
            stmt = stmt.where(
                or_(
                    Item.id.ilike(like),
                    Item.state.ilike(like),
                    cast(Item.properties, String).ilike(like),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.session.execute(count_stmt).scalar() or 0

        items = self.session.execute(stmt.limit(limit)).scalars().all()
        hits = [self._item_to_doc(item) for item in items]
        return {"hits": hits, "total": total}

    def _item_to_doc(self, item: Item) -> Dict[str, Any]:
        return {
            "id": item.id,
            "item_type_id": item.item_type_id,
            "config_id": item.config_id,
            "state": item.state,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "properties": item.properties or {},
        }
