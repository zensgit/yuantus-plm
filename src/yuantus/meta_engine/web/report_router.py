from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

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
    return service.get_summary()
