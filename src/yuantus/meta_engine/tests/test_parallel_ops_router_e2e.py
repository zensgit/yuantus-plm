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
    breakage_service.create_incident(
        description="e2e-bearing-crack",
        severity="high",
        status="open",
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
