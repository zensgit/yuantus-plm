from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user, get_current_user_optional
from yuantus.config import get_settings
from yuantus.context import get_request_context
from yuantus.database import get_db
from yuantus.meta_engine.reports.search_service import AdvancedSearchService
from yuantus.meta_engine.services.report_service import ReportService

report_summary_search_router = APIRouter(prefix="/reports", tags=["Reports"])


class AdvancedSearchRequest(BaseModel):
    item_type_id: Optional[str] = None
    filters: Optional[List[Dict[str, Any]]] = None
    full_text: Optional[str] = None
    sort: Optional[List[Dict[str, str]]] = None
    columns: Optional[List[str]] = None
    lang: Optional[str] = None
    fallback_langs: Optional[List[str]] = None
    localized_fields: Optional[List[str]] = None
    page: int = 1
    page_size: int = 25
    include_count: bool = True


@report_summary_search_router.get("/summary")
def get_summary(
    db: Session = Depends(get_db),
    _user=Depends(get_current_user_optional),
):
    service = ReportService(db)
    ctx = get_request_context()
    settings = get_settings()
    summary = service.get_summary()
    summary["meta"] = {
        "tenant_id": ctx.tenant_id,
        "org_id": ctx.org_id,
        "tenancy_mode": settings.TENANCY_MODE,
        "generated_at": datetime.utcnow().isoformat(),
    }
    return summary


@report_summary_search_router.post("/search", response_model=Dict[str, Any])
def advanced_search(
    req: AdvancedSearchRequest,
    _user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = AdvancedSearchService(db)
    return service.search(
        item_type_id=req.item_type_id,
        filters=req.filters,
        full_text=req.full_text,
        sort=req.sort,
        columns=req.columns,
        lang=req.lang,
        fallback_langs=req.fallback_langs,
        localized_fields=req.localized_fields,
        page=req.page,
        page_size=req.page_size,
        include_count=req.include_count,
    )
