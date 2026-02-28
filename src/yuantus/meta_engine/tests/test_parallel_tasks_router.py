from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db


def _client_with_user(user):
    mock_db_session = MagicMock()

    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    def override_get_current_user():
        return user

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app), mock_db_session


def test_workorder_doc_export_pdf_returns_pdf_payload():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.WorkorderDocumentPackService"
    ) as service_cls:
        service_cls.return_value.export_pack.return_value = {
            "manifest": {
                "generated_at": "2026-02-28T00:00:00Z",
                "routing_id": "r-1",
                "operation_id": "op-1",
                "count": 1,
                "scope_summary": {"operation": 1, "routing": 0},
                "export_meta": {
                    "job_no": "wo-1",
                    "operator_id": 1,
                    "operator_name": "Alice",
                    "exported_by": "alice@example.com",
                },
                "documents": [
                    {
                        "document_item_id": "doc-1",
                        "operation_id": "op-1",
                        "document_scope": "operation",
                        "inherit_to_children": True,
                        "visible_in_production": True,
                    }
                ],
            },
            "zip_bytes": b"PK\x03\x04",
        }
        resp = client.get(
            "/api/v1/workorder-docs/export?routing_id=r-1&operation_id=op-1&export_format=pdf"
        )

    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("application/pdf")
    assert 'filename="workorder-doc-pack.pdf"' in (
        resp.headers.get("content-disposition", "")
    )
    assert resp.content.startswith(b"%PDF")


def test_workorder_doc_export_rejects_unknown_format():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.WorkorderDocumentPackService"
    ) as service_cls:
        service_cls.return_value.export_pack.return_value = {
            "manifest": {"routing_id": "r-1", "documents": [], "count": 0},
            "zip_bytes": b"PK\x03\x04",
        }
        resp = client.get(
            "/api/v1/workorder-docs/export?routing_id=r-1&export_format=xlsx"
        )

    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "workorder_export_invalid_format"
    assert detail.get("context", {}).get("export_format") == "xlsx"


def test_workorder_doc_export_json_includes_export_meta():
    user = SimpleNamespace(id=2, roles=["admin"], is_superuser=False, email="u2@example.com")
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.WorkorderDocumentPackService"
    ) as service_cls:
        service_cls.return_value.export_pack.return_value = {
            "manifest": {
                "generated_at": "2026-02-28T00:00:00Z",
                "routing_id": "r-1",
                "operation_id": "op-1",
                "count": 1,
                "scope_summary": {"operation": 1, "routing": 0},
                "export_meta": {
                    "job_no": "wo-1",
                    "operator_id": 2,
                    "operator_name": "Bob",
                    "exported_by": "u2@example.com",
                },
                "documents": [],
            },
            "zip_bytes": b"PK\x03\x04",
        }
        resp = client.get(
            "/api/v1/workorder-docs/export?routing_id=r-1&operation_id=op-1&export_format=json&job_no=wo-1&operator_name=Bob"
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["export_meta"]["job_no"] == "wo-1"
    assert data["scope_summary"]["operation"] == 1


def test_breakage_helpdesk_sync_endpoint_returns_job():
    user = SimpleNamespace(id=3, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.BreakageIncidentService"
    ) as service_cls:
        service_cls.return_value.enqueue_helpdesk_stub_sync.return_value = SimpleNamespace(
            id="job-1",
            task_type="breakage_helpdesk_sync_stub",
            status="pending",
            created_at=None,
        )
        resp = client.post(
            "/api/v1/breakages/inc-1/helpdesk-sync",
            json={"metadata_json": {"channel": "qa"}},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["incident_id"] == "inc-1"
    assert data["job_id"] == "job-1"
    assert data["task_type"] == "breakage_helpdesk_sync_stub"
    assert db.commit.called


def test_breakage_metrics_invalid_window_maps_contract_error():
    user = SimpleNamespace(id=3, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.BreakageIncidentService"
    ) as service_cls:
        service_cls.return_value.metrics.side_effect = ValueError(
            "trend_window_days must be one of: 7, 14, 30"
        )
        resp = client.get("/api/v1/breakages/metrics?trend_window_days=10")

    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "breakage_metrics_invalid_request"
    assert detail.get("context", {}).get("trend_window_days") == 10


def test_breakage_metrics_export_returns_download_response():
    user = SimpleNamespace(id=3, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.BreakageIncidentService"
    ) as service_cls:
        service_cls.return_value.export_metrics.return_value = {
            "content": b"date,count,total\n2026-02-28,1,1\n",
            "media_type": "text/csv",
            "filename": "breakage-metrics.csv",
        }
        resp = client.get(
            "/api/v1/breakages/metrics/export?trend_window_days=14&export_format=csv"
        )

    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("text/csv")
    assert 'filename="breakage-metrics.csv"' in (
        resp.headers.get("content-disposition", "")
    )
    assert resp.headers.get("x-operator-id") == "3"
    assert "date,count,total" in resp.text


def test_breakage_metrics_export_invalid_request_maps_contract_error():
    user = SimpleNamespace(id=3, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.BreakageIncidentService"
    ) as service_cls:
        service_cls.return_value.export_metrics.side_effect = ValueError(
            "export_format must be json, csv or md"
        )
        resp = client.get(
            "/api/v1/breakages/metrics/export?trend_window_days=14&export_format=xlsx"
        )

    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "breakage_metrics_invalid_request"
    assert detail.get("context", {}).get("export_format") == "xlsx"


def test_doc_sync_create_job_maps_missing_site_to_404():
    user = SimpleNamespace(id=5, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.DocumentMultiSiteService"
    ) as service_cls:
        service_cls.return_value.enqueue_sync.side_effect = ValueError(
            "Remote site not found: s-404"
        )
        resp = client.post(
            "/api/v1/doc-sync/jobs",
            json={
                "site_id": "s-404",
                "direction": "push",
                "document_ids": ["d-1"],
            },
        )

    assert resp.status_code == 404
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "remote_site_not_found"
    assert detail.get("context", {}).get("site_id") == "s-404"


def test_doc_sync_list_jobs_invalid_datetime_maps_contract_error():
    user = SimpleNamespace(id=5, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)
    resp = client.get(
        "/api/v1/doc-sync/jobs?created_from=not-a-datetime"
    )
    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "invalid_datetime"
    assert detail.get("context", {}).get("field") == "created_from"


def test_doc_sync_list_jobs_includes_reliability_view_fields():
    user = SimpleNamespace(id=5, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.DocumentMultiSiteService"
    ) as service_cls:
        service_cls.return_value.list_sync_jobs.return_value = [SimpleNamespace(id="job-1")]
        service_cls.return_value.build_sync_job_view.return_value = {
            "id": "job-1",
            "task_type": "document_sync_push",
            "status": "failed",
            "attempt_count": 3,
            "max_attempts": 3,
            "retry_budget": {"attempt_count": 3, "max_attempts": 3, "remaining_attempts": 0},
            "is_dead_letter": True,
            "sync_trace": {"trace_id": "t-1", "origin_site": "A", "payload_hash": "h-1"},
        }
        resp = client.get("/api/v1/doc-sync/jobs?status=failed")

    assert resp.status_code == 200
    rows = resp.json().get("jobs") or []
    assert len(rows) == 1
    assert rows[0]["is_dead_letter"] is True
    assert rows[0]["retry_budget"]["remaining_attempts"] == 0
    assert rows[0]["sync_trace"]["trace_id"] == "t-1"


def test_eco_activity_create_invalid_maps_contract_error():
    user = SimpleNamespace(id=6, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ECOActivityValidationService"
    ) as service_cls:
        service_cls.return_value.create_activity.side_effect = ValueError("eco not found")
        resp = client.post(
            "/api/v1/eco-activities",
            json={
                "eco_id": "eco-404",
                "name": "A1",
                "depends_on_activity_ids": [],
                "is_blocking": True,
            },
        )

    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "eco_activity_invalid_request"
    assert detail.get("context", {}).get("eco_id") == "eco-404"


def test_eco_activity_transition_blocked_maps_contract_error():
    user = SimpleNamespace(id=6, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ECOActivityValidationService"
    ) as service_cls:
        service_cls.return_value.transition_activity.side_effect = ValueError(
            "Blocking dependencies not satisfied"
        )
        resp = client.post(
            "/api/v1/eco-activities/activity/act-1/transition",
            json={"to_status": "done"},
        )

    assert resp.status_code == 409
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "eco_activity_blocked"
    assert detail.get("context", {}).get("activity_id") == "act-1"


def test_workflow_rule_invalid_payload_returns_contract_error():
    user = SimpleNamespace(id=9, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.WorkflowCustomActionService"
    ) as service_cls:
        service_cls.return_value.create_rule.side_effect = ValueError(
            "max_retries must be between 1 and 5 for retry strategy"
        )
        resp = client.post(
            "/api/v1/workflow-actions/rules",
            json={
                "name": "r1",
                "target_object": "ECO",
                "trigger_phase": "before",
                "action_type": "emit_event",
                "fail_strategy": "retry",
                "action_params": {"max_retries": 9},
            },
        )

    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "invalid_workflow_rule"
    assert detail.get("context", {}).get("name") == "r1"


def test_workflow_execute_failure_returns_contract_error():
    user = SimpleNamespace(id=9, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.WorkflowCustomActionService"
    ) as service_cls:
        service_cls.return_value.evaluate_transition.side_effect = ValueError(
            "[BLOCK] workflow custom action failed"
        )
        resp = client.post(
            "/api/v1/workflow-actions/execute",
            json={
                "object_id": "eco-1",
                "target_object": "ECO",
                "from_state": "draft",
                "to_state": "progress",
                "trigger_phase": "before",
            },
        )

    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "workflow_action_execution_failed"
    assert detail.get("context", {}).get("object_id") == "eco-1"


def test_3d_overlay_component_permission_denied_maps_403():
    user = SimpleNamespace(id=8, roles=["viewer"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ThreeDOverlayService"
    ) as service_cls:
        service_cls.return_value.resolve_component.side_effect = PermissionError(
            "Overlay is not visible for current roles"
        )
        resp = client.get(
            "/api/v1/cad-3d/overlays/doc-1/components/C-001"
        )

    assert resp.status_code == 403
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "overlay_access_denied"
    assert detail.get("context", {}).get("document_item_id") == "doc-1"
    assert detail.get("context", {}).get("component_ref") == "C-001"


def test_3d_overlay_get_not_found_maps_contract_error():
    user = SimpleNamespace(id=8, roles=["viewer"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ThreeDOverlayService"
    ) as service_cls:
        service_cls.return_value.get_overlay.return_value = None
        resp = client.get("/api/v1/cad-3d/overlays/doc-404")

    assert resp.status_code == 404
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "overlay_not_found"
    assert detail.get("context", {}).get("document_item_id") == "doc-404"


def test_consumption_template_create_version_success():
    user = SimpleNamespace(id=12, roles=["planner"], is_superuser=False)
    client, db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ConsumptionPlanService"
    ) as service_cls:
        service_cls.return_value.create_template_version.return_value = SimpleNamespace(
            id="plan-v1",
            name="template-v1",
            state="active",
            planned_quantity=10.0,
            uom="EA",
            period_unit="week",
            item_id="item-1",
            properties={
                "template": {
                    "key": "tpl-1",
                    "version": "v1",
                    "is_template_version": True,
                    "is_active": True,
                }
            },
        )
        resp = client.post(
            "/api/v1/consumption/templates/tpl-1/versions",
            json={
                "name": "template-v1",
                "planned_quantity": 10.0,
                "version_label": "v1",
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "plan-v1"
    assert body["template"]["key"] == "tpl-1"
    assert body["template"]["is_active"] is True
    assert db.commit.called


def test_consumption_template_create_version_invalid_maps_contract_error():
    user = SimpleNamespace(id=12, roles=["planner"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ConsumptionPlanService"
    ) as service_cls:
        service_cls.return_value.create_template_version.side_effect = ValueError(
            "template_key must not be empty"
        )
        resp = client.post(
            "/api/v1/consumption/templates/%20/versions",
            json={"name": "invalid", "planned_quantity": 10.0},
        )

    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "consumption_template_version_invalid"


def test_consumption_template_state_not_found_maps_404_contract_error():
    user = SimpleNamespace(id=12, roles=["planner"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ConsumptionPlanService"
    ) as service_cls:
        service_cls.return_value.set_template_version_state.side_effect = ValueError(
            "Consumption plan not found: p-404"
        )
        resp = client.post(
            "/api/v1/consumption/templates/versions/p-404/state",
            json={"activate": True},
        )

    assert resp.status_code == 404
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "consumption_template_version_not_found"
    assert detail.get("context", {}).get("plan_id") == "p-404"


def test_consumption_template_impact_preview_returns_payload():
    user = SimpleNamespace(id=12, roles=["planner"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ConsumptionPlanService"
    ) as service_cls:
        service_cls.return_value.preview_template_impact.return_value = {
            "template_key": "tpl-1",
            "candidate": {"planned_quantity": 20.0, "uom": "EA", "period_unit": "week"},
            "summary": {"versions_total": 2, "baseline_quantity": 10.0, "delta_quantity": 10.0},
            "impacts": [],
        }
        resp = client.post(
            "/api/v1/consumption/templates/tpl-1/impact-preview",
            json={"planned_quantity": 20.0},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["template_key"] == "tpl-1"
    assert body["summary"]["delta_quantity"] == 10.0


def test_consumption_actual_plan_not_found_maps_contract_error():
    user = SimpleNamespace(id=12, roles=["planner"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ConsumptionPlanService"
    ) as service_cls:
        service_cls.return_value.add_actual.side_effect = ValueError(
            "Consumption plan not found: p-404"
        )
        resp = client.post(
            "/api/v1/consumption/plans/p-404/actuals",
            json={"actual_quantity": 1.0},
        )

    assert resp.status_code == 404
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "consumption_plan_not_found"
    assert detail.get("context", {}).get("plan_id") == "p-404"


def test_consumption_variance_plan_not_found_maps_contract_error():
    user = SimpleNamespace(id=12, roles=["planner"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ConsumptionPlanService"
    ) as service_cls:
        service_cls.return_value.variance.side_effect = ValueError(
            "Consumption plan not found: p-404"
        )
        resp = client.get("/api/v1/consumption/plans/p-404/variance")

    assert resp.status_code == 404
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "consumption_plan_not_found"
    assert detail.get("context", {}).get("plan_id") == "p-404"


def test_breakage_status_not_found_maps_contract_error():
    user = SimpleNamespace(id=3, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.BreakageIncidentService"
    ) as service_cls:
        service_cls.return_value.update_status.side_effect = ValueError(
            "Breakage incident not found: inc-404"
        )
        resp = client.post(
            "/api/v1/breakages/inc-404/status",
            json={"status": "closed"},
        )

    assert resp.status_code == 404
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "breakage_not_found"
    assert detail.get("context", {}).get("incident_id") == "inc-404"


def test_workorder_doc_link_invalid_maps_contract_error():
    user = SimpleNamespace(id=3, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.WorkorderDocumentPackService"
    ) as service_cls:
        service_cls.return_value.upsert_link.side_effect = ValueError("document invalid")
        resp = client.post(
            "/api/v1/workorder-docs/links",
            json={
                "routing_id": "r-1",
                "operation_id": "op-1",
                "document_item_id": "doc-1",
            },
        )

    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "workorder_doc_link_invalid"
    assert detail.get("context", {}).get("routing_id") == "r-1"


def test_3d_overlay_batch_resolve_endpoint_returns_rows():
    user = SimpleNamespace(id=13, roles=["engineer"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ThreeDOverlayService"
    ) as service_cls:
        service_cls.return_value.resolve_components.return_value = {
            "document_item_id": "doc-1",
            "requested": 2,
            "returned": 2,
            "hits": 1,
            "misses": 1,
            "include_missing": True,
            "results": [
                {
                    "component_ref": "C-001",
                    "found": True,
                    "hit": {"component_ref": "C-001", "item_id": "item-1"},
                },
                {"component_ref": "C-999", "found": False, "hit": None},
            ],
            "cache": {"entries": 1, "hits": 10, "misses": 2, "evictions": 0},
        }
        resp = client.post(
            "/api/v1/cad-3d/overlays/doc-1/components/resolve-batch",
            json={"component_refs": ["C-001", "C-999"], "include_missing": True},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["requested"] == 2
    assert body["hits"] == 1
    assert body["results"][1]["found"] is False


def test_3d_overlay_cache_stats_endpoint_returns_payload():
    user = SimpleNamespace(id=14, roles=["engineer"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ThreeDOverlayService"
    ) as service_cls:
        service_cls.return_value.cache_stats.return_value = {
            "entries": 2,
            "hits": 9,
            "misses": 3,
            "evictions": 1,
            "ttl_seconds": 60,
            "max_entries": 500,
        }
        resp = client.get("/api/v1/cad-3d/overlays/cache/stats")

    assert resp.status_code == 200
    body = resp.json()
    assert body["entries"] == 2
    assert body["hits"] == 9
    assert body["ttl_seconds"] == 60


def test_parallel_ops_summary_returns_payload():
    user = SimpleNamespace(id=15, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ParallelOpsOverviewService"
    ) as service_cls:
        service_cls.return_value.summary.return_value = {
            "generated_at": "2026-02-28T00:00:00",
            "window_days": 7,
            "window_since": "2026-02-21T00:00:00",
            "doc_sync": {"total": 3, "dead_letter_total": 1},
            "workflow_actions": {"total": 5},
            "breakages": {"total": 2},
            "consumption_templates": {"versions_total": 4},
            "overlay_cache": {"hits": 5, "misses": 2, "requests": 7},
            "slo_hints": [],
        }
        resp = client.get(
            "/api/v1/parallel-ops/summary?window_days=7&site_id=site-1&target_object=ECO&template_key=tpl-1"
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["window_days"] == 7
    assert body["doc_sync"]["dead_letter_total"] == 1
    assert body["overlay_cache"]["requests"] == 7
    assert body["operator_id"] == 15


def test_parallel_ops_summary_invalid_request_maps_contract_error():
    user = SimpleNamespace(id=15, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ParallelOpsOverviewService"
    ) as service_cls:
        service_cls.return_value.summary.side_effect = ValueError(
            "window_days must be one of: 1, 7, 14, 30, 90"
        )
        resp = client.get("/api/v1/parallel-ops/summary?window_days=10")

    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "parallel_ops_invalid_request"
    assert detail.get("context", {}).get("window_days") == 10


def test_parallel_ops_trends_returns_payload():
    user = SimpleNamespace(id=18, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ParallelOpsOverviewService"
    ) as service_cls:
        service_cls.return_value.trends.return_value = {
            "generated_at": "2026-02-28T00:00:00",
            "window_days": 7,
            "window_since": "2026-02-21T00:00:00",
            "bucket_days": 1,
            "filters": {"site_id": "site-1", "target_object": "ECO", "template_key": "tpl-1"},
            "points": [
                {
                    "bucket_start": "2026-02-27T00:00:00",
                    "bucket_end": "2026-02-28T00:00:00",
                    "doc_sync": {"total": 2, "failed_total": 1, "dead_letter_total": 1, "success_rate": 0.5, "dead_letter_rate": 0.5},
                    "workflow_actions": {"total": 1, "failed_total": 1, "failed_rate": 1.0},
                    "breakages": {"total": 1, "open_total": 1, "open_rate": 1.0},
                }
            ],
            "aggregates": {
                "doc_sync_total": 2,
                "doc_sync_failed_total": 1,
                "doc_sync_dead_letter_total": 1,
                "workflow_total": 1,
                "workflow_failed_total": 1,
                "breakages_total": 1,
                "breakages_open_total": 1,
            },
            "consumption_templates": {"versions_total": 1},
            "overlay_cache": {"requests": 2, "hit_rate": 0.5},
        }
        resp = client.get(
            "/api/v1/parallel-ops/trends?window_days=7&bucket_days=1&site_id=site-1&target_object=ECO&template_key=tpl-1"
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["bucket_days"] == 1
    assert body["aggregates"]["doc_sync_total"] == 2
    assert body["operator_id"] == 18


def test_parallel_ops_trends_invalid_request_maps_contract_error():
    user = SimpleNamespace(id=18, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ParallelOpsOverviewService"
    ) as service_cls:
        service_cls.return_value.trends.side_effect = ValueError(
            "bucket_days must be <= window_days"
        )
        resp = client.get("/api/v1/parallel-ops/trends?window_days=7&bucket_days=14")

    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "parallel_ops_invalid_request"
    assert detail.get("context", {}).get("bucket_days") == 14


def test_parallel_ops_trends_export_returns_download_response():
    user = SimpleNamespace(id=18, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ParallelOpsOverviewService"
    ) as service_cls:
        service_cls.return_value.export_trends.return_value = {
            "content": b"bucket_start,bucket_end,doc_sync_total\n2026-02-27,2026-02-28,2\n",
            "media_type": "text/csv",
            "filename": "parallel-ops-trends.csv",
        }
        resp = client.get(
            "/api/v1/parallel-ops/trends/export?window_days=7&bucket_days=1&export_format=csv"
        )

    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("text/csv")
    assert 'filename="parallel-ops-trends.csv"' in (
        resp.headers.get("content-disposition", "")
    )
    assert resp.headers.get("x-operator-id") == "18"
    assert "doc_sync_total" in resp.text


def test_parallel_ops_trends_export_invalid_request_maps_contract_error():
    user = SimpleNamespace(id=18, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ParallelOpsOverviewService"
    ) as service_cls:
        service_cls.return_value.export_trends.side_effect = ValueError(
            "export_format must be json, csv or md"
        )
        resp = client.get(
            "/api/v1/parallel-ops/trends/export?window_days=7&bucket_days=1&export_format=xlsx"
        )

    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "parallel_ops_invalid_request"
    assert detail.get("context", {}).get("export_format") == "xlsx"


def test_parallel_ops_alerts_returns_payload():
    user = SimpleNamespace(id=18, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ParallelOpsOverviewService"
    ) as service_cls:
        service_cls.return_value.alerts.return_value = {
            "generated_at": "2026-02-28T00:00:00",
            "window_days": 7,
            "window_since": "2026-02-21T00:00:00",
            "filters": {
                "site_id": "site-1",
                "target_object": "ECO",
                "template_key": "tpl-1",
                "level": "warn",
            },
            "status": "warning",
            "total": 1,
            "by_code": {"doc_sync_dead_letter_rate_high": 1},
            "hints": [
                {
                    "level": "warn",
                    "code": "doc_sync_dead_letter_rate_high",
                    "message": "doc sync dead-letter rate high",
                }
            ],
        }
        resp = client.get(
            "/api/v1/parallel-ops/alerts?window_days=7&site_id=site-1&target_object=ECO&template_key=tpl-1&level=warn"
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "warning"
    assert body["total"] == 1
    assert body["by_code"]["doc_sync_dead_letter_rate_high"] == 1
    assert body["operator_id"] == 18


def test_parallel_ops_alerts_invalid_request_maps_contract_error():
    user = SimpleNamespace(id=18, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ParallelOpsOverviewService"
    ) as service_cls:
        service_cls.return_value.alerts.side_effect = ValueError(
            "level must be one of: warn, critical, info"
        )
        resp = client.get("/api/v1/parallel-ops/alerts?window_days=7&level=oops")

    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "parallel_ops_invalid_request"
    assert detail.get("context", {}).get("level") == "oops"


def test_parallel_ops_summary_export_returns_download_response():
    user = SimpleNamespace(id=19, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ParallelOpsOverviewService"
    ) as service_cls:
        service_cls.return_value.export_summary.return_value = {
            "content": b'{"window_days": 7}',
            "media_type": "application/json",
            "filename": "parallel-ops-summary.json",
        }
        resp = client.get(
            "/api/v1/parallel-ops/summary/export?window_days=7&export_format=json"
        )

    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("application/json")
    assert 'filename="parallel-ops-summary.json"' in (
        resp.headers.get("content-disposition", "")
    )
    assert resp.headers.get("x-operator-id") == "19"
    assert '"window_days": 7' in resp.text


def test_parallel_ops_summary_export_invalid_request_maps_contract_error():
    user = SimpleNamespace(id=19, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ParallelOpsOverviewService"
    ) as service_cls:
        service_cls.return_value.export_summary.side_effect = ValueError(
            "export_format must be json, csv or md"
        )
        resp = client.get(
            "/api/v1/parallel-ops/summary/export?window_days=7&export_format=xlsx"
        )

    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "parallel_ops_invalid_request"
    assert detail.get("context", {}).get("export_format") == "xlsx"


def test_parallel_ops_summary_accepts_threshold_overrides():
    user = SimpleNamespace(id=19, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ParallelOpsOverviewService"
    ) as service_cls:
        service_cls.return_value.summary.return_value = {
            "generated_at": "2026-02-28T00:00:00",
            "window_days": 7,
            "window_since": "2026-02-21T00:00:00",
            "doc_sync": {"total": 2, "dead_letter_total": 1},
            "workflow_actions": {"total": 1},
            "breakages": {"total": 1},
            "consumption_templates": {"versions_total": 1},
            "overlay_cache": {"requests": 7, "hit_rate": 0.3},
            "slo_hints": [],
            "slo_thresholds": {
                "overlay_cache_hit_rate_warn": 0.2,
                "overlay_cache_min_requests_warn": 20,
                "doc_sync_dead_letter_rate_warn": 0.9,
                "workflow_failed_rate_warn": 0.9,
                "breakage_open_rate_warn": 0.9,
            },
        }
        resp = client.get(
            "/api/v1/parallel-ops/summary?window_days=7&overlay_cache_hit_rate_warn=0.2&overlay_cache_min_requests_warn=20&doc_sync_dead_letter_rate_warn=0.9&workflow_failed_rate_warn=0.9&breakage_open_rate_warn=0.9"
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["slo_thresholds"]["doc_sync_dead_letter_rate_warn"] == 0.9


def test_parallel_ops_summary_invalid_threshold_maps_contract_error():
    user = SimpleNamespace(id=19, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ParallelOpsOverviewService"
    ) as service_cls:
        service_cls.return_value.summary.side_effect = ValueError(
            "doc_sync_dead_letter_rate_warn must be between 0 and 1"
        )
        resp = client.get(
            "/api/v1/parallel-ops/summary?window_days=7&doc_sync_dead_letter_rate_warn=1.2"
        )

    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "parallel_ops_invalid_request"
    assert detail.get("context", {}).get("doc_sync_dead_letter_rate_warn") == 1.2


def test_parallel_ops_doc_sync_failures_returns_payload():
    user = SimpleNamespace(id=16, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ParallelOpsOverviewService"
    ) as service_cls:
        service_cls.return_value.doc_sync_failures.return_value = {
            "window_days": 7,
            "window_since": "2026-02-21T00:00:00",
            "site_filter": "site-1",
            "total": 1,
            "pagination": {"page": 1, "page_size": 20, "pages": 1, "total": 1},
            "jobs": [
                {
                    "id": "job-1",
                    "task_type": "document_sync_push",
                    "status": "failed",
                    "site_id": "site-1",
                }
            ],
        }
        resp = client.get("/api/v1/parallel-ops/doc-sync/failures?window_days=7&site_id=site-1")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["jobs"][0]["status"] == "failed"
    assert body["operator_id"] == 16


def test_parallel_ops_workflow_failures_returns_payload():
    user = SimpleNamespace(id=16, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ParallelOpsOverviewService"
    ) as service_cls:
        service_cls.return_value.workflow_failures.return_value = {
            "window_days": 7,
            "window_since": "2026-02-21T00:00:00",
            "target_object_filter": "ECO",
            "total": 1,
            "pagination": {"page": 1, "page_size": 20, "pages": 1, "total": 1},
            "runs": [
                {"id": "run-1", "status": "failed", "result_code": "RETRY_EXHAUSTED"}
            ],
        }
        resp = client.get(
            "/api/v1/parallel-ops/workflow/failures?window_days=7&target_object=ECO"
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["runs"][0]["result_code"] == "RETRY_EXHAUSTED"
    assert body["operator_id"] == 16


def test_parallel_ops_metrics_returns_prometheus_text():
    user = SimpleNamespace(id=17, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ParallelOpsOverviewService"
    ) as service_cls:
        service_cls.return_value.prometheus_metrics.return_value = (
            "# HELP yuantus_parallel_doc_sync_jobs_total ...\n"
            "yuantus_parallel_doc_sync_jobs_total{window_days=\"7\"} 3\n"
        )
        resp = client.get("/api/v1/parallel-ops/metrics?window_days=7")

    assert resp.status_code == 200
    assert resp.text.startswith("# HELP yuantus_parallel_doc_sync_jobs_total")
    assert "yuantus_parallel_doc_sync_jobs_total" in resp.text
    assert resp.headers.get("x-operator-id") == "17"
    assert resp.headers.get("content-type", "").startswith("text/plain")


def test_parallel_ops_doc_sync_failures_invalid_request_maps_contract_error():
    user = SimpleNamespace(id=16, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ParallelOpsOverviewService"
    ) as service_cls:
        service_cls.return_value.doc_sync_failures.side_effect = ValueError(
            "page_size must be between 1 and 200"
        )
        resp = client.get("/api/v1/parallel-ops/doc-sync/failures?window_days=10")

    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "parallel_ops_invalid_request"
