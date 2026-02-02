"""Report definition execution services."""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from yuantus.meta_engine.reports.models import Dashboard, ReportDefinition, ReportExecution
from yuantus.meta_engine.reports.search_service import AdvancedSearchService


class ReportDefinitionService:
    def __init__(self, session: Session):
        self.session = session
        self.search_service = AdvancedSearchService(session)

    def create_definition(
        self,
        *,
        name: str,
        code: Optional[str],
        description: Optional[str],
        category: Optional[str],
        report_type: str,
        data_source: Dict[str, Any],
        layout: Optional[Dict[str, Any]],
        parameters: Optional[List[Dict[str, Any]]],
        owner_id: Optional[int],
        is_public: bool,
        allowed_roles: Optional[List[str]],
        is_active: bool,
        created_by_id: Optional[int],
    ) -> ReportDefinition:
        report = ReportDefinition(
            name=name,
            code=code,
            description=description,
            category=category,
            report_type=report_type,
            data_source=data_source,
            layout=layout,
            parameters=parameters,
            owner_id=owner_id,
            is_public=is_public,
            allowed_roles=allowed_roles,
            is_active=is_active,
            created_by_id=created_by_id,
        )
        self.session.add(report)
        self.session.commit()
        return report

    def list_definitions(
        self,
        *,
        owner_id: Optional[int],
        include_public: bool = True,
        active_only: bool = True,
    ) -> List[ReportDefinition]:
        q = self.session.query(ReportDefinition)
        if active_only:
            q = q.filter(ReportDefinition.is_active.is_(True))
        if owner_id is not None and include_public:
            q = q.filter(
                (ReportDefinition.owner_id == owner_id)
                | (ReportDefinition.is_public.is_(True))
            )
        elif owner_id is not None:
            q = q.filter(ReportDefinition.owner_id == owner_id)
        elif include_public:
            q = q.filter(ReportDefinition.is_public.is_(True))
        return q.order_by(ReportDefinition.created_at.desc()).all()

    def get_definition(self, report_id: str) -> Optional[ReportDefinition]:
        return self.session.get(ReportDefinition, report_id)

    def update_definition(
        self,
        report_id: str,
        *,
        name: Optional[str] = None,
        code: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        report_type: Optional[str] = None,
        data_source: Optional[Dict[str, Any]] = None,
        layout: Optional[Dict[str, Any]] = None,
        parameters: Optional[List[Dict[str, Any]]] = None,
        is_public: Optional[bool] = None,
        allowed_roles: Optional[List[str]] = None,
        is_active: Optional[bool] = None,
    ) -> ReportDefinition:
        report = self.get_definition(report_id)
        if not report:
            raise ValueError("Report definition not found")

        if name is not None:
            report.name = name
        if code is not None:
            report.code = code
        if description is not None:
            report.description = description
        if category is not None:
            report.category = category
        if report_type is not None:
            report.report_type = report_type
        if data_source is not None:
            report.data_source = data_source
        if layout is not None:
            report.layout = layout
        if parameters is not None:
            report.parameters = parameters
        if is_public is not None:
            report.is_public = is_public
        if allowed_roles is not None:
            report.allowed_roles = allowed_roles
        if is_active is not None:
            report.is_active = is_active

        self.session.add(report)
        self.session.commit()
        return report

    def delete_definition(self, report_id: str) -> None:
        report = self.get_definition(report_id)
        if not report:
            raise ValueError("Report definition not found")
        self.session.delete(report)
        self.session.commit()

    def execute_definition(
        self,
        report_id: str,
        *,
        parameters: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 200,
    ) -> Dict[str, Any]:
        report = self.get_definition(report_id)
        if not report:
            raise ValueError("Report definition not found")

        execution = ReportExecution(
            report_id=report.id,
            parameters_used=parameters,
            status="running",
            executed_by_id=user_id,
        )
        self.session.add(execution)
        self.session.flush()

        start = time.perf_counter()
        try:
            data = self._execute_data_source(report, parameters, page, page_size)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            execution.status = "completed"
            execution.row_count = len(data.get("items") or [])
            execution.execution_time_ms = elapsed_ms
            execution.completed_at = datetime.utcnow()
            self.session.add(execution)
            self.session.commit()
            return {
                "execution_id": execution.id,
                "status": execution.status,
                "row_count": execution.row_count,
                "execution_time_ms": execution.execution_time_ms,
                "data": data,
            }
        except Exception as exc:  # pragma: no cover - handled for observability
            execution.status = "failed"
            execution.error_message = str(exc)
            execution.completed_at = datetime.utcnow()
            self.session.add(execution)
            self.session.commit()
            raise

    def _execute_data_source(
        self,
        report: ReportDefinition,
        parameters: Optional[Dict[str, Any]],
        page: int,
        page_size: int,
    ) -> Dict[str, Any]:
        data_source = dict(report.data_source or {})
        if parameters:
            data_source.update(parameters)

        source_type = data_source.get("type", "query")

        if source_type == "saved_search":
            saved_search_id = data_source.get("saved_search_id")
            if not saved_search_id:
                raise ValueError("saved_search_id required for saved_search data source")
            from yuantus.meta_engine.reports.search_service import SavedSearchService

            saved_search_service = SavedSearchService(self.session)
            return saved_search_service.run_saved_search(
                saved_search_id,
                page=page,
                page_size=page_size,
            )

        if source_type == "query":
            return self.search_service.search(
                item_type_id=data_source.get("item_type_id"),
                filters=data_source.get("filters"),
                full_text=data_source.get("full_text"),
                sort=data_source.get("sort"),
                columns=data_source.get("columns"),
                page=page,
                page_size=page_size,
                include_count=True,
            )

        raise ValueError(f"Unsupported data source type: {source_type}")


class DashboardService:
    def __init__(self, session: Session):
        self.session = session

    def create_dashboard(
        self,
        *,
        name: str,
        description: Optional[str],
        layout: Optional[Dict[str, Any]],
        widgets: Optional[List[Dict[str, Any]]],
        auto_refresh: bool,
        refresh_interval: int,
        owner_id: Optional[int],
        is_public: bool,
        is_default: bool,
        created_by_id: Optional[int],
    ) -> Dashboard:
        dashboard = Dashboard(
            name=name,
            description=description,
            layout=layout,
            widgets=widgets,
            auto_refresh=auto_refresh,
            refresh_interval=refresh_interval,
            owner_id=owner_id,
            is_public=is_public,
            is_default=is_default,
            created_by_id=created_by_id,
        )
        self.session.add(dashboard)
        self.session.commit()
        return dashboard

    def list_dashboards(
        self,
        *,
        owner_id: Optional[int],
        include_public: bool = True,
    ) -> List[Dashboard]:
        q = self.session.query(Dashboard)
        if owner_id is not None and include_public:
            q = q.filter((Dashboard.owner_id == owner_id) | (Dashboard.is_public.is_(True)))
        elif owner_id is not None:
            q = q.filter(Dashboard.owner_id == owner_id)
        elif include_public:
            q = q.filter(Dashboard.is_public.is_(True))
        return q.order_by(Dashboard.created_at.desc()).all()

    def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        return self.session.get(Dashboard, dashboard_id)

    def update_dashboard(
        self,
        dashboard_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        layout: Optional[Dict[str, Any]] = None,
        widgets: Optional[List[Dict[str, Any]]] = None,
        auto_refresh: Optional[bool] = None,
        refresh_interval: Optional[int] = None,
        is_public: Optional[bool] = None,
        is_default: Optional[bool] = None,
    ) -> Dashboard:
        dashboard = self.get_dashboard(dashboard_id)
        if not dashboard:
            raise ValueError("Dashboard not found")

        if name is not None:
            dashboard.name = name
        if description is not None:
            dashboard.description = description
        if layout is not None:
            dashboard.layout = layout
        if widgets is not None:
            dashboard.widgets = widgets
        if auto_refresh is not None:
            dashboard.auto_refresh = auto_refresh
        if refresh_interval is not None:
            dashboard.refresh_interval = refresh_interval
        if is_public is not None:
            dashboard.is_public = is_public
        if is_default is not None:
            dashboard.is_default = is_default

        self.session.add(dashboard)
        self.session.commit()
        return dashboard

    def delete_dashboard(self, dashboard_id: str) -> None:
        dashboard = self.get_dashboard(dashboard_id)
        if not dashboard:
            raise ValueError("Dashboard not found")
        self.session.delete(dashboard)
        self.session.commit()
