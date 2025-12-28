"""
Search Service
Handles indexing and searching of Items using Elasticsearch/OpenSearch.
Phase 9: Advanced Search
"""

import json
import logging
from typing import Dict, Any, Optional, Iterable

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

# Optional Elasticsearch dependency
try:
    from elasticsearch import Elasticsearch
except ImportError:
    Elasticsearch = None  # type: ignore

from yuantus.config import get_settings
from yuantus.meta_engine.models.eco import ECO
from yuantus.meta_engine.models.item import Item

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self, session: Optional[Session] = None):
        self.session = session
        settings = get_settings()
        self.index_name = f"{settings.SEARCH_ENGINE_INDEX_PREFIX}-items"
        self.eco_index_name = f"{settings.SEARCH_ENGINE_INDEX_PREFIX}-ecos"

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
                        "item_number": {"type": "keyword"},
                        "name": {"type": "text"},
                        "description": {"type": "text"},
                        "search_text": {"type": "text"},
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

    def ensure_eco_index(self) -> None:
        """Creates the ECO index with mappings if it doesn't exist."""
        if not self.client:
            return
        if self.client.indices.exists(index=self.eco_index_name):
            return
        mapping = {
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "name": {"type": "text"},
                    "description": {"type": "text"},
                    "search_text": {"type": "text"},
                    "state": {"type": "keyword"},
                    "eco_type": {"type": "keyword"},
                    "priority": {"type": "keyword"},
                    "product_id": {"type": "keyword"},
                    "source_version_id": {"type": "keyword"},
                    "target_version_id": {"type": "keyword"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                }
            }
        }
        self.client.indices.create(index=self.eco_index_name, body=mapping)
        logger.info(f"Created search index: {self.eco_index_name}")

    def _index_status(self, index_name: str) -> Dict[str, Any]:
        engine = "elasticsearch" if self.client else "db"
        enabled = bool(self.client)
        index_exists = False
        if enabled:
            try:
                index_exists = bool(self.client.indices.exists(index=index_name))
            except Exception as exc:
                logger.warning("Search index status check failed: %s", exc)
        return {
            "engine": engine,
            "enabled": enabled,
            "index": index_name,
            "index_exists": index_exists,
        }

    def status(self) -> Dict[str, Any]:
        return self._index_status(self.index_name)

    def eco_status(self) -> Dict[str, Any]:
        return self._index_status(self.eco_index_name)

    def reindex_items(
        self,
        *,
        item_type_id: Optional[str] = None,
        reset: bool = False,
        limit: Optional[int] = None,
        batch_size: int = 200,
    ) -> Dict[str, Any]:
        if not self.session:
            raise ValueError("SearchService requires a session for reindex.")

        if not self.client:
            count_stmt = select(func.count()).select_from(Item)
            if item_type_id:
                count_stmt = count_stmt.where(Item.item_type_id == item_type_id)
            total = self.session.execute(count_stmt).scalar() or 0
            return {
                "ok": True,
                "engine": "db",
                "index": self.index_name,
                "indexed": int(total),
                "reset": False,
                "item_type_id": item_type_id,
                "note": "db-fallback",
            }

        if reset:
            try:
                self.client.indices.delete(index=self.index_name, ignore=[400, 404])
            except Exception as exc:
                logger.warning("Search index delete failed: %s", exc)

        self.ensure_index()

        stmt = select(Item).order_by(Item.updated_at.desc())
        if item_type_id:
            stmt = stmt.where(Item.item_type_id == item_type_id)
        if limit:
            stmt = stmt.limit(limit)

        indexed = 0
        for item in (
            self.session.execute(stmt)
            .scalars()
            .yield_per(batch_size)
        ):
            self.index_item(item)
            indexed += 1

        return {
            "ok": True,
            "engine": "elasticsearch",
            "index": self.index_name,
            "indexed": indexed,
            "reset": reset,
            "item_type_id": item_type_id,
        }

    def reindex_ecos(
        self,
        *,
        state: Optional[str] = None,
        reset: bool = False,
        limit: Optional[int] = None,
        batch_size: int = 200,
    ) -> Dict[str, Any]:
        if not self.session:
            raise ValueError("SearchService requires a session for reindex.")

        if not self.client:
            count_stmt = select(func.count()).select_from(ECO)
            if state:
                count_stmt = count_stmt.where(ECO.state == state)
            total = self.session.execute(count_stmt).scalar() or 0
            return {
                "ok": True,
                "engine": "db",
                "index": self.eco_index_name,
                "indexed": int(total),
                "reset": False,
                "state": state,
                "note": "db-fallback",
            }

        if reset:
            try:
                self.client.indices.delete(index=self.eco_index_name, ignore=[400, 404])
            except Exception as exc:
                logger.warning("Search index delete failed: %s", exc)

        self.ensure_eco_index()

        stmt = select(ECO).order_by(ECO.updated_at.desc())
        if state:
            stmt = stmt.where(ECO.state == state)
        if limit:
            stmt = stmt.limit(limit)

        indexed = 0
        for eco in (
            self.session.execute(stmt)
            .scalars()
            .yield_per(batch_size)
        ):
            self.index_eco(eco)
            indexed += 1

        return {
            "ok": True,
            "engine": "elasticsearch",
            "index": self.eco_index_name,
            "indexed": indexed,
            "reset": reset,
            "state": state,
        }

    @staticmethod
    def _iter_values(value: Any) -> Iterable[Any]:
        if isinstance(value, dict):
            for val in value.values():
                yield from SearchService._iter_values(val)
            return
        if isinstance(value, (list, tuple, set)):
            for val in value:
                yield from SearchService._iter_values(val)
            return
        yield value

    @staticmethod
    def _normalize_value(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            text = value.strip()
            return text or None
        try:
            return json.dumps(
                value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
            )
        except TypeError:
            return str(value)

    def _build_search_text(self, props: Dict[str, Any]) -> str:
        preferred_keys = (
            "item_number",
            "name",
            "description",
            "title",
            "part_number",
            "drawing_number",
            "doc_number",
            "revision",
        )
        seen = set()
        chunks = []
        for key in preferred_keys:
            if key not in props:
                continue
            text = self._normalize_value(props.get(key))
            if text and text not in seen:
                seen.add(text)
                chunks.append(text)

        for value in self._iter_values(props):
            text = self._normalize_value(value)
            if text and text not in seen:
                seen.add(text)
                chunks.append(text)

        search_text = " ".join(chunks)
        return search_text[:4000]

    def _build_doc(self, item: Item) -> Dict[str, Any]:
        props = item.properties or {}
        return {
            "id": item.id,
            "item_type_id": item.item_type_id,
            "config_id": item.config_id,
            "state": item.state,
            "item_number": props.get("item_number"),
            "name": props.get("name"),
            "description": props.get("description"),
            "search_text": self._build_search_text(props),
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "properties": props,
        }

    def index_item(self, item: Item):
        """Index or update an item document."""
        if not self.client:
            return

        doc = self._build_doc(item)

        try:
            self.client.index(index=self.index_name, id=item.id, document=doc)
            logger.debug(f"Indexed item {item.id}")
        except Exception as e:
            logger.error(f"Failed to index item {item.id}: {e}")

    def index_eco(self, eco: ECO) -> None:
        """Index or update an ECO document."""
        if not self.client:
            return

        doc = self._eco_to_doc(eco)
        try:
            self.ensure_eco_index()
            self.client.index(index=self.eco_index_name, id=eco.id, document=doc)
        except Exception as exc:
            logger.error("Failed to index ECO %s: %s", eco.id, exc)

    def delete_item(self, item_id: str):
        """Delete an item from the index."""
        if not self.client:
            return

        try:
            self.client.delete(index=self.index_name, id=item_id)
            logger.debug(f"Deleted item {item_id} from index")
        except Exception as e:
            logger.error(f"Failed to delete item {item_id} from index: {e}")

    def delete_eco(self, eco_id: str) -> None:
        """Delete an ECO from the index."""
        if not self.client:
            return

        try:
            self.client.delete(index=self.eco_index_name, id=eco_id)
        except Exception as exc:
            logger.error("Failed to delete ECO %s from index: %s", eco_id, exc)

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
                            "search_text",
                            "item_number",
                            "name",
                            "description",
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
            if self.session:
                return self._search_fallback_db(
                    query_string=query_string, filters=filters or {}, limit=limit
                )
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

    def search_ecos(
        self, query_string: str, *, state: Optional[str] = None, limit: int = 20
    ) -> Dict[str, Any]:
        if not self.client:
            return self.search_ecos_db(query_string=query_string, state=state, limit=limit)

        self.ensure_eco_index()
        must_clauses = []

        if query_string:
            must_clauses.append(
                {
                    "multi_match": {
                        "query": query_string,
                        "fields": [
                            "search_text",
                            "name",
                            "description",
                            "id",
                            "product_id",
                            "source_version_id",
                            "target_version_id",
                            "state",
                            "eco_type",
                            "priority",
                        ],
                        "fuzziness": "AUTO",
                    }
                }
            )
        else:
            must_clauses.append({"match_all": {}})

        if state:
            must_clauses.append({"term": {"state": state}})

        body = {"query": {"bool": {"must": must_clauses}}, "size": limit}

        try:
            response = self.client.search(index=self.eco_index_name, body=body)
            hits = response["hits"]["hits"]
            return {
                "total": response["hits"]["total"]["value"],
                "hits": [h["_source"] for h in hits],
            }
        except Exception as exc:
            logger.error("ECO search failed: %s", exc)
            if self.session:
                return self.search_ecos_db(query_string=query_string, state=state, limit=limit)
            raise

    def search_ecos_db(
        self, *, query_string: str, state: Optional[str], limit: int
    ) -> Dict[str, Any]:
        if not self.session:
            return {"hits": [], "total": 0}

        stmt = select(ECO)
        if state:
            stmt = stmt.where(ECO.state == state)
        if query_string:
            like = f"%{query_string}%"
            stmt = stmt.where(
                or_(
                    ECO.id.ilike(like),
                    ECO.name.ilike(like),
                    cast(ECO.description, String).ilike(like),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.session.execute(count_stmt).scalar() or 0

        ecos = self.session.execute(stmt.limit(limit)).scalars().all()
        hits = [self._eco_to_doc(eco) for eco in ecos]
        return {"hits": hits, "total": total}

    def _item_to_doc(self, item: Item) -> Dict[str, Any]:
        return self._build_doc(item)

    def _eco_to_doc(self, eco: ECO) -> Dict[str, Any]:
        search_text = " ".join(
            [
                part
                for part in [
                    eco.name or "",
                    eco.description or "",
                    eco.id or "",
                    eco.product_id or "",
                    eco.state or "",
                    eco.eco_type or "",
                    eco.priority or "",
                ]
                if part
            ]
        )
        return {
            "id": eco.id,
            "name": eco.name,
            "description": eco.description,
            "search_text": search_text[:4000],
            "state": eco.state,
            "eco_type": eco.eco_type,
            "priority": eco.priority,
            "product_id": eco.product_id,
            "source_version_id": eco.source_version_id,
            "target_version_id": eco.target_version_id,
            "created_at": eco.created_at.isoformat() if eco.created_at else None,
            "updated_at": eco.updated_at.isoformat() if eco.updated_at else None,
        }
