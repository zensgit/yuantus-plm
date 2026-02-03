"""Advanced search and saved search services."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import or_, cast, Float
from sqlalchemy.orm import Session

from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.reports.models import SavedSearch


class AdvancedSearchService:
    def __init__(self, session: Session):
        self.session = session

    def search(
        self,
        *,
        item_type_id: Optional[str] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        full_text: Optional[str] = None,
        sort: Optional[List[Dict[str, str]]] = None,
        columns: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 25,
        include_count: bool = True,
    ) -> Dict[str, Any]:
        return self._search_with_sql(
            item_type_id=item_type_id,
            filters=filters,
            full_text=full_text,
            sort=sort,
            columns=columns,
            page=page,
            page_size=page_size,
            include_count=include_count,
        )

    def _search_with_sql(
        self,
        *,
        item_type_id: Optional[str] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        full_text: Optional[str] = None,
        sort: Optional[List[Dict[str, str]]] = None,
        columns: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 25,
        include_count: bool = True,
    ) -> Dict[str, Any]:
        query = self.session.query(Item)

        if item_type_id:
            query = query.filter(Item.item_type_id == item_type_id)

        if filters:
            for f in filters:
                query = self._apply_filter(query, f)

        if full_text:
            search_term = f"%{full_text}%"
            query = query.filter(
                or_(
                    Item.config_id.ilike(search_term),
                    Item.properties["name"].astext.ilike(search_term),
                    Item.properties["description"].astext.ilike(search_term),
                )
            )

        total = query.count() if include_count else None

        if sort:
            for s in sort:
                field = s.get("field", "created_at")
                order = s.get("order", "desc")

                if hasattr(Item, field):
                    col = getattr(Item, field)
                else:
                    col = Item.properties[field].astext

                if order == "desc":
                    query = query.order_by(col.desc())
                else:
                    query = query.order_by(col.asc())
        else:
            query = query.order_by(Item.created_at.desc())

        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()

        results: List[Dict[str, Any]] = []
        for item in items:
            row = {
                "id": item.id,
                "config_id": item.config_id,
                "item_type_id": item.item_type_id,
                "generation": item.generation,
                "state": item.state,
                "is_current": item.is_current,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }

            if item.properties:
                if columns:
                    for col in columns:
                        if col in item.properties:
                            row[col] = item.properties[col]
                else:
                    row.update(item.properties)

            results.append(row)

        return {
            "items": results,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size if total is not None else None,
        }

    def _apply_filter(self, query, filter_def: Dict[str, Any]):
        field = filter_def.get("field")
        op = (filter_def.get("op") or "eq").lower()
        value = filter_def.get("value")

        if not field:
            return query

        if hasattr(Item, field):
            column = getattr(Item, field)
        else:
            column = Item.properties[field].astext

        if op in {"eq", "="}:
            return query.filter(column == value)
        if op in {"ne", "!="}:
            return query.filter(column != value)
        if op in {"gt", ">"}:
            return query.filter(self._cast_numeric(column) > self._coerce_number(value))
        if op in {"gte", ">="}:
            return query.filter(self._cast_numeric(column) >= self._coerce_number(value))
        if op in {"lt", "<"}:
            return query.filter(self._cast_numeric(column) < self._coerce_number(value))
        if op in {"lte", "<="}:
            return query.filter(self._cast_numeric(column) <= self._coerce_number(value))
        if op == "contains":
            return query.filter(column.ilike(f"%{value}%"))
        if op in {"not_contains", "not_like"}:
            return query.filter(~column.ilike(f"%{value}%"))
        if op in {"startswith", "prefix"}:
            return query.filter(column.ilike(f"{value}%"))
        if op in {"endswith", "suffix"}:
            return query.filter(column.ilike(f"%{value}"))
        if op == "in":
            values = value if isinstance(value, list) else self._split_list(value)
            return query.filter(column.in_(values))
        if op in {"nin", "not_in"}:
            values = value if isinstance(value, list) else self._split_list(value)
            return query.filter(~column.in_(values))
        if op == "isnull":
            if bool(value):
                return query.filter(column.is_(None))
            return query.filter(column.isnot(None))

        return query

    def _cast_numeric(self, column):
        return cast(column, Float)

    def _coerce_number(self, value: Any) -> Any:
        if value is None:
            return value
        if isinstance(value, (int, float)):
            return value
        try:
            return float(value)
        except (TypeError, ValueError):
            return value

    def _split_list(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return list(value)


class SavedSearchService:
    def __init__(self, session: Session):
        self.session = session
        self.search_service = AdvancedSearchService(session)

    def create_saved_search(
        self,
        *,
        name: str,
        description: Optional[str],
        owner_id: Optional[int],
        is_public: bool,
        item_type_id: Optional[str],
        criteria: Dict[str, Any],
        display_columns: Optional[List[str]] = None,
        page_size: int = 25,
    ) -> SavedSearch:
        saved = SavedSearch(
            name=name,
            description=description,
            owner_id=owner_id,
            is_public=is_public,
            item_type_id=item_type_id,
            criteria=criteria,
            display_columns=display_columns,
            page_size=page_size,
        )
        self.session.add(saved)
        self.session.commit()
        return saved

    def list_saved_searches(
        self,
        *,
        owner_id: Optional[int],
        include_public: bool = True,
    ) -> List[SavedSearch]:
        q = self.session.query(SavedSearch)
        if owner_id is not None and include_public:
            q = q.filter(or_(SavedSearch.owner_id == owner_id, SavedSearch.is_public.is_(True)))
        elif owner_id is not None:
            q = q.filter(SavedSearch.owner_id == owner_id)
        elif include_public:
            q = q.filter(SavedSearch.is_public.is_(True))
        return q.order_by(SavedSearch.created_at.desc()).all()

    def get_saved_search(self, saved_search_id: str) -> Optional[SavedSearch]:
        return self.session.get(SavedSearch, saved_search_id)

    def update_saved_search(
        self,
        saved_search_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_public: Optional[bool] = None,
        item_type_id: Optional[str] = None,
        criteria: Optional[Dict[str, Any]] = None,
        display_columns: Optional[List[str]] = None,
        page_size: Optional[int] = None,
    ) -> SavedSearch:
        saved = self.get_saved_search(saved_search_id)
        if not saved:
            raise ValueError("Saved search not found")

        if name is not None:
            saved.name = name
        if description is not None:
            saved.description = description
        if is_public is not None:
            saved.is_public = is_public
        if item_type_id is not None:
            saved.item_type_id = item_type_id
        if criteria is not None:
            saved.criteria = criteria
        if display_columns is not None:
            saved.display_columns = display_columns
        if page_size is not None:
            saved.page_size = page_size

        self.session.add(saved)
        self.session.commit()
        return saved

    def delete_saved_search(self, saved_search_id: str) -> None:
        saved = self.get_saved_search(saved_search_id)
        if not saved:
            raise ValueError("Saved search not found")
        self.session.delete(saved)
        self.session.commit()

    def run_saved_search(
        self,
        saved_search_id: str,
        *,
        page: int = 1,
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        saved = self.get_saved_search(saved_search_id)
        if not saved:
            raise ValueError("Saved search not found")

        criteria = saved.criteria or {}
        result = self.search_service.search(
            item_type_id=criteria.get("item_type_id") or saved.item_type_id,
            filters=criteria.get("filters"),
            full_text=criteria.get("full_text"),
            sort=criteria.get("sort"),
            columns=criteria.get("columns") or saved.display_columns,
            page=page,
            page_size=page_size or saved.page_size or 25,
            include_count=True,
        )

        saved.use_count = (saved.use_count or 0) + 1
        saved.last_used_at = datetime.utcnow()
        self.session.add(saved)
        self.session.commit()

        return result
