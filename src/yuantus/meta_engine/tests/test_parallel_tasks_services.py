from __future__ import annotations

import io
from datetime import datetime, timedelta
from unittest.mock import patch
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
    ParallelOpsOverviewService,
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


def test_document_multi_site_service_idempotency_filters_and_dead_letter_view(session):
    service = DocumentMultiSiteService(session)
    site = service.upsert_remote_site(
        name="site-filter",
        endpoint="https://example-filter.test/plm",
        auth_secret="secret-token",
    )
    session.commit()

    first = service.enqueue_sync(
        site_id=site.id,
        direction="push",
        document_ids=["doc-1"],
        idempotency_key="sync-k-1",
        metadata_json={"retry_max_attempts": 4},
    )
    second = service.enqueue_sync(
        site_id=site.id,
        direction="push",
        document_ids=["doc-1"],
        idempotency_key="sync-k-1",
        metadata_json={"retry_max_attempts": 4},
    )
    session.commit()

    assert first.id == second.id
    assert first.payload["idempotency_conflicts"] == 1
    assert first.payload["sync_trace"]["trace_id"]
    assert first.payload["sync_trace"]["payload_hash"]
    assert first.max_attempts == 4

    first.status = "failed"
    first.attempt_count = 4
    first.max_attempts = 4
    first.last_error = "network timeout"
    session.flush()

    view = service.build_sync_job_view(first)
    assert view["is_dead_letter"] is True
    assert view["dead_letter_reason"] == "network timeout"
    assert view["retry_budget"]["remaining_attempts"] == 0

    third = service.enqueue_sync(
        site_id=site.id,
        direction="pull",
        document_ids=["doc-2"],
        idempotency_key="sync-k-2",
    )
    third.status = "completed"
    third.created_at = datetime.utcnow() + timedelta(seconds=1)
    session.commit()

    pending = service.list_sync_jobs(site_id=site.id, status="failed", limit=10)
    assert len(pending) == 1
    assert pending[0].id == first.id

    with pytest.raises(ValueError, match="status must be one of"):
        service.list_sync_jobs(status="deadletter")


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


def test_workflow_custom_actions_order_conflicts_and_result_codes(session):
    service = WorkflowCustomActionService(session)
    low = service.create_rule(
        name="rule-z-low",
        target_object="ECO",
        from_state="draft",
        to_state="progress",
        trigger_phase="before",
        action_type="emit_event",
        action_params={"event": "z", "priority": 50},
        fail_strategy="warn",
    )
    high = service.create_rule(
        name="rule-a-high",
        target_object="ECO",
        from_state="draft",
        to_state="progress",
        trigger_phase="before",
        action_type="emit_event",
        action_params={"event": "a", "priority": 10},
        fail_strategy="warn",
    )
    session.commit()

    assert isinstance(high.action_params, dict)
    assert int(high.action_params.get("priority") or 0) == 10
    assert int((high.action_params.get("conflict_scope") or {}).get("count") or 0) >= 1

    runs = service.evaluate_transition(
        object_id="eco-order-1",
        target_object="ECO",
        from_state="draft",
        to_state="progress",
        trigger_phase="before",
        context={"source": "order-test"},
    )
    session.commit()

    assert [run.rule_id for run in runs] == [high.id, low.id]
    assert all((run.result or {}).get("result_code") == "OK" for run in runs)
    assert (runs[0].result or {}).get("execution", {}).get("order") == 1
    assert (runs[1].result or {}).get("execution", {}).get("order") == 2

    retry_rule = service.create_rule(
        name="rule-retry-fail",
        target_object="ECO",
        from_state="draft",
        to_state="progress",
        trigger_phase="before",
        action_type="emit_event",
        action_params={"priority": 5, "max_retries": 2},
        fail_strategy="retry",
    )
    session.commit()

    with patch.object(service, "_run_action", side_effect=RuntimeError("boom")):
        runs = service.evaluate_transition(
            object_id="eco-order-2",
            target_object="ECO",
            from_state="draft",
            to_state="progress",
            trigger_phase="before",
            context={"source": "retry-test"},
        )
    session.commit()

    target_run = [run for run in runs if run.rule_id == retry_rule.id][0]
    assert target_run.status == "failed"
    assert target_run.attempts == 3
    assert (target_run.result or {}).get("result_code") == "RETRY_EXHAUSTED"


def test_workflow_custom_actions_timeout_is_enforced(session):
    service = WorkflowCustomActionService(session)
    service.create_rule(
        name="rule-timeout-warn",
        target_object="ECO",
        from_state="draft",
        to_state="progress",
        trigger_phase="before",
        action_type="emit_event",
        action_params={"priority": 1, "timeout_s": 0.01},
        fail_strategy="warn",
    )
    session.commit()

    def _slow_action(**kwargs):
        _ = kwargs
        return {"ok": True}

    with patch("time.monotonic", side_effect=[0.0, 0.02]):
        with patch.object(service, "_run_action", side_effect=_slow_action):
            runs = service.evaluate_transition(
                object_id="eco-timeout-1",
                target_object="ECO",
                from_state="draft",
                to_state="progress",
                trigger_phase="before",
                context={"source": "timeout-test"},
            )
    session.commit()

    assert len(runs) == 1
    assert runs[0].status == "warning"
    assert (runs[0].result or {}).get("result_code") == "WARN"


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


def test_consumption_template_versioning_activation_and_impact_preview(session):
    service = ConsumptionPlanService(session)
    version_v1 = service.create_template_version(
        template_key="tpl-motor",
        name="motor-plan-v1",
        planned_quantity=10.0,
        version_label="v1",
        activate=True,
    )
    version_v2 = service.create_template_version(
        template_key="tpl-motor",
        name="motor-plan-v2",
        planned_quantity=12.0,
        version_label="v2",
        activate=True,
    )
    session.commit()

    rows = service.list_template_versions("tpl-motor")
    assert len(rows) == 2
    active_rows = [row for row in rows if (row.get("template") or {}).get("is_active")]
    assert len(active_rows) == 1
    assert active_rows[0]["id"] == version_v2.id

    switched = service.set_template_version_state(version_v1.id, activate=True)
    session.commit()
    assert switched.state == "active"

    refreshed = service.list_template_versions("tpl-motor")
    active_rows = [row for row in refreshed if (row.get("template") or {}).get("is_active")]
    assert len(active_rows) == 1
    assert active_rows[0]["id"] == version_v1.id

    impact = service.preview_template_impact(
        template_key="tpl-motor",
        planned_quantity=15.0,
    )
    assert impact["summary"]["versions_total"] == 2
    assert impact["summary"]["baseline_quantity"] == 10.0
    assert impact["summary"]["delta_quantity"] == 5.0
    assert impact["active_version"]["id"] == version_v1.id

    plain = service.create_plan(name="plain-plan", planned_quantity=5.0)
    with pytest.raises(ValueError, match="not a template version"):
        service.set_template_version_state(plain.id, activate=True)


def test_breakage_metrics_include_repeat_rate_and_hotspot(session):
    service = BreakageIncidentService(session)
    service.create_incident(
        description="bearing crack",
        product_item_id="p-1",
        bom_line_item_id="bom-1",
        severity="high",
        responsibility="supplier-a",
    )
    service.create_incident(
        description="bearing crack",
        product_item_id="p-1",
        bom_line_item_id="bom-1",
        severity="high",
        responsibility="supplier-a",
    )
    service.create_incident(
        description="wire short",
        product_item_id="p-2",
        bom_line_item_id="bom-2",
        severity="medium",
        responsibility="line-b",
    )
    session.commit()

    metrics = service.metrics(
        product_item_id="p-1",
        responsibility="supplier-a",
        trend_window_days=14,
        page=1,
        page_size=1,
    )
    assert metrics["filters"]["product_item_id"] == "p-1"
    assert metrics["filters"]["responsibility"] == "supplier-a"
    assert metrics["pagination"]["page_size"] == 1
    assert metrics["pagination"]["total"] == 2
    assert len(metrics["incidents"]) == 1
    assert metrics["trend_window_days"] == 14
    assert len(metrics["trend"]) == 14
    assert metrics["total"] == 2
    assert metrics["repeated_event_count"] == 2
    assert metrics["repeated_failure_rate"] > 0
    assert metrics["hotspot_components"][0]["bom_line_item_id"] == "bom-1"
    assert metrics["by_responsibility"]["supplier-a"] == 2


def test_breakage_metrics_rejects_invalid_trend_window(session):
    service = BreakageIncidentService(session)
    with pytest.raises(ValueError, match="trend_window_days"):
        service.metrics(trend_window_days=10)


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

    pack = service.export_pack(
        routing_id="r-1",
        operation_id="op-10",
        export_meta={
            "job_no": "wo-20260228-001",
            "operator_id": 7,
            "operator_name": "Alice",
            "exported_by": "alice@example.com",
        },
    )
    assert pack["manifest"]["count"] == 2
    assert pack["manifest"]["scope_summary"]["routing"] == 1
    assert pack["manifest"]["scope_summary"]["operation"] == 1
    assert pack["manifest"]["export_meta"]["job_no"] == "wo-20260228-001"
    assert pack["manifest"]["export_meta"]["operator_id"] == 7
    zf = ZipFile(io.BytesIO(pack["zip_bytes"]))
    names = set(zf.namelist())
    assert "manifest.json" in names
    assert "documents.csv" in names


def test_3d_overlay_role_gate_and_component_lookup(session):
    service = ThreeDOverlayService(session)
    service.reset_cache_for_tests()
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


def test_3d_overlay_batch_resolve_and_cache_stats(session):
    service = ThreeDOverlayService(session)
    service.reset_cache_for_tests()
    service.upsert_overlay(
        document_item_id="doc-3d-cache",
        status="released",
        visibility_role="engineer",
        part_refs=[
            {"component_ref": "C-001", "item_id": "item-1", "name": "motor"},
            {"component_ref": "C-002", "item_id": "item-2", "name": "housing"},
        ],
    )
    session.commit()

    service.reset_cache_for_tests()
    overlay = service.get_overlay(document_item_id="doc-3d-cache", user_roles=["engineer"])
    assert overlay is not None
    stats_after_miss = service.cache_stats()
    assert stats_after_miss["misses"] == 1
    assert stats_after_miss["hits"] == 0
    assert stats_after_miss["entries"] == 1

    _ = service.get_overlay(document_item_id="doc-3d-cache", user_roles=["engineer"])
    stats_after_hit = service.cache_stats()
    assert stats_after_hit["hits"] == 1
    assert stats_after_hit["entries"] == 1

    batch = service.resolve_components(
        document_item_id="doc-3d-cache",
        component_refs=["C-002", "C-404"],
        user_roles=["engineer"],
        include_missing=True,
    )
    assert batch["requested"] == 2
    assert batch["hits"] == 1
    assert batch["misses"] == 1
    assert batch["results"][0]["component_ref"] == "C-002"
    assert batch["results"][0]["found"] is True
    assert batch["results"][0]["hit"]["item_id"] == "item-2"
    assert batch["results"][1]["component_ref"] == "C-404"
    assert batch["results"][1]["found"] is False

    found_only = service.resolve_components(
        document_item_id="doc-3d-cache",
        component_refs=["C-002", "C-404"],
        user_roles=["engineer"],
        include_missing=False,
    )
    assert found_only["returned"] == 1
    assert found_only["hits"] == 1

    with pytest.raises(PermissionError):
        service.resolve_components(
            document_item_id="doc-3d-cache",
            component_refs=["C-001"],
            user_roles=["viewer"],
        )


def test_parallel_ops_overview_summary_and_window_validation(session):
    ThreeDOverlayService.reset_cache_for_tests()
    overlay_service = ThreeDOverlayService(session)
    overlay_service.upsert_overlay(
        document_item_id="doc-ops-1",
        visibility_role="engineer",
        part_refs=[{"component_ref": "X-1", "item_id": "i-1"}],
    )
    session.commit()

    _ = overlay_service.get_overlay(document_item_id="doc-ops-1", user_roles=["engineer"])
    _ = overlay_service.get_overlay(document_item_id="doc-ops-1", user_roles=["engineer"])

    now = datetime.utcnow()
    session.add_all(
        [
            ConversionJob(
                id="job-sync-ok",
                task_type="document_sync_push",
                status="completed",
                payload={"site_id": "site-1"},
                attempt_count=1,
                max_attempts=3,
                created_at=now - timedelta(days=1),
            ),
            ConversionJob(
                id="job-sync-dead",
                task_type="document_sync_pull",
                status="failed",
                payload={"site_id": "site-1"},
                attempt_count=3,
                max_attempts=3,
                created_at=now - timedelta(days=1),
            ),
            ConversionJob(
                id="job-sync-other-site",
                task_type="document_sync_push",
                status="completed",
                payload={"site_id": "site-2"},
                attempt_count=1,
                max_attempts=3,
                created_at=now - timedelta(days=1),
            ),
        ]
    )
    session.add_all(
        [
            WorkflowCustomActionRun(
                id="wf-run-ok",
                rule_id="r-1",
                object_id="eco-1",
                target_object="ECO",
                from_state="draft",
                to_state="progress",
                trigger_phase="before",
                status="completed",
                attempts=1,
                result={"result_code": "OK"},
                created_at=now - timedelta(days=1),
            ),
            WorkflowCustomActionRun(
                id="wf-run-failed",
                rule_id="r-2",
                object_id="eco-2",
                target_object="ECO",
                from_state="draft",
                to_state="progress",
                trigger_phase="before",
                status="failed",
                attempts=3,
                result={"result_code": "RETRY_EXHAUSTED"},
                created_at=now - timedelta(days=1),
            ),
        ]
    )

    breakage_service = BreakageIncidentService(session)
    breakage_service.create_incident(
        description="bearing crack",
        severity="high",
        status="open",
        responsibility="supplier-a",
    )
    breakage_service.create_incident(
        description="bearing crack",
        severity="high",
        status="open",
        responsibility="supplier-a",
    )

    consumption_service = ConsumptionPlanService(session)
    _ = consumption_service.create_template_version(
        template_key="tpl-ops",
        name="ops-v1",
        planned_quantity=10.0,
        version_label="v1",
        activate=True,
    )
    _ = consumption_service.create_template_version(
        template_key="tpl-ops",
        name="ops-v2",
        planned_quantity=12.0,
        version_label="v2",
        activate=True,
    )
    session.commit()

    ops = ParallelOpsOverviewService(session)
    result = ops.summary(
        window_days=7,
        site_id="site-1",
        target_object="ECO",
        template_key="tpl-ops",
    )
    assert result["window_days"] == 7
    assert result["doc_sync"]["total"] == 2
    assert result["doc_sync"]["dead_letter_total"] == 1
    assert result["workflow_actions"]["total"] == 2
    assert result["workflow_actions"]["by_result_code"]["OK"] == 1
    assert result["workflow_actions"]["by_result_code"]["RETRY_EXHAUSTED"] == 1
    assert result["breakages"]["total"] == 2
    assert result["breakages"]["open_total"] == 2
    assert result["consumption_templates"]["versions_total"] == 2
    assert result["consumption_templates"]["templates_total"] == 1
    assert result["overlay_cache"]["requests"] >= 2

    hint_codes = {row["code"] for row in (result.get("slo_hints") or [])}
    assert "doc_sync_dead_letter_rate_high" in hint_codes
    assert "workflow_action_failed_rate_high" in hint_codes
    assert "breakage_open_rate_high" in hint_codes

    trends = ops.trends(
        window_days=7,
        bucket_days=1,
        site_id="site-1",
        target_object="ECO",
        template_key="tpl-ops",
    )
    assert trends["window_days"] == 7
    assert trends["bucket_days"] == 1
    assert len(trends["points"]) >= 1
    assert trends["aggregates"]["doc_sync_total"] == 2
    assert trends["aggregates"]["doc_sync_failed_total"] == 1
    assert trends["aggregates"]["doc_sync_dead_letter_total"] == 1
    assert trends["aggregates"]["workflow_total"] == 2
    assert trends["aggregates"]["workflow_failed_total"] == 1
    assert trends["aggregates"]["breakages_total"] == 2
    assert trends["aggregates"]["breakages_open_total"] == 2
    assert trends["consumption_templates"]["versions_total"] == 2

    doc_sync_failures = ops.doc_sync_failures(
        window_days=7,
        site_id="site-1",
        page=1,
        page_size=1,
    )
    assert doc_sync_failures["total"] == 1
    assert doc_sync_failures["pagination"]["pages"] == 1
    assert len(doc_sync_failures["jobs"]) == 1
    assert doc_sync_failures["jobs"][0]["status"] == "failed"
    assert doc_sync_failures["jobs"][0]["site_id"] == "site-1"

    workflow_failures = ops.workflow_failures(
        window_days=7,
        target_object="ECO",
        page=1,
        page_size=10,
    )
    assert workflow_failures["total"] == 1
    assert workflow_failures["runs"][0]["result_code"] == "RETRY_EXHAUSTED"

    metrics = ops.prometheus_metrics(
        window_days=7,
        site_id="site-1",
        target_object="ECO",
        template_key="tpl-ops",
    )
    assert "yuantus_parallel_doc_sync_jobs_total" in metrics
    assert "yuantus_parallel_workflow_runs_total" in metrics
    assert "yuantus_parallel_slo_hints_total" in metrics
    assert 'site_id="site-1"' in metrics

    alerts = ops.alerts(
        window_days=7,
        site_id="site-1",
        target_object="ECO",
        template_key="tpl-ops",
        level="warn",
    )
    assert alerts["status"] == "warning"
    assert alerts["total"] >= 1
    assert all(row.get("level") == "warn" for row in (alerts.get("hints") or []))
    assert alerts["by_code"].get("doc_sync_dead_letter_rate_high", 0) >= 1

    export_json = ops.export_summary(
        window_days=7,
        site_id="site-1",
        target_object="ECO",
        template_key="tpl-ops",
        export_format="json",
    )
    assert export_json["media_type"] == "application/json"
    assert export_json["filename"] == "parallel-ops-summary.json"
    assert b'"window_days": 7' in export_json["content"]

    export_csv = ops.export_summary(
        window_days=7,
        site_id="site-1",
        target_object="ECO",
        template_key="tpl-ops",
        export_format="csv",
    )
    assert export_csv["media_type"] == "text/csv"
    assert export_csv["filename"] == "parallel-ops-summary.csv"
    csv_text = export_csv["content"].decode("utf-8")
    assert "metric,value" in csv_text
    assert "doc_sync.total,2" in csv_text

    export_md = ops.export_summary(
        window_days=7,
        site_id="site-1",
        target_object="ECO",
        template_key="tpl-ops",
        export_format="md",
    )
    assert export_md["media_type"] == "text/markdown"
    assert export_md["filename"] == "parallel-ops-summary.md"
    md_text = export_md["content"].decode("utf-8")
    assert md_text.startswith("# Parallel Ops Summary")
    assert "| doc_sync.total | 2 |" in md_text

    with pytest.raises(ValueError, match="window_days"):
        ops.summary(window_days=10)
    with pytest.raises(ValueError, match="bucket_days must be one of"):
        ops.trends(window_days=7, bucket_days=2)
    with pytest.raises(ValueError, match="bucket_days must be <= window_days"):
        ops.trends(window_days=7, bucket_days=14)
    with pytest.raises(ValueError, match="page_size"):
        ops.doc_sync_failures(window_days=7, page_size=500)
    with pytest.raises(ValueError, match="level must be one of"):
        ops.alerts(window_days=7, level="oops")
    with pytest.raises(ValueError, match="export_format must be json, csv or md"):
        ops.export_summary(window_days=7, export_format="xlsx")
