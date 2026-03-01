from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.job import ConversionJob
from yuantus.meta_engine.models.parallel_tasks import (
    BreakageIncident,
    ConsumptionPlan,
    ConsumptionRecord,
    ECOActivityGate,
    ECOActivityGateEvent,
    RemoteSite,
    ThreeDOverlay,
    WorkflowCustomActionRule,
    WorkflowCustomActionRun,
    WorkorderDocumentLink,
)
from yuantus.meta_engine.services.parallel_tasks_service import (
    BreakageIncidentService,
    ConsumptionPlanService,
    ThreeDOverlayService,
)
from yuantus.models.base import Base
from yuantus.security.rbac.models import RBACUser


def _client_with_real_db(user):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[
            RBACUser.__table__,
            RemoteSite.__table__,
            ECOActivityGate.__table__,
            ECOActivityGateEvent.__table__,
            WorkflowCustomActionRule.__table__,
            WorkflowCustomActionRun.__table__,
            ConsumptionPlan.__table__,
            ConsumptionRecord.__table__,
            BreakageIncident.__table__,
            WorkorderDocumentLink.__table__,
            ThreeDOverlay.__table__,
            ConversionJob.__table__,
        ],
    )
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    db = SessionLocal()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_get_current_user():
        return user

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app), db


def test_parallel_ops_endpoints_e2e_with_real_service_data():
    user = SimpleNamespace(id=21, roles=["admin", "engineer"], is_superuser=False)
    client, db = _client_with_real_db(user)

    ThreeDOverlayService.reset_cache_for_tests()
    overlay_service = ThreeDOverlayService(db)
    overlay_service.upsert_overlay(
        document_item_id="doc-e2e-1",
        visibility_role="engineer",
        part_refs=[{"component_ref": "E2E-1", "item_id": "item-e2e-1"}],
    )
    db.commit()

    _ = overlay_service.get_overlay(document_item_id="doc-e2e-1", user_roles=["engineer"])
    _ = overlay_service.get_overlay(document_item_id="doc-e2e-1", user_roles=["engineer"])

    now = datetime.utcnow()
    db.add_all(
        [
            ConversionJob(
                id="e2e-sync-ok",
                task_type="document_sync_push",
                status="completed",
                payload={"site_id": "site-e2e"},
                attempt_count=1,
                max_attempts=3,
                created_at=now - timedelta(hours=2),
            ),
            ConversionJob(
                id="e2e-sync-fail",
                task_type="document_sync_pull",
                status="failed",
                payload={"site_id": "site-e2e"},
                attempt_count=3,
                max_attempts=3,
                created_at=now - timedelta(hours=1),
            ),
        ]
    )
    db.add(
        WorkflowCustomActionRun(
            id="e2e-wf-fail",
            rule_id="e2e-rule-1",
            object_id="eco-e2e-1",
            target_object="ECO",
            from_state="draft",
            to_state="progress",
            trigger_phase="before",
            status="failed",
            attempts=3,
            result={"result_code": "RETRY_EXHAUSTED"},
            created_at=now - timedelta(hours=1),
        )
    )

    breakage_service = BreakageIncidentService(db)
    breakage_incident = breakage_service.create_incident(
        description="e2e-bearing-crack",
        severity="high",
        status="open",
        product_item_id="prod-e2e-1",
        bom_line_item_id="bom-e2e-1",
        batch_code="batch-e2e-1",
        responsibility="supplier-e2e",
    )

    consumption_service = ConsumptionPlanService(db)
    consumption_service.create_template_version(
        template_key="tpl-e2e",
        name="tpl-e2e-v1",
        planned_quantity=10.0,
        version_label="v1",
        activate=True,
    )
    db.commit()

    breakage_metrics_export_csv_resp = client.get(
        "/api/v1/breakages/metrics/export?trend_window_days=14&responsibility=supplier-e2e&bom_line_item_id=bom-e2e-1&export_format=csv"
    )
    assert breakage_metrics_export_csv_resp.status_code == 200
    assert breakage_metrics_export_csv_resp.headers.get("content-type", "").startswith(
        "text/csv"
    )
    assert breakage_metrics_export_csv_resp.headers.get("x-operator-id") == "21"
    assert "bom_line_item_id_filter" in breakage_metrics_export_csv_resp.text
    assert "bom-e2e-1" in breakage_metrics_export_csv_resp.text
    assert "responsibility_filter" in breakage_metrics_export_csv_resp.text

    breakage_metrics_resp = client.get(
        "/api/v1/breakages/metrics?trend_window_days=14&responsibility=supplier-e2e&bom_line_item_id=bom-e2e-1"
    )
    assert breakage_metrics_resp.status_code == 200
    breakage_metrics = breakage_metrics_resp.json()
    assert breakage_metrics["by_product_item"]["prod-e2e-1"] == 1
    assert breakage_metrics["by_batch_code"]["batch-e2e-1"] == 1
    assert breakage_metrics["by_bom_line_item"]["bom-e2e-1"] == 1
    assert breakage_metrics["top_product_items"][0]["product_item_id"] == "prod-e2e-1"
    assert breakage_metrics["top_batch_codes"][0]["batch_code"] == "batch-e2e-1"
    assert breakage_metrics["top_bom_line_items"][0]["bom_line_item_id"] == "bom-e2e-1"
    assert breakage_metrics["filters"]["bom_line_item_id"] == "bom-e2e-1"
    assert breakage_metrics["operator_id"] == 21

    breakage_list_resp = client.get("/api/v1/breakages?bom_line_item_id=bom-e2e-1")
    assert breakage_list_resp.status_code == 200
    breakage_list = breakage_list_resp.json()
    assert breakage_list["total"] == 1
    assert breakage_list["incidents"][0]["id"] == breakage_incident.id
    assert breakage_list["incidents"][0]["bom_line_item_id"] == "bom-e2e-1"
    assert breakage_list["operator_id"] == 21

    breakage_export_csv_resp = client.get(
        "/api/v1/breakages/export?bom_line_item_id=bom-e2e-1&export_format=csv&page=1&page_size=10"
    )
    assert breakage_export_csv_resp.status_code == 200
    assert breakage_export_csv_resp.headers.get("content-type", "").startswith("text/csv")
    assert breakage_export_csv_resp.headers.get("x-operator-id") == "21"
    assert "bom_line_item_id_filter" in breakage_export_csv_resp.text
    assert "bom-e2e-1" in breakage_export_csv_resp.text

    breakage_export_job_create_resp = client.post(
        "/api/v1/breakages/export/jobs",
        json={
            "bom_line_item_id": "bom-e2e-1",
            "page": 1,
            "page_size": 10,
            "export_format": "csv",
            "execute_immediately": True,
        },
    )
    assert breakage_export_job_create_resp.status_code == 200
    breakage_export_job = breakage_export_job_create_resp.json()
    assert breakage_export_job["job_id"]
    assert breakage_export_job["download_ready"] is True
    assert breakage_export_job["operator_id"] == 21

    breakage_export_job_status_resp = client.get(
        f"/api/v1/breakages/export/jobs/{breakage_export_job['job_id']}"
    )
    assert breakage_export_job_status_resp.status_code == 200
    breakage_export_job_status = breakage_export_job_status_resp.json()
    assert breakage_export_job_status["job_id"] == breakage_export_job["job_id"]
    assert breakage_export_job_status["status"] == "completed"
    assert breakage_export_job_status["operator_id"] == 21

    breakage_export_job_download_resp = client.get(
        f"/api/v1/breakages/export/jobs/{breakage_export_job['job_id']}/download"
    )
    assert breakage_export_job_download_resp.status_code == 200
    assert breakage_export_job_download_resp.headers.get("content-type", "").startswith(
        "text/csv"
    )
    assert breakage_export_job_download_resp.headers.get("x-operator-id") == "21"
    assert "bom_line_item_id_filter" in breakage_export_job_download_resp.text
    assert "bom-e2e-1" in breakage_export_job_download_resp.text

    breakage_groups_resp = client.get(
        "/api/v1/breakages/metrics/groups?group_by=responsibility&trend_window_days=14&bom_line_item_id=bom-e2e-1&page=1&page_size=10"
    )
    assert breakage_groups_resp.status_code == 200
    breakage_groups = breakage_groups_resp.json()
    assert breakage_groups["group_by"] == "responsibility"
    assert breakage_groups["total_groups"] >= 1
    assert breakage_groups["groups"][0]["group_value"] == "supplier-e2e"
    assert breakage_groups["groups"][0]["count"] == 1
    assert breakage_groups["filters"]["bom_line_item_id"] == "bom-e2e-1"
    assert breakage_groups["operator_id"] == 21

    breakage_groups_bom_line_resp = client.get(
        "/api/v1/breakages/metrics/groups?group_by=bom_line_item_id&trend_window_days=14&page=1&page_size=10"
    )
    assert breakage_groups_bom_line_resp.status_code == 200
    breakage_groups_bom_line = breakage_groups_bom_line_resp.json()
    assert breakage_groups_bom_line["group_by"] == "bom_line_item_id"
    assert breakage_groups_bom_line["groups"][0]["group_value"] == "bom-e2e-1"
    assert breakage_groups_bom_line["groups"][0]["count"] == 1
    assert breakage_groups_bom_line["operator_id"] == 21

    breakage_groups_export_md_resp = client.get(
        "/api/v1/breakages/metrics/groups/export?group_by=responsibility&trend_window_days=14&responsibility=supplier-e2e&bom_line_item_id=bom-e2e-1&export_format=md"
    )
    assert breakage_groups_export_md_resp.status_code == 200
    assert breakage_groups_export_md_resp.headers.get("content-type", "").startswith(
        "text/markdown"
    )
    assert breakage_groups_export_md_resp.headers.get("x-operator-id") == "21"
    assert "# Breakage Metrics Groups" in breakage_groups_export_md_resp.text
    assert "bom_line_item_id" in breakage_groups_export_md_resp.text
    assert "supplier-e2e" in breakage_groups_export_md_resp.text

    helpdesk_sync_resp = client.post(
        f"/api/v1/breakages/{breakage_incident.id}/helpdesk-sync",
        json={"metadata_json": {"channel": "e2e"}},
    )
    assert helpdesk_sync_resp.status_code == 200
    helpdesk_sync = helpdesk_sync_resp.json()
    assert helpdesk_sync["incident_id"] == breakage_incident.id
    assert helpdesk_sync["task_type"] == "breakage_helpdesk_sync_stub"

    helpdesk_status_resp = client.get(
        f"/api/v1/breakages/{breakage_incident.id}/helpdesk-sync/status"
    )
    assert helpdesk_status_resp.status_code == 200
    helpdesk_status = helpdesk_status_resp.json()
    assert helpdesk_status["incident_id"] == breakage_incident.id
    assert helpdesk_status["sync_status"] in {"queued", "pending"}
    assert helpdesk_status["operator_id"] == 21

    helpdesk_execute_failed_resp = client.post(
        f"/api/v1/breakages/{breakage_incident.id}/helpdesk-sync/execute",
        json={
            "job_id": helpdesk_sync["job_id"],
            "simulate_status": "failed",
            "error_code": "timeout",
            "error_message": "upstream timeout",
        },
    )
    assert helpdesk_execute_failed_resp.status_code == 200
    helpdesk_execute_failed = helpdesk_execute_failed_resp.json()
    assert helpdesk_execute_failed["incident_id"] == breakage_incident.id
    assert helpdesk_execute_failed["sync_status"] == "failed"
    assert helpdesk_execute_failed["last_job"]["failure_category"] == "transient"
    assert helpdesk_execute_failed["operator_id"] == 21

    helpdesk_execute_completed_resp = client.post(
        f"/api/v1/breakages/{breakage_incident.id}/helpdesk-sync/execute",
        json={
            "job_id": helpdesk_sync["job_id"],
            "simulate_status": "completed",
            "external_ticket_id": "HD-E2E-1",
        },
    )
    assert helpdesk_execute_completed_resp.status_code == 200
    helpdesk_execute_completed = helpdesk_execute_completed_resp.json()
    assert helpdesk_execute_completed["sync_status"] == "completed"
    assert helpdesk_execute_completed["external_ticket_id"] == "HD-E2E-1"
    assert helpdesk_execute_completed["operator_id"] == 21

    helpdesk_result_resp = client.post(
        f"/api/v1/breakages/{breakage_incident.id}/helpdesk-sync/result",
        json={
            "job_id": helpdesk_sync["job_id"],
            "sync_status": "completed",
            "external_ticket_id": "HD-E2E-1",
        },
    )
    assert helpdesk_result_resp.status_code == 200
    helpdesk_result = helpdesk_result_resp.json()
    assert helpdesk_result["incident_id"] == breakage_incident.id
    assert helpdesk_result["sync_status"] == "completed"
    assert helpdesk_result["external_ticket_id"] == "HD-E2E-1"
    assert helpdesk_result["operator_id"] == 21

    helpdesk_status_done_resp = client.get(
        f"/api/v1/breakages/{breakage_incident.id}/helpdesk-sync/status"
    )
    assert helpdesk_status_done_resp.status_code == 200
    helpdesk_status_done = helpdesk_status_done_resp.json()
    assert helpdesk_status_done["sync_status"] == "completed"
    assert helpdesk_status_done["external_ticket_id"] == "HD-E2E-1"
    assert helpdesk_status_done["operator_id"] == 21

    breakage_cockpit_resp = client.get(
        "/api/v1/breakages/cockpit?trend_window_days=14&responsibility=supplier-e2e&page=1&page_size=10"
    )
    assert breakage_cockpit_resp.status_code == 200
    breakage_cockpit = breakage_cockpit_resp.json()
    assert breakage_cockpit["total"] >= 1
    assert breakage_cockpit["metrics"]["by_responsibility"]["supplier-e2e"] >= 1
    assert breakage_cockpit["helpdesk_sync_summary"]["total_jobs"] >= 1
    assert breakage_cockpit["operator_id"] == 21

    breakage_cockpit_export_md_resp = client.get(
        "/api/v1/breakages/cockpit/export?trend_window_days=14&responsibility=supplier-e2e&page=1&page_size=10&export_format=md"
    )
    assert breakage_cockpit_export_md_resp.status_code == 200
    assert breakage_cockpit_export_md_resp.headers.get("content-type", "").startswith(
        "text/markdown"
    )
    assert breakage_cockpit_export_md_resp.headers.get("x-operator-id") == "21"
    assert "# Breakage Cockpit" in breakage_cockpit_export_md_resp.text

    summary_resp = client.get(
        "/api/v1/parallel-ops/summary?window_days=7&site_id=site-e2e&target_object=ECO&template_key=tpl-e2e"
    )
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["doc_sync"]["total"] == 2
    assert summary["workflow_actions"]["total"] == 1
    assert summary["breakages"]["total"] == 1
    assert summary["consumption_templates"]["versions_total"] == 1
    assert summary["operator_id"] == 21

    relaxed_summary_resp = client.get(
        "/api/v1/parallel-ops/summary?window_days=7&site_id=site-e2e&target_object=ECO&template_key=tpl-e2e&overlay_cache_hit_rate_warn=0.1&overlay_cache_min_requests_warn=999&doc_sync_dead_letter_rate_warn=1.0&workflow_failed_rate_warn=1.0&breakage_open_rate_warn=1.0"
    )
    assert relaxed_summary_resp.status_code == 200
    relaxed_summary = relaxed_summary_resp.json()
    assert relaxed_summary.get("slo_hints") == []

    trends_resp = client.get(
        "/api/v1/parallel-ops/trends?window_days=7&bucket_days=1&site_id=site-e2e&target_object=ECO&template_key=tpl-e2e"
    )
    assert trends_resp.status_code == 200
    trends = trends_resp.json()
    assert trends["bucket_days"] == 1
    assert trends["aggregates"]["doc_sync_total"] == 2
    assert trends["aggregates"]["doc_sync_failed_total"] == 1
    assert trends["aggregates"]["workflow_total"] == 1
    assert trends["aggregates"]["breakages_total"] == 1
    assert len(trends["points"]) >= 1
    assert trends["operator_id"] == 21

    trends_export_csv_resp = client.get(
        "/api/v1/parallel-ops/trends/export?window_days=7&bucket_days=1&site_id=site-e2e&target_object=ECO&template_key=tpl-e2e&export_format=csv"
    )
    assert trends_export_csv_resp.status_code == 200
    assert trends_export_csv_resp.headers.get("content-type", "").startswith("text/csv")
    assert trends_export_csv_resp.headers.get("x-operator-id") == "21"
    assert "doc_sync_total" in trends_export_csv_resp.text

    alerts_resp = client.get(
        "/api/v1/parallel-ops/alerts?window_days=7&site_id=site-e2e&target_object=ECO&template_key=tpl-e2e&level=warn"
    )
    assert alerts_resp.status_code == 200
    alerts = alerts_resp.json()
    assert alerts["status"] == "warning"
    assert alerts["total"] >= 1
    assert alerts["operator_id"] == 21

    relaxed_alerts_resp = client.get(
        "/api/v1/parallel-ops/alerts?window_days=7&site_id=site-e2e&target_object=ECO&template_key=tpl-e2e&level=warn&overlay_cache_hit_rate_warn=0.1&overlay_cache_min_requests_warn=999&doc_sync_dead_letter_rate_warn=1.0&workflow_failed_rate_warn=1.0&breakage_open_rate_warn=1.0"
    )
    assert relaxed_alerts_resp.status_code == 200
    relaxed_alerts = relaxed_alerts_resp.json()
    assert relaxed_alerts["status"] == "ok"
    assert relaxed_alerts["total"] == 0

    summary_export_json_resp = client.get(
        "/api/v1/parallel-ops/summary/export?window_days=7&site_id=site-e2e&target_object=ECO&template_key=tpl-e2e&export_format=json"
    )
    assert summary_export_json_resp.status_code == 200
    assert summary_export_json_resp.headers.get("content-type", "").startswith(
        "application/json"
    )
    assert summary_export_json_resp.headers.get("x-operator-id") == "21"
    assert '"doc_sync"' in summary_export_json_resp.text

    summary_export_csv_resp = client.get(
        "/api/v1/parallel-ops/summary/export?window_days=7&site_id=site-e2e&target_object=ECO&template_key=tpl-e2e&export_format=csv"
    )
    assert summary_export_csv_resp.status_code == 200
    assert summary_export_csv_resp.headers.get("content-type", "").startswith("text/csv")
    assert "metric,value" in summary_export_csv_resp.text
    assert "doc_sync.total,2" in summary_export_csv_resp.text

    summary_export_md_resp = client.get(
        "/api/v1/parallel-ops/summary/export?window_days=7&site_id=site-e2e&target_object=ECO&template_key=tpl-e2e&export_format=md"
    )
    assert summary_export_md_resp.status_code == 200
    assert summary_export_md_resp.headers.get("content-type", "").startswith(
        "text/markdown"
    )
    assert summary_export_md_resp.text.startswith("# Parallel Ops Summary")

    doc_sync_failures_resp = client.get(
        "/api/v1/parallel-ops/doc-sync/failures?window_days=7&site_id=site-e2e&page=1&page_size=10"
    )
    assert doc_sync_failures_resp.status_code == 200
    doc_sync_failures = doc_sync_failures_resp.json()
    assert doc_sync_failures["total"] == 1
    assert doc_sync_failures["jobs"][0]["id"] == "e2e-sync-fail"

    workflow_failures_resp = client.get(
        "/api/v1/parallel-ops/workflow/failures?window_days=7&target_object=ECO&page=1&page_size=10"
    )
    assert workflow_failures_resp.status_code == 200
    workflow_failures = workflow_failures_resp.json()
    assert workflow_failures["total"] == 1
    assert workflow_failures["runs"][0]["id"] == "e2e-wf-fail"

    metrics_resp = client.get(
        "/api/v1/parallel-ops/metrics?window_days=7&site_id=site-e2e&target_object=ECO&template_key=tpl-e2e"
    )
    assert metrics_resp.status_code == 200
    assert metrics_resp.headers.get("content-type", "").startswith("text/plain")
    assert metrics_resp.headers.get("x-operator-id") == "21"
    assert "yuantus_parallel_doc_sync_jobs_total" in metrics_resp.text
    assert 'site_id="site-e2e"' in metrics_resp.text
