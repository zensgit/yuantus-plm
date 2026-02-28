from __future__ import annotations

import io
from zipfile import ZipFile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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
    DocumentMultiSiteService,
    ECOActivityValidationService,
    ThreeDOverlayService,
    WorkflowCustomActionService,
    WorkorderDocumentPackService,
)
from yuantus.models.base import Base
from yuantus.security.rbac.models import RBACUser


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
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
    try:
        yield db
    finally:
        db.close()


def test_document_multi_site_service_can_upsert_and_replay_jobs(session):
    service = DocumentMultiSiteService(session)

    site_a = service.upsert_remote_site(
        name="site-a",
        endpoint="https://example.test/plm",
        auth_secret="secret-token",
    )
    site_b = service.upsert_remote_site(
        name="site-b",
        endpoint="https://example-b.test/plm",
        auth_secret="secret-token-b",
    )
    session.commit()

    assert site_a.name == "site-a"
    assert site_b.name == "site-b"
    assert site_a.auth_secret_ciphertext and "secret-token" not in site_a.auth_secret_ciphertext

    # A -> B push sample
    push_job = service.enqueue_sync(
        site_id=site_a.id,
        direction="push",
        document_ids=["doc-b", "doc-a", "doc-a"],
        user_id=7,
    )
    assert push_job.task_type == "document_sync_push"
    assert push_job.payload["document_ids"] == ["doc-a", "doc-b"]

    # B -> A pull sample
    pull_job = service.enqueue_sync(
        site_id=site_b.id,
        direction="pull",
        document_ids=["doc-x"],
        user_id=7,
    )
    assert pull_job.task_type == "document_sync_pull"

    jobs = service.list_sync_jobs(site_id=site_a.id, limit=10)
    assert len(jobs) == 1
    assert jobs[0].id == push_job.id

    replay = service.replay_sync_job(push_job.id, user_id=7)
    assert replay.id != push_job.id
    assert replay.payload.get("replay_of") == push_job.id


def test_eco_activity_validation_enforces_dependency_gate(session):
    service = ECOActivityValidationService(session)
    a1 = service.create_activity(eco_id="eco-1", name="design review")
    a2 = service.create_activity(
        eco_id="eco-1",
        name="quality review",
        depends_on_activity_ids=[a1.id],
    )
    session.commit()

    with pytest.raises(ValueError, match="Blocking dependencies"):
        service.transition_activity(activity_id=a2.id, to_status="completed", user_id=1)

    service.transition_activity(activity_id=a1.id, to_status="completed", user_id=1)
    service.transition_activity(activity_id=a2.id, to_status="completed", user_id=1)
    session.commit()

    blockers = service.blockers_for_eco("eco-1")
    assert blockers["total"] == 0
    events = service.recent_events("eco-1", limit=20)
    assert len(events) >= 4


def test_workflow_custom_actions_emit_event_and_create_job(session):
    service = WorkflowCustomActionService(session)
    service.create_rule(
        name="eco-before-event",
        target_object="ECO",
        from_state="draft",
        to_state="progress",
        trigger_phase="before",
        action_type="emit_event",
        action_params={"event": "eco.transition"},
        fail_strategy="warn",
    )
    service.create_rule(
        name="eco-before-job",
        target_object="ECO",
        from_state="draft",
        to_state="progress",
        trigger_phase="before",
        action_type="create_job",
        action_params={"task_type": "workflow_notify"},
        fail_strategy="block",
    )
    session.commit()

    runs = service.evaluate_transition(
        object_id="eco-1",
        target_object="ECO",
        from_state="draft",
        to_state="progress",
        trigger_phase="before",
        context={"source": "test"},
    )
    session.commit()

    assert len(runs) == 2
    assert all(run.status == "completed" for run in runs)
    jobs = session.query(ConversionJob).all()
    assert len(jobs) == 1
    assert jobs[0].task_type == "workflow_notify"


def test_consumption_plan_variance_dashboard(session):
    service = ConsumptionPlanService(session)
    plan = service.create_plan(name="plan-1", planned_quantity=10.0, uom="ea")
    service.add_actual(plan_id=plan.id, actual_quantity=6.0, source_type="workorder")
    service.add_actual(plan_id=plan.id, actual_quantity=5.0, source_type="report")
    session.commit()

    variance = service.variance(plan.id)
    assert variance["planned_quantity"] == 10.0
    assert variance["actual_quantity"] == 11.0
    assert variance["delta_quantity"] == 1.0
    assert variance["records"] == 2

    dashboard = service.dashboard()
    assert dashboard["total"] == 1
    assert dashboard["plans"][0]["plan_id"] == plan.id


def test_breakage_metrics_include_repeat_rate_and_hotspot(session):
    service = BreakageIncidentService(session)
    service.create_incident(
        description="bearing crack",
        product_item_id="p-1",
        bom_line_item_id="bom-1",
        severity="high",
    )
    service.create_incident(
        description="bearing crack",
        product_item_id="p-1",
        bom_line_item_id="bom-1",
        severity="high",
    )
    service.create_incident(
        description="wire short",
        product_item_id="p-2",
        bom_line_item_id="bom-2",
        severity="medium",
    )
    session.commit()

    metrics = service.metrics()
    assert metrics["total"] == 3
    assert metrics["repeated_event_count"] == 2
    assert metrics["repeated_failure_rate"] > 0
    assert metrics["hotspot_components"][0]["bom_line_item_id"] == "bom-1"


def test_breakage_helpdesk_stub_sync_enqueue(session):
    service = BreakageIncidentService(session)
    incident = service.create_incident(
        description="sensor drift",
        product_item_id="p-3",
        bom_line_item_id="bom-3",
        severity="low",
    )
    session.commit()

    job = service.enqueue_helpdesk_stub_sync(
        incident.id,
        user_id=11,
        metadata_json={"channel": "qa"},
    )
    session.commit()

    assert job.task_type == "breakage_helpdesk_sync_stub"
    assert job.payload["incident_id"] == incident.id
    assert job.payload["metadata"]["channel"] == "qa"


def test_workorder_doc_pack_supports_inherited_links_and_zip_export(session):
    service = WorkorderDocumentPackService(session)
    service.upsert_link(routing_id="r-1", document_item_id="doc-routing")
    service.upsert_link(
        routing_id="r-1",
        operation_id="op-10",
        document_item_id="doc-op",
        inherit_to_children=False,
    )
    session.commit()

    docs = service.list_links(
        routing_id="r-1",
        operation_id="op-10",
        include_inherited=True,
    )
    assert {doc.document_item_id for doc in docs} == {"doc-routing", "doc-op"}

    pack = service.export_pack(routing_id="r-1", operation_id="op-10")
    assert pack["manifest"]["count"] == 2
    zf = ZipFile(io.BytesIO(pack["zip_bytes"]))
    names = set(zf.namelist())
    assert "manifest.json" in names
    assert "documents.csv" in names


def test_3d_overlay_role_gate_and_component_lookup(session):
    service = ThreeDOverlayService(session)
    service.upsert_overlay(
        document_item_id="doc-3d-1",
        status="released",
        visibility_role="engineer",
        part_refs=[
            {"component_ref": "C-001", "item_id": "item-1", "name": "motor"},
            {"component_ref": "C-002", "item_id": "item-2", "name": "housing"},
        ],
    )
    session.commit()

    with pytest.raises(PermissionError):
        service.get_overlay(document_item_id="doc-3d-1", user_roles=["viewer"])

    overlay = service.get_overlay(document_item_id="doc-3d-1", user_roles=["engineer"])
    assert overlay is not None

    hit = service.resolve_component(
        document_item_id="doc-3d-1",
        component_ref="C-002",
        user_roles=["engineer"],
    )
    assert hit["hit"]["item_id"] == "item-2"

    with pytest.raises(ValueError, match="Component not found"):
        service.resolve_component(
            document_item_id="doc-3d-1",
            component_ref="C-999",
            user_roles=["engineer"],
        )
