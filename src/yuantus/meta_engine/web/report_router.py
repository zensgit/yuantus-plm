from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from yuantus.config import get_settings
from yuantus.context import get_request_context
from yuantus.database import get_db
from yuantus.meta_engine.services.report_service import ReportService
from yuantus.api.dependencies.auth import get_current_user_optional

report_router = APIRouter(prefix="/reports", tags=["Reports"])


@report_router.get("/summary")
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
