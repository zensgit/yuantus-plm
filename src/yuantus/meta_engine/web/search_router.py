import csv
from io import StringIO
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from yuantus.database import get_db
from yuantus.api.dependencies.auth import (
    CurrentUser,
    require_admin_user,
    get_current_user,
)
from yuantus.meta_engine.services.file_search_service import FileSearchService
from yuantus.meta_engine.services.search_indexer import indexer_status
from yuantus.meta_engine.services.search_service import SearchService

search_router = APIRouter(prefix="/search", tags=["Search"])


class SearchStatusResponse(BaseModel):
    engine: str
    enabled: bool
    index: str
    index_exists: bool = False


class SearchIndexerStatusResponse(BaseModel):
    registered: bool
    registered_at: Optional[str] = None
    status_started_at: str
    uptime_seconds: int
    health: str
    health_reasons: list[str]
    item_index_ready: bool
    eco_index_ready: bool
    handlers: list[str]
    indexed_event_types: list[str]
    unindexed_event_types: list[str]
    event_coverage: Dict[str, str]
    subscription_counts: Dict[str, int]
    missing_handlers: list[str]
    duplicate_handlers: list[str]
    event_counts: Dict[str, int]
    success_counts: Dict[str, int]
    skipped_counts: Dict[str, int]
    error_counts: Dict[str, int]
    last_event_type: Optional[str] = None
    last_event_at: Optional[str] = None
    last_event_age_seconds: Optional[int] = None
    last_outcome: Optional[str] = None
    last_success_event_type: Optional[str] = None
    last_success_at: Optional[str] = None
    last_success_age_seconds: Optional[int] = None
    last_skipped_event_type: Optional[str] = None
    last_skipped_at: Optional[str] = None
    last_skipped_age_seconds: Optional[int] = None
    last_skipped_reason: Optional[str] = None
    last_error_event_type: Optional[str] = None
    last_error_at: Optional[str] = None
    last_error_age_seconds: Optional[int] = None
    last_error: Optional[str] = None


class SearchReportBucket(BaseModel):
    key: str
    count: int


class SearchItemReport(BaseModel):
    total: int
    by_item_type: list[SearchReportBucket]
    by_state: list[SearchReportBucket]


class SearchEcoReport(BaseModel):
    total: int
    by_state: list[SearchReportBucket]
    by_stage: list[SearchReportBucket]


class SearchReportsSummaryResponse(BaseModel):
    engine: str
    items: SearchItemReport
    ecos: SearchEcoReport


class SearchReportAgeBucket(BaseModel):
    key: str
    count: int
    avg_age_days: float
    max_age_days: float


class SearchEcoStageAgingResponse(BaseModel):
    engine: str
    age_source: str
    buckets: list[SearchReportAgeBucket]


class SearchEcoStateTrendBucket(BaseModel):
    date: str
    state: str
    count: int


class SearchEcoStateTrendResponse(BaseModel):
    engine: str
    trend_source: str
    days: int
    start_date: str
    end_date: str
    buckets: list[SearchEcoStateTrendBucket]


class SearchReindexRequest(BaseModel):
    item_type_id: Optional[str] = Field(default=None)
    reset: bool = Field(default=False)
    limit: Optional[int] = Field(default=None, ge=1)
    batch_size: int = Field(default=200, ge=1, le=2000)


class SearchReindexResponse(BaseModel):
    ok: bool
    engine: str
    index: str
    indexed: int
    reset: bool
    item_type_id: Optional[str] = None
    note: Optional[str] = None


class EcoReindexRequest(BaseModel):
    state: Optional[str] = Field(default=None)
    reset: bool = Field(default=False)
    limit: Optional[int] = Field(default=None, ge=1)
    batch_size: int = Field(default=200, ge=1, le=2000)


class EcoReindexResponse(BaseModel):
    ok: bool
    engine: str
    index: str
    indexed: int
    reset: bool
    state: Optional[str] = None
    note: Optional[str] = None


class FileSearchResult(BaseModel):
    id: str
    filename: str
    cad_format: Optional[str] = None
    document_type: Optional[str] = None
    document_version: Optional[str] = None
    cad_review_state: Optional[str] = None
    created_at: Optional[str] = None


class FileSearchResponse(BaseModel):
    total: int
    results: list[FileSearchResult]


@search_router.get("/")
def search_items(
    q: str,
    item_type: Optional[str] = None,
    state: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = SearchService(db)
    filters: Dict[str, Any] = {}
    if item_type:
        filters["item_type_id"] = item_type
    if state:
        filters["state"] = state
    return service.search(q, filters=filters, limit=limit)


@search_router.get("/ecos")
def search_ecos(
    q: str = Query("", description="Search text for ECO id/name/description"),
    state: Optional[str] = Query(None, description="Filter by ECO state"),
    limit: int = Query(20, ge=1, le=200),
    _: CurrentUser = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = SearchService(db)
    return service.search_ecos(q, state=state, limit=limit)


@search_router.get("/files", response_model=FileSearchResponse)
def search_files(
    q: str = Query("", description="Search CAD files by id/filename/metadata"),
    limit: int = Query(20, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileSearchResponse:
    service = FileSearchService(db)
    result = service.search_files(q, limit=limit)
    return FileSearchResponse(**result)


@search_router.get("/ecos/status", response_model=SearchStatusResponse)
def search_ecos_status(
    _: CurrentUser = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> SearchStatusResponse:
    service = SearchService(db)
    return SearchStatusResponse(**service.eco_status())


@search_router.get("/indexer/status", response_model=SearchIndexerStatusResponse)
def search_indexer_status(
    _: CurrentUser = Depends(require_admin_user),
) -> SearchIndexerStatusResponse:
    return SearchIndexerStatusResponse(**indexer_status())


@search_router.get("/reports/summary", response_model=None)
def search_reports_summary(
    export_format: Literal["json", "csv"] = Query(
        "json",
        alias="format",
        description="Response format for summary aggregation.",
    ),
    _: CurrentUser = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> SearchReportsSummaryResponse | Response:
    service = SearchService(db)
    summary = SearchReportsSummaryResponse(**service.reports_summary())
    if export_format == "csv":
        return Response(
            content=_format_search_reports_summary_csv(summary),
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="search-reports-summary.csv"'
            },
        )
    return summary


@search_router.get("/reports/eco-stage-aging", response_model=None)
def search_reports_eco_stage_aging(
    export_format: Literal["json", "csv"] = Query(
        "json",
        alias="format",
        description="Response format for ECO stage aging aggregation.",
    ),
    _: CurrentUser = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> SearchEcoStageAgingResponse | Response:
    service = SearchService(db)
    report = SearchEcoStageAgingResponse(**service.eco_stage_aging_report())
    if export_format == "csv":
        return Response(
            content=_format_search_eco_stage_aging_csv(report),
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="search-eco-stage-aging.csv"'
            },
        )
    return report


@search_router.get("/reports/eco-state-trend", response_model=None)
def search_reports_eco_state_trend(
    days: int = Query(
        30,
        ge=1,
        le=366,
        description="Number of UTC calendar days to include.",
    ),
    export_format: Literal["json", "csv"] = Query(
        "json",
        alias="format",
        description="Response format for ECO state trend aggregation.",
    ),
    _: CurrentUser = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> SearchEcoStateTrendResponse | Response:
    service = SearchService(db)
    report = SearchEcoStateTrendResponse(**service.eco_state_trend_report(days=days))
    if export_format == "csv":
        return Response(
            content=_format_search_eco_state_trend_csv(report),
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="search-eco-state-trend.csv"'
            },
        )
    return report


@search_router.post("/ecos/reindex", response_model=EcoReindexResponse)
def search_ecos_reindex(
    req: EcoReindexRequest,
    _: CurrentUser = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> EcoReindexResponse:
    service = SearchService(db)
    result = service.reindex_ecos(
        state=req.state,
        reset=req.reset,
        limit=req.limit,
        batch_size=req.batch_size,
    )
    return EcoReindexResponse(**result)


@search_router.get("/status", response_model=SearchStatusResponse)
def search_status(
    _: CurrentUser = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> SearchStatusResponse:
    service = SearchService(db)
    return SearchStatusResponse(**service.status())


@search_router.post("/reindex", response_model=SearchReindexResponse)
def search_reindex(
    req: SearchReindexRequest,
    _: CurrentUser = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> SearchReindexResponse:
    service = SearchService(db)
    result = service.reindex_items(
        item_type_id=req.item_type_id,
        reset=req.reset,
        limit=req.limit,
        batch_size=req.batch_size,
    )
    return SearchReindexResponse(**result)


def _format_search_reports_summary_csv(summary: SearchReportsSummaryResponse) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["section", "key", "count"])
    writer.writerow(["items.total", "total", summary.items.total])
    for bucket in summary.items.by_item_type:
        writer.writerow(["items.by_item_type", bucket.key, bucket.count])
    for bucket in summary.items.by_state:
        writer.writerow(["items.by_state", bucket.key, bucket.count])
    writer.writerow(["ecos.total", "total", summary.ecos.total])
    for bucket in summary.ecos.by_state:
        writer.writerow(["ecos.by_state", bucket.key, bucket.count])
    for bucket in summary.ecos.by_stage:
        writer.writerow(["ecos.by_stage", bucket.key, bucket.count])
    return buffer.getvalue()


def _format_search_eco_stage_aging_csv(report: SearchEcoStageAgingResponse) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["stage", "count", "avg_age_days", "max_age_days"])
    for bucket in report.buckets:
        writer.writerow(
            [bucket.key, bucket.count, bucket.avg_age_days, bucket.max_age_days]
        )
    return buffer.getvalue()


def _format_search_eco_state_trend_csv(report: SearchEcoStateTrendResponse) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["date", "state", "count"])
    for bucket in report.buckets:
        writer.writerow([bucket.date, bucket.state, bucket.count])
    return buffer.getvalue()
