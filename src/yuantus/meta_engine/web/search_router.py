from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from yuantus.database import get_db
from yuantus.meta_engine.services.search_service import SearchService

search_router = APIRouter(prefix="/search", tags=["Search"])


@search_router.get("/")
def search_items(
    q: str, item_type: Optional[str] = None, db: Session = Depends(get_db)
):
    service = SearchService(db)
    filters = {"item_type_id": item_type} if item_type else {}
    return service.search(q, filters=filters)
