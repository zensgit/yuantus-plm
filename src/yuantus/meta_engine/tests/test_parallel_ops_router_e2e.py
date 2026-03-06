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
    breakage_incident_failed = breakage_service.create_incident(
        description="e2e-bearing-timeout",
        severity="medium",
        status="open",
        product_item_id="prod-e2e-2",
        bom_line_item_id="bom-e2e-2",
        batch_code="batch-e2e-2",
        responsibility="supplier-e2e",
    )
    breakage_failed_job = breakage_service.enqueue_helpdesk_stub_sync(
        breakage_incident_failed.id,
        user_id=21,
        provider="zendesk",
        idempotency_key="ops-e2e-failed-1",
    )
    breakage_service.record_helpdesk_sync_result(
        breakage_incident_failed.id,
        sync_status="failed",
        job_id=breakage_failed_job.id,
        error_code="provider_timeout",
        error_message="upstream timeout",
        user_id=21,
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

    export_job_row = db.get(ConversionJob, breakage_export_job["job_id"])
    assert export_job_row is not None
    export_job_row.completed_at = datetime.utcnow() - timedelta(hours=25)
    db.add(export_job_row)
    db.commit()

    breakage_export_cleanup_resp = client.post(
        "/api/v1/breakages/export/jobs/cleanup",
        json={"ttl_hours": 24, "limit": 50},
    )
    assert breakage_export_cleanup_resp.status_code == 200
    breakage_export_cleanup = breakage_export_cleanup_resp.json()
    assert breakage_export_cleanup["expired_jobs"] >= 1
    assert breakage_export_cleanup["operator_id"] == 21

    breakage_export_job_status_after_cleanup_resp = client.get(
        f"/api/v1/breakages/export/jobs/{breakage_export_job['job_id']}"
    )
    assert breakage_export_job_status_after_cleanup_resp.status_code == 200
    breakage_export_job_status_after_cleanup = (
        breakage_export_job_status_after_cleanup_resp.json()
    )
    assert breakage_export_job_status_after_cleanup["download_ready"] is False
    assert breakage_export_job_status_after_cleanup["sync_status"] == "expired"

    breakage_export_job_download_after_cleanup_resp = client.get(
        f"/api/v1/breakages/export/jobs/{breakage_export_job['job_id']}/download"
    )
    assert breakage_export_job_download_after_cleanup_resp.status_code == 400

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
    by_bom_line_group = {
        row["group_value"]: row["count"] for row in (breakage_groups_bom_line["groups"] or [])
    }
    assert by_bom_line_group["bom-e2e-1"] == 1
    assert by_bom_line_group["bom-e2e-2"] == 1
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
    assert breakage_cockpit["helpdesk_sync_summary"]["providers_total"] >= 1
    assert breakage_cockpit["helpdesk_sync_summary"]["by_provider"]["stub"] >= 1
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
    assert summary["breakages"]["total"] == 2
    assert summary["breakages"]["helpdesk"]["total_jobs"] >= 1
    assert summary["breakages"]["helpdesk"]["replay_jobs_total"] == 0
    assert summary["breakages"]["helpdesk"]["replay_batches_total"] == 0
    assert summary["breakages"]["helpdesk"]["by_provider"]["stub"] >= 1
    assert summary["breakages"]["helpdesk"]["replay_by_provider"] == {}
    assert summary["consumption_templates"]["versions_total"] == 1
    assert summary["operator_id"] == 21

    relaxed_summary_resp = client.get(
        "/api/v1/parallel-ops/summary?window_days=7&site_id=site-e2e&target_object=ECO&template_key=tpl-e2e&overlay_cache_hit_rate_warn=0.1&overlay_cache_min_requests_warn=999&doc_sync_dead_letter_rate_warn=1.0&workflow_failed_rate_warn=1.0&breakage_open_rate_warn=1.0&breakage_helpdesk_failed_rate_warn=0.9&breakage_helpdesk_failed_total_warn=99&breakage_helpdesk_triage_coverage_warn=0.0&breakage_helpdesk_export_failed_total_warn=99&breakage_helpdesk_provider_failed_rate_warn=1.0&breakage_helpdesk_provider_failed_min_jobs_warn=99&breakage_helpdesk_provider_failed_rate_critical=1.0&breakage_helpdesk_provider_failed_min_jobs_critical=999"
    )
    assert relaxed_summary_resp.status_code == 200
    relaxed_summary = relaxed_summary_resp.json()
    assert relaxed_summary.get("slo_hints") == []
    assert (
        relaxed_summary["slo_thresholds"]["breakage_helpdesk_provider_failed_rate_critical"]
        == 1.0
    )
    assert (
        relaxed_summary["slo_thresholds"]["breakage_helpdesk_provider_failed_min_jobs_critical"]
        == 999
    )

    strict_helpdesk_summary_resp = client.get(
        "/api/v1/parallel-ops/summary?window_days=7&site_id=site-e2e&target_object=ECO&template_key=tpl-e2e&overlay_cache_hit_rate_warn=0.1&overlay_cache_min_requests_warn=999&doc_sync_dead_letter_rate_warn=1.0&workflow_failed_rate_warn=1.0&breakage_open_rate_warn=1.0&breakage_helpdesk_failed_rate_warn=0.1&breakage_helpdesk_failed_total_warn=0&breakage_helpdesk_provider_failed_rate_warn=0.5&breakage_helpdesk_provider_failed_min_jobs_warn=1"
    )
    assert strict_helpdesk_summary_resp.status_code == 200
    strict_helpdesk_summary = strict_helpdesk_summary_resp.json()
    strict_hint_codes = {row["code"] for row in (strict_helpdesk_summary.get("slo_hints") or [])}
    assert "breakage_helpdesk_failed_rate_high" in strict_hint_codes
    assert "breakage_helpdesk_failed_total_high" in strict_hint_codes
    assert "breakage_helpdesk_triage_coverage_low" in strict_hint_codes
    assert "breakage_helpdesk_provider_failed_rate_high" in strict_hint_codes

    critical_helpdesk_summary_resp = client.get(
        "/api/v1/parallel-ops/summary?window_days=7&site_id=site-e2e&target_object=ECO&template_key=tpl-e2e&overlay_cache_hit_rate_warn=0.1&overlay_cache_min_requests_warn=999&doc_sync_dead_letter_rate_warn=1.0&workflow_failed_rate_warn=1.0&breakage_open_rate_warn=1.0&breakage_helpdesk_failed_rate_warn=0.9&breakage_helpdesk_failed_total_warn=99&breakage_helpdesk_provider_failed_rate_warn=0.99&breakage_helpdesk_provider_failed_min_jobs_warn=99&breakage_helpdesk_provider_failed_rate_critical=0.5&breakage_helpdesk_provider_failed_min_jobs_critical=1"
    )
    assert critical_helpdesk_summary_resp.status_code == 200
    critical_helpdesk_summary = critical_helpdesk_summary_resp.json()
    assert any(
        row.get("code") == "breakage_helpdesk_provider_failed_rate_critical"
        and row.get("level") == "critical"
        for row in (critical_helpdesk_summary.get("slo_hints") or [])
    )

    trends_resp = client.get(
        "/api/v1/parallel-ops/trends?window_days=7&bucket_days=1&site_id=site-e2e&target_object=ECO&template_key=tpl-e2e"
    )
    assert trends_resp.status_code == 200
    trends = trends_resp.json()
    assert trends["bucket_days"] == 1
    assert trends["aggregates"]["doc_sync_total"] == 2
    assert trends["aggregates"]["doc_sync_failed_total"] == 1
    assert trends["aggregates"]["workflow_total"] == 1
    assert trends["aggregates"]["breakages_total"] == 2
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
        "/api/v1/parallel-ops/alerts?window_days=7&site_id=site-e2e&target_object=ECO&template_key=tpl-e2e&level=warn&overlay_cache_hit_rate_warn=0.1&overlay_cache_min_requests_warn=999&doc_sync_dead_letter_rate_warn=1.0&workflow_failed_rate_warn=1.0&breakage_open_rate_warn=1.0&breakage_helpdesk_failed_rate_warn=0.9&breakage_helpdesk_failed_total_warn=99&breakage_helpdesk_triage_coverage_warn=0.0&breakage_helpdesk_export_failed_total_warn=99&breakage_helpdesk_provider_failed_rate_warn=1.0&breakage_helpdesk_provider_failed_min_jobs_warn=99&breakage_helpdesk_provider_failed_rate_critical=1.0&breakage_helpdesk_provider_failed_min_jobs_critical=999"
    )
    assert relaxed_alerts_resp.status_code == 200
    relaxed_alerts = relaxed_alerts_resp.json()
    assert relaxed_alerts["status"] == "ok"
    assert relaxed_alerts["total"] == 0

    strict_helpdesk_alerts_resp = client.get(
        "/api/v1/parallel-ops/alerts?window_days=7&site_id=site-e2e&target_object=ECO&template_key=tpl-e2e&level=warn&overlay_cache_hit_rate_warn=0.1&overlay_cache_min_requests_warn=999&doc_sync_dead_letter_rate_warn=1.0&workflow_failed_rate_warn=1.0&breakage_open_rate_warn=1.0&breakage_helpdesk_failed_rate_warn=0.1&breakage_helpdesk_failed_total_warn=0&breakage_helpdesk_provider_failed_rate_warn=0.5&breakage_helpdesk_provider_failed_min_jobs_warn=1"
    )
    assert strict_helpdesk_alerts_resp.status_code == 200
    strict_helpdesk_alerts = strict_helpdesk_alerts_resp.json()
    assert strict_helpdesk_alerts["by_code"].get("breakage_helpdesk_failed_rate_high", 0) >= 1
    assert strict_helpdesk_alerts["by_code"].get("breakage_helpdesk_failed_total_high", 0) >= 1
    assert (
        strict_helpdesk_alerts["by_code"].get("breakage_helpdesk_provider_failed_rate_high", 0)
        >= 1
    )
    critical_helpdesk_alerts_resp = client.get(
        "/api/v1/parallel-ops/alerts?window_days=7&site_id=site-e2e&target_object=ECO&template_key=tpl-e2e&level=critical&overlay_cache_hit_rate_warn=0.1&overlay_cache_min_requests_warn=999&doc_sync_dead_letter_rate_warn=1.0&workflow_failed_rate_warn=1.0&breakage_open_rate_warn=1.0&breakage_helpdesk_failed_rate_warn=0.9&breakage_helpdesk_failed_total_warn=99&breakage_helpdesk_provider_failed_rate_warn=0.99&breakage_helpdesk_provider_failed_min_jobs_warn=99&breakage_helpdesk_provider_failed_rate_critical=0.5&breakage_helpdesk_provider_failed_min_jobs_critical=1"
    )
    assert critical_helpdesk_alerts_resp.status_code == 200
    critical_helpdesk_alerts = critical_helpdesk_alerts_resp.json()
    assert (
        critical_helpdesk_alerts["by_code"].get("breakage_helpdesk_provider_failed_rate_critical", 0)
        >= 1
    )

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
    assert "breakages.helpdesk.replay_jobs_total" in summary_export_csv_resp.text

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

    breakage_helpdesk_failures_resp = client.get(
        "/api/v1/parallel-ops/breakage-helpdesk/failures"
        "?window_days=7&provider=zendesk&failure_category=transient&page=1&page_size=10"
    )
    assert breakage_helpdesk_failures_resp.status_code == 200
    breakage_helpdesk_failures = breakage_helpdesk_failures_resp.json()
    assert breakage_helpdesk_failures["total"] == 1
    assert breakage_helpdesk_failures["by_provider"]["zendesk"] == 1
    assert breakage_helpdesk_failures["jobs"][0]["id"] == breakage_failed_job.id
    assert breakage_helpdesk_failures["jobs"][0]["error_code"] == "provider_timeout"

    breakage_helpdesk_failure_trends_resp = client.get(
        "/api/v1/parallel-ops/breakage-helpdesk/failures/trends"
        "?window_days=7&bucket_days=1&provider=zendesk&failure_category=transient"
    )
    assert breakage_helpdesk_failure_trends_resp.status_code == 200
    breakage_helpdesk_failure_trends = breakage_helpdesk_failure_trends_resp.json()
    assert breakage_helpdesk_failure_trends["aggregates"]["total_jobs"] == 1
    assert breakage_helpdesk_failure_trends["aggregates"]["failed_jobs"] == 1
    assert breakage_helpdesk_failure_trends["aggregates"]["failed_rate"] == 1.0
    assert breakage_helpdesk_failure_trends["by_failure_category"]["transient"] == 1

    breakage_helpdesk_failures_triage_resp = client.get(
        "/api/v1/parallel-ops/breakage-helpdesk/failures/triage"
        "?window_days=7&provider=zendesk&failure_category=transient&top_n=5"
    )
    assert breakage_helpdesk_failures_triage_resp.status_code == 200
    breakage_helpdesk_failures_triage = breakage_helpdesk_failures_triage_resp.json()
    assert breakage_helpdesk_failures_triage["total_failed_jobs"] == 1
    assert breakage_helpdesk_failures_triage["replay_candidates_total"] == 1
    assert (
        breakage_helpdesk_failures_triage["hotspots"]["failure_categories"][0]["key"]
        == "transient"
    )
    assert breakage_helpdesk_failures_triage["triaged_jobs"] == 0
    assert breakage_helpdesk_failures_triage["triage_rate"] == 0.0

    breakage_helpdesk_failures_triage_apply_resp = client.post(
        "/api/v1/parallel-ops/breakage-helpdesk/failures/triage/apply",
        json={
            "triage_status": "in_progress",
            "job_ids": [breakage_failed_job.id],
            "triage_owner": "ops-l2",
            "root_cause": "provider_rate_limit",
            "resolution": "retry_with_backoff",
            "note": "triage from e2e",
            "tags": ["hot", "provider"],
        },
    )
    assert breakage_helpdesk_failures_triage_apply_resp.status_code == 200
    breakage_helpdesk_failures_triage_apply = (
        breakage_helpdesk_failures_triage_apply_resp.json()
    )
    assert breakage_helpdesk_failures_triage_apply["updated_total"] == 1
    assert breakage_helpdesk_failures_triage_apply["updated_jobs"][0]["id"] == (
        breakage_failed_job.id
    )
    assert (
        breakage_helpdesk_failures_triage_apply["updated_jobs"][0]["triage_status"]
        == "in_progress"
    )
    assert breakage_helpdesk_failures_triage_apply["operator_id"] == 21

    breakage_helpdesk_replay_enqueue_resp = client.post(
        "/api/v1/parallel-ops/breakage-helpdesk/failures/replay/enqueue",
        json={"job_ids": [breakage_failed_job.id], "limit": 20},
    )
    assert breakage_helpdesk_replay_enqueue_resp.status_code == 200
    breakage_helpdesk_replay_enqueue = breakage_helpdesk_replay_enqueue_resp.json()
    assert breakage_helpdesk_replay_enqueue["batch_id"]
    assert breakage_helpdesk_replay_enqueue["created_jobs_total"] == 1
    assert breakage_helpdesk_replay_enqueue["errors_total"] == 0
    assert breakage_helpdesk_replay_enqueue["operator_id"] == 21
    replay_job_id = breakage_helpdesk_replay_enqueue["created_jobs"][0]["job_id"]
    replay_job = db.get(ConversionJob, replay_job_id)
    assert replay_job is not None
    assert replay_job.task_type == "breakage_helpdesk_sync_stub"
    replay_batch_id = breakage_helpdesk_replay_enqueue["batch_id"]

    breakage_helpdesk_replay_batch_resp = client.get(
        f"/api/v1/parallel-ops/breakage-helpdesk/failures/replay/batches/{replay_batch_id}"
        "?page=1&page_size=20"
    )
    assert breakage_helpdesk_replay_batch_resp.status_code == 200
    breakage_helpdesk_replay_batch = breakage_helpdesk_replay_batch_resp.json()
    assert breakage_helpdesk_replay_batch["batch_id"] == replay_batch_id
    assert breakage_helpdesk_replay_batch["total"] >= 1
    assert breakage_helpdesk_replay_batch["by_provider"]["zendesk"] >= 1
    assert breakage_helpdesk_replay_batch["operator_id"] == 21

    breakage_helpdesk_replay_batches_resp = client.get(
        "/api/v1/parallel-ops/breakage-helpdesk/failures/replay/batches"
        "?window_days=7&provider=zendesk&page=1&page_size=20"
    )
    assert breakage_helpdesk_replay_batches_resp.status_code == 200
    breakage_helpdesk_replay_batches = breakage_helpdesk_replay_batches_resp.json()
    assert breakage_helpdesk_replay_batches["total_batches"] >= 1
    assert breakage_helpdesk_replay_batches["by_provider"]["zendesk"] >= 1
    assert breakage_helpdesk_replay_batches["batches"][0]["batch_id"] == replay_batch_id
    assert breakage_helpdesk_replay_batches["operator_id"] == 21

    breakage_helpdesk_replay_batch_export_resp = client.get(
        f"/api/v1/parallel-ops/breakage-helpdesk/failures/replay/batches/{replay_batch_id}/export"
        "?export_format=csv"
    )
    assert breakage_helpdesk_replay_batch_export_resp.status_code == 200
    assert breakage_helpdesk_replay_batch_export_resp.headers.get(
        "content-type", ""
    ).startswith("text/csv")
    assert breakage_helpdesk_replay_batch_export_resp.headers.get("x-operator-id") == "21"
    assert replay_batch_id in breakage_helpdesk_replay_batch_export_resp.text
    assert replay_job_id in breakage_helpdesk_replay_batch_export_resp.text

    breakage_helpdesk_replay_trends_resp = client.get(
        "/api/v1/parallel-ops/breakage-helpdesk/failures/replay/trends"
        "?window_days=7&bucket_days=1&provider=zendesk"
    )
    assert breakage_helpdesk_replay_trends_resp.status_code == 200
    breakage_helpdesk_replay_trends = breakage_helpdesk_replay_trends_resp.json()
    assert breakage_helpdesk_replay_trends["aggregates"]["total_jobs"] >= 1
    assert breakage_helpdesk_replay_trends["aggregates"]["total_batches"] >= 1
    assert breakage_helpdesk_replay_trends["by_provider"]["zendesk"] >= 1
    assert breakage_helpdesk_replay_trends["operator_id"] == 21

    breakage_helpdesk_replay_trends_export_resp = client.get(
        "/api/v1/parallel-ops/breakage-helpdesk/failures/replay/trends/export"
        "?window_days=7&bucket_days=1&provider=zendesk&export_format=csv"
    )
    assert breakage_helpdesk_replay_trends_export_resp.status_code == 200
    assert breakage_helpdesk_replay_trends_export_resp.headers.get(
        "content-type", ""
    ).startswith("text/csv")
    assert (
        "bucket_start,bucket_end,total_jobs,failed_jobs,failed_rate,batches_total"
        in breakage_helpdesk_replay_trends_export_resp.text
    )

    summary_after_replay_resp = client.get(
        "/api/v1/parallel-ops/summary?window_days=7&site_id=site-e2e&target_object=ECO&template_key=tpl-e2e"
    )
    assert summary_after_replay_resp.status_code == 200
    summary_after_replay = summary_after_replay_resp.json()
    assert summary_after_replay["breakages"]["helpdesk"]["replay_jobs_total"] >= 1
    assert summary_after_replay["breakages"]["helpdesk"]["replay_batches_total"] >= 1
    assert summary_after_replay["breakages"]["helpdesk"]["replay_by_provider"]["zendesk"] >= 1

    replay_strict_summary_resp = client.get(
        "/api/v1/parallel-ops/summary?window_days=7&site_id=site-e2e&target_object=ECO&template_key=tpl-e2e&overlay_cache_hit_rate_warn=0.1&overlay_cache_min_requests_warn=999&doc_sync_dead_letter_rate_warn=1.0&workflow_failed_rate_warn=1.0&breakage_open_rate_warn=1.0&breakage_helpdesk_failed_rate_warn=1.0&breakage_helpdesk_failed_total_warn=999&breakage_helpdesk_triage_coverage_warn=0.0&breakage_helpdesk_export_failed_total_warn=999&breakage_helpdesk_provider_failed_rate_warn=1.0&breakage_helpdesk_provider_failed_min_jobs_warn=999&breakage_helpdesk_replay_failed_rate_warn=1.0&breakage_helpdesk_replay_failed_total_warn=999&breakage_helpdesk_replay_pending_total_warn=0"
    )
    assert replay_strict_summary_resp.status_code == 200
    replay_strict_summary = replay_strict_summary_resp.json()
    replay_hint_codes = {row["code"] for row in (replay_strict_summary.get("slo_hints") or [])}
    assert "breakage_helpdesk_replay_pending_total_high" in replay_hint_codes

    breakage_helpdesk_failures_triage_after_resp = client.get(
        "/api/v1/parallel-ops/breakage-helpdesk/failures/triage"
        "?window_days=7&provider=zendesk&failure_category=transient&top_n=5"
    )
    assert breakage_helpdesk_failures_triage_after_resp.status_code == 200
    breakage_helpdesk_failures_triage_after = (
        breakage_helpdesk_failures_triage_after_resp.json()
    )
    assert breakage_helpdesk_failures_triage_after["triaged_jobs"] == 1
    assert breakage_helpdesk_failures_triage_after["triage_rate"] == 1.0

    breakage_helpdesk_failures_export_resp = client.get(
        "/api/v1/parallel-ops/breakage-helpdesk/failures/export"
        "?window_days=7&provider=zendesk&failure_category=transient&export_format=csv"
    )
    assert breakage_helpdesk_failures_export_resp.status_code == 200
    assert breakage_helpdesk_failures_export_resp.headers.get("content-type", "").startswith(
        "text/csv"
    )
    assert breakage_helpdesk_failures_export_resp.headers.get("x-operator-id") == "21"
    assert "provider_timeout" in breakage_helpdesk_failures_export_resp.text

    breakage_helpdesk_export_job_create_resp = client.post(
        "/api/v1/parallel-ops/breakage-helpdesk/failures/export/jobs",
        json={
            "window_days": 7,
            "provider": "zendesk",
            "failure_category": "transient",
            "export_format": "csv",
            "execute_immediately": False,
        },
    )
    assert breakage_helpdesk_export_job_create_resp.status_code == 200
    breakage_helpdesk_export_job_create = breakage_helpdesk_export_job_create_resp.json()
    export_job_id = breakage_helpdesk_export_job_create["job_id"]
    assert breakage_helpdesk_export_job_create["download_ready"] is False
    assert breakage_helpdesk_export_job_create["operator_id"] == 21

    breakage_helpdesk_export_job_run_resp = client.post(
        f"/api/v1/parallel-ops/breakage-helpdesk/failures/export/jobs/{export_job_id}/run"
    )
    assert breakage_helpdesk_export_job_run_resp.status_code == 200
    breakage_helpdesk_export_job_run = breakage_helpdesk_export_job_run_resp.json()
    assert breakage_helpdesk_export_job_run["status"] == "completed"
    assert breakage_helpdesk_export_job_run["download_ready"] is True
    assert breakage_helpdesk_export_job_run["operator_id"] == 21

    breakage_helpdesk_export_job_status_resp = client.get(
        f"/api/v1/parallel-ops/breakage-helpdesk/failures/export/jobs/{export_job_id}"
    )
    assert breakage_helpdesk_export_job_status_resp.status_code == 200
    breakage_helpdesk_export_job_status = breakage_helpdesk_export_job_status_resp.json()
    assert breakage_helpdesk_export_job_status["status"] == "completed"
    assert breakage_helpdesk_export_job_status["download_ready"] is True
    assert breakage_helpdesk_export_job_status["operator_id"] == 21

    breakage_helpdesk_export_jobs_overview_resp = client.get(
        "/api/v1/parallel-ops/breakage-helpdesk/failures/export/jobs/overview"
        "?window_days=7&provider=zendesk&failure_category=transient&export_format=csv&page=1&page_size=20"
    )
    assert breakage_helpdesk_export_jobs_overview_resp.status_code == 200
    breakage_helpdesk_export_jobs_overview = (
        breakage_helpdesk_export_jobs_overview_resp.json()
    )
    assert breakage_helpdesk_export_jobs_overview["total"] >= 1
    assert breakage_helpdesk_export_jobs_overview["by_provider"]["zendesk"] >= 1
    assert breakage_helpdesk_export_jobs_overview["by_failure_category"]["transient"] >= 1
    assert breakage_helpdesk_export_jobs_overview["by_export_format"]["csv"] >= 1
    assert breakage_helpdesk_export_jobs_overview["duration_seconds"]["count"] >= 1
    assert breakage_helpdesk_export_jobs_overview["operator_id"] == 21

    breakage_helpdesk_export_job_download_resp = client.get(
        f"/api/v1/parallel-ops/breakage-helpdesk/failures/export/jobs/{export_job_id}/download"
    )
    assert breakage_helpdesk_export_job_download_resp.status_code == 200
    assert breakage_helpdesk_export_job_download_resp.headers.get("content-type", "").startswith(
        "text/csv"
    )
    assert breakage_helpdesk_export_job_download_resp.headers.get("x-operator-id") == "21"
    assert "provider_timeout" in breakage_helpdesk_export_job_download_resp.text

    breakage_helpdesk_export_job_cleanup_resp = client.post(
        "/api/v1/parallel-ops/breakage-helpdesk/failures/export/jobs/cleanup",
        json={"ttl_hours": 24, "limit": 200},
    )
    assert breakage_helpdesk_export_job_cleanup_resp.status_code == 200
    breakage_helpdesk_export_job_cleanup = breakage_helpdesk_export_job_cleanup_resp.json()
    assert breakage_helpdesk_export_job_cleanup["operator_id"] == 21
    assert breakage_helpdesk_export_job_cleanup["ttl_hours"] == 24

    metrics_resp = client.get(
        "/api/v1/parallel-ops/metrics?window_days=7&site_id=site-e2e&target_object=ECO&template_key=tpl-e2e"
    )
    assert metrics_resp.status_code == 200
    assert metrics_resp.headers.get("content-type", "").startswith("text/plain")
    assert metrics_resp.headers.get("x-operator-id") == "21"
    assert "yuantus_parallel_doc_sync_jobs_total" in metrics_resp.text
    assert "yuantus_parallel_breakage_helpdesk_triage_rate" in metrics_resp.text
    assert "yuantus_parallel_breakage_helpdesk_export_jobs_total" in metrics_resp.text
    assert "yuantus_parallel_breakage_helpdesk_provider_failed_rate" in metrics_resp.text
    assert "yuantus_parallel_breakage_helpdesk_replay_jobs_total" in metrics_resp.text
    assert "yuantus_parallel_breakage_helpdesk_replay_batches_total" in metrics_resp.text
    assert "yuantus_parallel_breakage_helpdesk_replay_pending_total" in metrics_resp.text
    assert "yuantus_parallel_breakage_helpdesk_replay_by_provider" in metrics_resp.text
    assert 'site_id="site-e2e"' in metrics_resp.text

    replay_payload_cleanup = dict(replay_job.payload or {})
    replay_sync_cleanup = (
        dict(replay_payload_cleanup.get("helpdesk_sync"))
        if isinstance(replay_payload_cleanup.get("helpdesk_sync"), dict)
        else {}
    )
    replay_sync_cleanup["sync_status"] = "completed"
    replay_payload_cleanup["helpdesk_sync"] = replay_sync_cleanup
    replay_job.status = "completed"
    replay_job.payload = replay_payload_cleanup
    replay_job.created_at = datetime.utcnow() - timedelta(hours=200)
    db.add(replay_job)
    db.commit()

    replay_cleanup_dry_run_resp = client.post(
        "/api/v1/parallel-ops/breakage-helpdesk/failures/replay/batches/cleanup",
        json={"ttl_hours": 24, "limit": 200, "dry_run": True},
    )
    assert replay_cleanup_dry_run_resp.status_code == 200
    replay_cleanup_dry_run = replay_cleanup_dry_run_resp.json()
    assert replay_cleanup_dry_run["dry_run"] is True
    assert replay_cleanup_dry_run["archived_jobs"] >= 1
    replay_batches_after_dry_run_resp = client.get(
        "/api/v1/parallel-ops/breakage-helpdesk/failures/replay/batches"
        "?window_days=90&provider=zendesk&page=1&page_size=20"
    )
    assert replay_batches_after_dry_run_resp.status_code == 200
    replay_batches_after_dry_run = replay_batches_after_dry_run_resp.json()
    assert replay_batches_after_dry_run["total_batches"] >= 1

    replay_cleanup_resp = client.post(
        "/api/v1/parallel-ops/breakage-helpdesk/failures/replay/batches/cleanup",
        json={"ttl_hours": 24, "limit": 200},
    )
    assert replay_cleanup_resp.status_code == 200
    replay_cleanup = replay_cleanup_resp.json()
    assert replay_cleanup["dry_run"] is False
    assert replay_cleanup["archived_jobs"] >= 1
    assert replay_cleanup["archived_batches"] >= 1
    assert replay_cleanup["operator_id"] == 21

    replay_batches_after_cleanup_resp = client.get(
        "/api/v1/parallel-ops/breakage-helpdesk/failures/replay/batches"
        "?window_days=90&provider=zendesk&page=1&page_size=20"
    )
    assert replay_batches_after_cleanup_resp.status_code == 200
    replay_batches_after_cleanup = replay_batches_after_cleanup_resp.json()
    assert replay_batches_after_cleanup["total_batches"] == 0

    replay_trends_after_cleanup_resp = client.get(
        "/api/v1/parallel-ops/breakage-helpdesk/failures/replay/trends"
        "?window_days=90&bucket_days=1&provider=zendesk"
    )
    assert replay_trends_after_cleanup_resp.status_code == 200
    replay_trends_after_cleanup = replay_trends_after_cleanup_resp.json()
    assert replay_trends_after_cleanup["aggregates"]["total_jobs"] == 0


def test_breakage_helpdesk_ticket_update_endpoint_e2e():
    user = SimpleNamespace(id=35, roles=["admin"], is_superuser=False)
    client, db = _client_with_real_db(user)

    breakage_service = BreakageIncidentService(db)
    incident = breakage_service.create_incident(
        description="e2e-ticket-update",
        severity="high",
        status="open",
        product_item_id="prod-ticket-e2e-1",
        bom_line_item_id="bom-ticket-e2e-1",
    )
    db.commit()

    helpdesk_sync_resp = client.post(
        f"/api/v1/breakages/{incident.id}/helpdesk-sync",
        json={"provider": "jira"},
    )
    assert helpdesk_sync_resp.status_code == 200
    helpdesk_sync = helpdesk_sync_resp.json()
    assert helpdesk_sync["job_id"]

    ticket_update_progress_resp = client.post(
        f"/api/v1/breakages/{incident.id}/helpdesk-sync/ticket-update",
        json={
            "job_id": helpdesk_sync["job_id"],
            "event_id": "evt-ticket-1",
            "provider_ticket_status": "assigned",
            "provider_updated_at": "2026-03-06T09:00:00+08:00",
            "provider_assignee": "ops-l2",
            "provider_payload": {"source": "jira-webhook", "event": "issue_updated"},
        },
    )
    assert ticket_update_progress_resp.status_code == 200
    ticket_update_progress = ticket_update_progress_resp.json()
    assert ticket_update_progress["incident_status"] == "in_progress"
    assert ticket_update_progress["incident_responsibility"] == "ops-l2"
    assert ticket_update_progress["sync_status"] == "in_progress"
    assert ticket_update_progress["last_job"]["status"] == "processing"
    assert ticket_update_progress["last_job"]["provider_ticket_status"] == "in_progress"
    assert ticket_update_progress["last_job"]["provider_ticket_updated_at"] == (
        "2026-03-06T01:00:00"
    )
    assert ticket_update_progress["last_job"]["provider_payload"]["event"] == "issue_updated"
    assert ticket_update_progress["event_id"] == "evt-ticket-1"
    assert ticket_update_progress["idempotent_replay"] is False
    assert ticket_update_progress["operator_id"] == 35

    ticket_update_replay_resp = client.post(
        f"/api/v1/breakages/{incident.id}/helpdesk-sync/ticket-update",
        json={
            "job_id": helpdesk_sync["job_id"],
            "provider_ticket_status": "closed",
            "event_id": "evt-ticket-1",
            "incident_responsibility": "qa-owner",
        },
    )
    assert ticket_update_replay_resp.status_code == 200
    ticket_update_replay = ticket_update_replay_resp.json()
    assert ticket_update_replay["idempotent_replay"] is True
    assert ticket_update_replay["event_id"] == "evt-ticket-1"
    assert ticket_update_replay["incident_status"] == "in_progress"
    assert ticket_update_replay["sync_status"] == "in_progress"
    assert ticket_update_replay["last_job"]["provider_ticket_status"] == "in_progress"
    assert ticket_update_replay["last_job"]["provider_event_ids_count"] == 1

    ticket_update_done_resp = client.post(
        f"/api/v1/breakages/{incident.id}/helpdesk-sync/ticket-update",
        json={
            "job_id": helpdesk_sync["job_id"],
            "provider_ticket_status": "closed",
            "event_id": "evt-ticket-2",
            "external_ticket_id": "HD-TICKET-E2E-1",
            "incident_responsibility": "qa-owner",
        },
    )
    assert ticket_update_done_resp.status_code == 200
    ticket_update_done = ticket_update_done_resp.json()
    assert ticket_update_done["incident_status"] == "closed"
    assert ticket_update_done["incident_responsibility"] == "qa-owner"
    assert ticket_update_done["sync_status"] == "completed"
    assert ticket_update_done["external_ticket_id"] == "HD-TICKET-E2E-1"
    assert ticket_update_done["last_job"]["status"] == "completed"
    assert ticket_update_done["last_job"]["provider_ticket_status"] == "closed"
    assert ticket_update_done["last_job"]["provider_event_ids_count"] == 2
    assert ticket_update_done["event_id"] == "evt-ticket-2"
    assert ticket_update_done["operator_id"] == 35


def test_eco_activity_sla_endpoint_e2e():
    user = SimpleNamespace(id=31, roles=["admin"], is_superuser=False)
    client, _db = _client_with_real_db(user)
    now = datetime(2026, 3, 5, 12, 0, 0)

    create_overdue_resp = client.post(
        "/api/v1/eco-activities",
        json={
            "eco_id": "eco-sla-e2e",
            "name": "overdue-e2e",
            "assignee_id": 100,
            "properties": {"due_at": (now - timedelta(hours=1)).isoformat()},
        },
    )
    assert create_overdue_resp.status_code == 200

    create_due_soon_resp = client.post(
        "/api/v1/eco-activities",
        json={
            "eco_id": "eco-sla-e2e",
            "name": "due-soon-e2e",
            "assignee_id": 100,
            "properties": {"due_at": (now + timedelta(hours=2)).isoformat()},
        },
    )
    assert create_due_soon_resp.status_code == 200

    create_no_due_resp = client.post(
        "/api/v1/eco-activities",
        json={
            "eco_id": "eco-sla-e2e",
            "name": "no-due-e2e",
            "assignee_id": 101,
        },
    )
    assert create_no_due_resp.status_code == 200

    create_closed_resp = client.post(
        "/api/v1/eco-activities",
        json={
            "eco_id": "eco-sla-e2e",
            "name": "closed-e2e",
            "assignee_id": 100,
            "properties": {"due_at": (now - timedelta(hours=3)).isoformat()},
        },
    )
    assert create_closed_resp.status_code == 200
    closed_id = create_closed_resp.json()["id"]
    close_resp = client.post(
        f"/api/v1/eco-activities/activity/{closed_id}/transition",
        json={"to_status": "completed", "reason": "done"},
    )
    assert close_resp.status_code == 200

    sla_resp = client.get(
        "/api/v1/eco-activities/eco-sla-e2e/sla"
        "?due_soon_hours=24&evaluated_at=2026-03-05T12:00:00Z"
    )
    assert sla_resp.status_code == 200
    sla = sla_resp.json()
    assert sla["operator_id"] == 31
    assert sla["total"] == 3
    assert sla["overdue_total"] == 1
    assert sla["due_soon_total"] == 1
    assert sla["no_due_date_total"] == 1
    assert sla["closed_total"] == 0
    assert [row["name"] for row in sla["activities"]][:2] == [
        "overdue-e2e",
        "due-soon-e2e",
    ]

    sla_assignee_closed_resp = client.get(
        "/api/v1/eco-activities/eco-sla-e2e/sla"
        "?due_soon_hours=24&assignee_id=100&include_closed=true"
        "&evaluated_at=2026-03-05T12:00:00Z"
    )
    assert sla_assignee_closed_resp.status_code == 200
    sla_assignee_closed = sla_assignee_closed_resp.json()
    assert sla_assignee_closed["total"] == 3
    assert sla_assignee_closed["closed_total"] == 1
    names = [row["name"] for row in sla_assignee_closed["activities"]]
    assert "no-due-e2e" not in names
    assert "closed-e2e" in names


def test_eco_activity_transition_check_endpoint_e2e():
    user = SimpleNamespace(id=34, roles=["admin"], is_superuser=False)
    client, _db = _client_with_real_db(user)

    parent_resp = client.post(
        "/api/v1/eco-activities",
        json={
            "eco_id": "eco-sm-e2e",
            "name": "parent-e2e",
            "is_blocking": True,
        },
    )
    assert parent_resp.status_code == 200
    parent_id = parent_resp.json()["id"]

    child_resp = client.post(
        "/api/v1/eco-activities",
        json={
            "eco_id": "eco-sm-e2e",
            "name": "child-e2e",
            "depends_on_activity_ids": [parent_id],
            "is_blocking": True,
        },
    )
    assert child_resp.status_code == 200
    child_id = child_resp.json()["id"]

    blocked_check_resp = client.get(
        f"/api/v1/eco-activities/activity/{child_id}/transition-check?to_status=done"
    )
    assert blocked_check_resp.status_code == 200
    blocked_check = blocked_check_resp.json()
    assert blocked_check["operator_id"] == 34
    assert blocked_check["to_status"] == "completed"
    assert blocked_check["can_transition"] is False
    assert blocked_check["reason_code"] == "blocking_dependencies"

    parent_done_resp = client.post(
        f"/api/v1/eco-activities/activity/{parent_id}/transition",
        json={"to_status": "done"},
    )
    assert parent_done_resp.status_code == 200
    assert parent_done_resp.json()["status"] == "completed"

    ready_check_resp = client.get(
        f"/api/v1/eco-activities/activity/{child_id}/transition-check?to_status=in_progress"
    )
    assert ready_check_resp.status_code == 200
    ready_check = ready_check_resp.json()
    assert ready_check["to_status"] == "active"
    assert ready_check["can_transition"] is True
    assert ready_check["reason_code"] == "ok"


def test_eco_activity_bulk_transition_check_endpoint_e2e():
    user = SimpleNamespace(id=36, roles=["admin"], is_superuser=False)
    client, _db = _client_with_real_db(user)

    parent_resp = client.post(
        "/api/v1/eco-activities",
        json={
            "eco_id": "eco-sm-bulk-e2e",
            "name": "parent-e2e",
            "is_blocking": True,
        },
    )
    assert parent_resp.status_code == 200
    parent_id = parent_resp.json()["id"]

    child_resp = client.post(
        "/api/v1/eco-activities",
        json={
            "eco_id": "eco-sm-bulk-e2e",
            "name": "child-e2e",
            "depends_on_activity_ids": [parent_id],
            "is_blocking": True,
        },
    )
    assert child_resp.status_code == 200
    child_id = child_resp.json()["id"]

    notify_resp = client.post(
        "/api/v1/eco-activities",
        json={
            "eco_id": "eco-sm-bulk-e2e",
            "name": "notify-e2e",
            "is_blocking": False,
        },
    )
    assert notify_resp.status_code == 200
    notify_id = notify_resp.json()["id"]

    done_parent_resp = client.post(
        f"/api/v1/eco-activities/activity/{parent_id}/transition",
        json={"to_status": "done"},
    )
    assert done_parent_resp.status_code == 200

    bulk_resp = client.post(
        "/api/v1/eco-activities/eco-sm-bulk-e2e/transition-check/bulk",
        json={
            "to_status": "done",
            "activity_ids": [child_id, parent_id, notify_id, "missing-e2e"],
            "include_terminal": False,
            "include_non_blocking": False,
            "limit": 20,
        },
    )
    assert bulk_resp.status_code == 200
    bulk = bulk_resp.json()
    assert bulk["operator_id"] == 36
    assert bulk["to_status"] == "completed"
    assert bulk["selected_total"] == 4
    assert bulk["total"] == 1
    assert bulk["ready_total"] == 1
    assert bulk["missing_total"] == 1
    assert bulk["excluded_total"] == 2
    assert bulk["missing_activity_ids"] == ["missing-e2e"]
    assert bulk["decisions"][0]["activity_id"] == child_id
    assert bulk["decisions"][0]["can_transition"] is True


def test_eco_activity_bulk_transition_endpoint_e2e():
    user = SimpleNamespace(id=37, roles=["admin"], is_superuser=False)
    client, _db = _client_with_real_db(user)

    parent_resp = client.post(
        "/api/v1/eco-activities",
        json={
            "eco_id": "eco-sm-bulk-run-e2e",
            "name": "parent-e2e",
            "is_blocking": True,
        },
    )
    assert parent_resp.status_code == 200
    parent_id = parent_resp.json()["id"]

    child_resp = client.post(
        "/api/v1/eco-activities",
        json={
            "eco_id": "eco-sm-bulk-run-e2e",
            "name": "child-e2e",
            "depends_on_activity_ids": [parent_id],
            "is_blocking": True,
        },
    )
    assert child_resp.status_code == 200
    child_id = child_resp.json()["id"]

    notify_resp = client.post(
        "/api/v1/eco-activities",
        json={
            "eco_id": "eco-sm-bulk-run-e2e",
            "name": "notify-e2e",
            "is_blocking": False,
        },
    )
    assert notify_resp.status_code == 200
    notify_id = notify_resp.json()["id"]

    bulk_transition_resp = client.post(
        "/api/v1/eco-activities/eco-sm-bulk-run-e2e/transition/bulk",
        json={
            "to_status": "done",
            "activity_ids": [child_id, parent_id, notify_id],
            "include_terminal": False,
            "include_non_blocking": False,
            "limit": 20,
            "reason": "bulk-run-e2e",
        },
    )
    assert bulk_transition_resp.status_code == 200
    bulk_transition = bulk_transition_resp.json()
    assert bulk_transition["operator_id"] == 37
    assert bulk_transition["to_status"] == "completed"
    assert bulk_transition["selected_total"] == 3
    assert bulk_transition["total"] == 2
    assert bulk_transition["executed_total"] == 2
    assert bulk_transition["noop_total"] == 0
    assert bulk_transition["blocked_total"] == 0
    assert bulk_transition["invalid_total"] == 0
    assert bulk_transition["excluded_total"] == 1

    list_resp = client.get("/api/v1/eco-activities/eco-sm-bulk-run-e2e")
    assert list_resp.status_code == 200
    rows = {row["id"]: row for row in list_resp.json()["activities"]}
    assert rows[parent_id]["status"] == "completed"
    assert rows[child_id]["status"] == "completed"
    assert rows[notify_id]["status"] == "pending"

    truncated_bulk_resp = client.post(
        "/api/v1/eco-activities/eco-sm-bulk-run-e2e/transition/bulk",
        json={
            "to_status": "done",
            "include_terminal": True,
            "include_non_blocking": True,
            "limit": 1,
        },
    )
    assert truncated_bulk_resp.status_code == 400
    truncated_detail = truncated_bulk_resp.json().get("detail") or {}
    assert truncated_detail.get("code") == "eco_activity_transition_invalid"


def test_eco_activity_sla_alerts_endpoint_e2e():
    user = SimpleNamespace(id=33, roles=["admin"], is_superuser=False)
    client, _db = _client_with_real_db(user)
    now = datetime(2026, 3, 5, 12, 0, 0)

    for name, offset_hours, is_blocking in [
        ("overdue-blocking-1", -3, True),
        ("overdue-blocking-2", -2, True),
        ("due-soon-1", 1, False),
        ("due-soon-2", 2, False),
    ]:
        resp = client.post(
            "/api/v1/eco-activities",
            json={
                "eco_id": "eco-alert-e2e",
                "name": name,
                "is_blocking": is_blocking,
                "properties": {"due_at": (now + timedelta(hours=offset_hours)).isoformat()},
            },
        )
        assert resp.status_code == 200

    alerts_resp = client.get(
        "/api/v1/eco-activities/eco-alert-e2e/sla/alerts"
        "?evaluated_at=2026-03-05T12:00:00Z"
        "&due_soon_hours=24"
        "&overdue_rate_warn=0.2"
        "&due_soon_count_warn=1"
        "&blocking_overdue_warn=1"
    )
    assert alerts_resp.status_code == 200
    alerts = alerts_resp.json()
    assert alerts["operator_id"] == 33
    assert alerts["status"] == "warning"
    alert_codes = {row["code"] for row in alerts["alerts"]}
    assert "eco_activity_sla_overdue_rate_high" in alert_codes
    assert "eco_activity_sla_due_soon_count_high" in alert_codes
    assert "eco_activity_sla_blocking_overdue_high" in alert_codes

    export_resp = client.get(
        "/api/v1/eco-activities/eco-alert-e2e/sla/alerts/export"
        "?evaluated_at=2026-03-05T12:00:00Z"
        "&due_soon_hours=24"
        "&overdue_rate_warn=0.2"
        "&due_soon_count_warn=1"
        "&blocking_overdue_warn=1"
        "&export_format=md"
    )
    assert export_resp.status_code == 200
    assert export_resp.headers.get("content-type", "").startswith("text/markdown")
    assert export_resp.headers.get("x-operator-id") == "33"
    assert "# ECO Activity SLA Alerts" in export_resp.text


def test_doc_sync_summary_endpoint_e2e():
    user = SimpleNamespace(id=32, roles=["admin"], is_superuser=False)
    client, db = _client_with_real_db(user)
    now = datetime.utcnow()

    db.add_all(
        [
            ConversionJob(
                id="sum-site-a-ok",
                task_type="document_sync_push",
                status="completed",
                payload={
                    "site_id": "site-a",
                    "site_name": "Site A",
                    "direction": "push",
                },
                attempt_count=1,
                max_attempts=3,
                created_at=now - timedelta(hours=1),
            ),
            ConversionJob(
                id="sum-site-a-failed",
                task_type="document_sync_pull",
                status="failed",
                payload={
                    "site_id": "site-a",
                    "site_name": "Site A",
                    "direction": "pull",
                },
                attempt_count=3,
                max_attempts=3,
                created_at=now - timedelta(hours=2),
            ),
            ConversionJob(
                id="sum-site-b-processing",
                task_type="document_sync_push",
                status="processing",
                payload={
                    "site_id": "site-b",
                    "site_name": "Site B",
                    "direction": "push",
                },
                attempt_count=1,
                max_attempts=3,
                created_at=now - timedelta(hours=3),
            ),
            ConversionJob(
                id="sum-site-b-old",
                task_type="document_sync_pull",
                status="completed",
                payload={
                    "site_id": "site-b",
                    "site_name": "Site B",
                    "direction": "pull",
                },
                attempt_count=1,
                max_attempts=3,
                created_at=now - timedelta(days=20),
            ),
        ]
    )
    db.commit()

    summary_resp = client.get("/api/v1/doc-sync/summary?window_days=7")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["operator_id"] == 32
    assert summary["total_jobs"] == 3
    assert summary["total_sites"] == 2
    assert summary["overall_by_status"]["completed"] == 1
    assert summary["overall_by_status"]["failed"] == 1
    assert summary["overall_by_status"]["processing"] == 1
    assert summary["overall_dead_letter_total"] == 1

    by_site = {row["site_id"]: row for row in summary["sites"]}
    assert by_site["site-a"]["total"] == 2
    assert by_site["site-a"]["dead_letter_total"] == 1
    assert by_site["site-b"]["total"] == 1
    assert by_site["site-b"]["by_status"] == {"processing": 1}

    filtered_resp = client.get("/api/v1/doc-sync/summary?window_days=7&site_id=site-a")
    assert filtered_resp.status_code == 200
    filtered = filtered_resp.json()
    assert filtered["site_filter"] == "site-a"
    assert filtered["total_jobs"] == 2
    assert filtered["total_sites"] == 1
    assert filtered["sites"][0]["site_id"] == "site-a"

    dead_letter_resp = client.get(
        "/api/v1/doc-sync/jobs/dead-letter?window_days=7&site_id=site-a&limit=20"
    )
    assert dead_letter_resp.status_code == 200
    dead_letter = dead_letter_resp.json()
    assert dead_letter["operator_id"] == 32
    assert dead_letter["total"] == 1
    assert dead_letter["jobs"][0]["id"] == "sum-site-a-failed"
    assert dead_letter["jobs"][0]["is_dead_letter"] is True

    replay_batch_resp = client.post(
        "/api/v1/doc-sync/jobs/replay-batch",
        json={
            "site_id": "site-a",
            "only_dead_letter": True,
            "window_days": 7,
            "limit": 20,
        },
    )
    assert replay_batch_resp.status_code == 200
    replay_batch = replay_batch_resp.json()
    assert replay_batch["operator_id"] == 32
    assert replay_batch["requested"] == 1
    assert replay_batch["replayed"] == 1
    assert replay_batch["failed"] == 0
    replayed_job_id = replay_batch["replayed_jobs"][0]["replayed_job_id"]
    replayed = db.get(ConversionJob, replayed_job_id)
    assert replayed is not None
    assert replayed.payload.get("replay_of") == "sum-site-a-failed"

    summary_export_csv_resp = client.get(
        "/api/v1/doc-sync/summary/export?window_days=7&site_id=site-a&export_format=csv"
    )
    assert summary_export_csv_resp.status_code == 200
    assert summary_export_csv_resp.headers.get("content-type", "").startswith("text/csv")
    assert summary_export_csv_resp.headers.get("x-operator-id") == "32"
    assert "dead_letter_total" in summary_export_csv_resp.text
    assert "site-a" in summary_export_csv_resp.text
