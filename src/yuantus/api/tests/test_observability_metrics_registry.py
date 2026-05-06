from __future__ import annotations

from yuantus.observability.metrics import (
    duration_buckets,
    record_job_lifecycle,
    render_runtime_prometheus_text,
    render_prometheus_text,
    render_search_indexer_metrics,
    reset_registry,
)


def setup_function(_fn) -> None:
    reset_registry()


def test_counter_increments_per_call() -> None:
    record_job_lifecycle("cad_convert", "success", 25.0)
    record_job_lifecycle("cad_convert", "success", 30.0)
    record_job_lifecycle("cad_convert", "failure", 10.0)
    out = render_prometheus_text()
    assert 'yuantus_jobs_total{task_type="cad_convert",status="success"} 2' in out
    assert 'yuantus_jobs_total{task_type="cad_convert",status="failure"} 1' in out


def test_histogram_buckets_are_cumulative_within_record() -> None:
    record_job_lifecycle("cad_convert", "success", 25.0)
    out = render_prometheus_text()
    for upper in duration_buckets():
        assert (
            f'yuantus_job_duration_ms_bucket{{task_type="cad_convert",status="success",le="{upper}"}} 1'
            in out
        )
    assert 'yuantus_job_duration_ms_bucket{task_type="cad_convert",status="success",le="+Inf"} 1' in out
    assert 'yuantus_job_duration_ms_count{task_type="cad_convert",status="success"} 1' in out
    assert 'yuantus_job_duration_ms_sum{task_type="cad_convert",status="success"} 25.0' in out


def test_histogram_assigns_observation_to_correct_bucket() -> None:
    record_job_lifecycle("cad_convert", "success", 250.0)
    out = render_prometheus_text()
    assert 'yuantus_job_duration_ms_bucket{task_type="cad_convert",status="success",le="50"} 0' in out
    assert 'yuantus_job_duration_ms_bucket{task_type="cad_convert",status="success",le="100"} 0' in out
    assert 'yuantus_job_duration_ms_bucket{task_type="cad_convert",status="success",le="500"} 1' in out
    assert 'yuantus_job_duration_ms_bucket{task_type="cad_convert",status="success",le="+Inf"} 1' in out


def test_record_with_none_duration_increments_counter_only() -> None:
    record_job_lifecycle("cad_convert", "failure", None)
    out = render_prometheus_text()
    assert 'yuantus_jobs_total{task_type="cad_convert",status="failure"} 1' in out
    assert "yuantus_job_duration_ms" not in out


def test_render_emits_prometheus_help_and_type_lines() -> None:
    record_job_lifecycle("cad_convert", "success", 100.0)
    out = render_prometheus_text()
    assert "# HELP yuantus_jobs_total" in out
    assert "# TYPE yuantus_jobs_total counter" in out
    assert "# HELP yuantus_job_duration_ms" in out
    assert "# TYPE yuantus_job_duration_ms histogram" in out


def test_long_tail_buckets_cover_cad_workloads() -> None:
    buckets = list(duration_buckets())
    assert max(buckets) >= 300000, "long-tail bucket >= 5min required for CAD jobs"
    assert min(buckets) <= 50, "fast-bucket <= 50ms required for short queue jobs"


def test_empty_registry_renders_empty_string() -> None:
    out = render_prometheus_text()
    assert out == ""


def test_search_indexer_metrics_snapshot_renders_health_and_outcomes() -> None:
    out = render_search_indexer_metrics(
        {
            "registered": True,
            "uptime_seconds": 42,
            "health": "degraded",
            "health_reasons": ["missing-handlers"],
            "item_index_ready": True,
            "eco_index_ready": False,
            "handlers": ["item.created", "eco.deleted"],
            "subscription_counts": {"item.created": 1, "eco.deleted": 0},
            "event_counts": {"item.created": 3, "eco.deleted": 1},
            "success_counts": {"item.created": 2, "eco.deleted": 0},
            "skipped_counts": {"item.created": 1, "eco.deleted": 0},
            "error_counts": {"item.created": 0, "eco.deleted": 1},
            "last_error": "RuntimeError: token=supersecret",
        }
    )

    assert "yuantus_search_indexer_registered 1" in out
    assert "yuantus_search_indexer_uptime_seconds 42" in out
    assert 'yuantus_search_indexer_health{state="degraded"} 1' in out
    assert (
        'yuantus_search_indexer_health_reason{reason="missing-handlers"} 1'
        in out
    )
    assert 'yuantus_search_indexer_index_ready{index="item"} 1' in out
    assert 'yuantus_search_indexer_index_ready{index="eco"} 0' in out
    assert (
        'yuantus_search_indexer_subscriptions{event_type="item.created"} 1'
        in out
    )
    assert (
        'yuantus_search_indexer_events_total{event_type="item.created",outcome="received"} 3'
        in out
    )
    assert (
        'yuantus_search_indexer_events_total{event_type="eco.deleted",outcome="error"} 1'
        in out
    )
    assert "supersecret" not in out
    assert "last_error" not in out


def test_runtime_prometheus_text_combines_job_registry_and_search_indexer(
    monkeypatch,
) -> None:
    from yuantus.meta_engine.services import search_indexer

    monkeypatch.setattr(
        search_indexer,
        "indexer_status",
        lambda: {
            "registered": False,
            "uptime_seconds": 0,
            "health": "not_registered",
            "health_reasons": ["not-registered"],
            "item_index_ready": False,
            "eco_index_ready": False,
            "handlers": ["item.created"],
            "subscription_counts": {"item.created": 0},
            "event_counts": {"item.created": 0},
            "success_counts": {"item.created": 0},
            "skipped_counts": {"item.created": 0},
            "error_counts": {"item.created": 0},
        },
    )
    record_job_lifecycle("cad_convert", "success", 25.0)

    out = render_runtime_prometheus_text()

    assert 'yuantus_jobs_total{task_type="cad_convert",status="success"} 1' in out
    assert 'yuantus_search_indexer_health{state="not_registered"} 1' in out
