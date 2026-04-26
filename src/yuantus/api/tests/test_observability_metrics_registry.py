from __future__ import annotations

from yuantus.observability.metrics import (
    duration_buckets,
    record_job_lifecycle,
    render_prometheus_text,
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
