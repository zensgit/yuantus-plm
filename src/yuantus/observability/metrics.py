from __future__ import annotations

import threading
from collections.abc import Mapping
from typing import Any, Dict, Iterable, List, Optional, Tuple


_DURATION_BUCKETS_MS: Tuple[int, ...] = (
    50,
    100,
    500,
    1000,
    5000,
    10000,
    30000,
    60000,
    300000,
)
_SEARCH_INDEXER_HEALTH_STATES: Tuple[str, ...] = ("ok", "not_registered", "degraded")
_SEARCH_INDEXER_OUTCOME_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("received", "event_counts"),
    ("success", "success_counts"),
    ("skipped", "skipped_counts"),
    ("error", "error_counts"),
)


class _Registry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[Tuple[str, str], int] = {}
        self._hist_counts: Dict[Tuple[str, str], List[int]] = {}
        self._hist_sums: Dict[Tuple[str, str], float] = {}
        self._hist_totals: Dict[Tuple[str, str], int] = {}

    def record_job_lifecycle(
        self,
        task_type: str,
        status: str,
        duration_ms: Optional[float],
    ) -> None:
        key = (task_type or "unknown", status)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + 1
            if duration_ms is None:
                return
            buckets = self._hist_counts.setdefault(
                key, [0] * len(_DURATION_BUCKETS_MS)
            )
            for i, upper in enumerate(_DURATION_BUCKETS_MS):
                if duration_ms <= upper:
                    buckets[i] += 1
            self._hist_sums[key] = self._hist_sums.get(key, 0.0) + float(duration_ms)
            self._hist_totals[key] = self._hist_totals.get(key, 0) + 1

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._hist_counts.clear()
            self._hist_sums.clear()
            self._hist_totals.clear()

    def render_prometheus_text(self) -> str:
        lines: List[str] = []
        with self._lock:
            counter_keys = sorted(self._counters)
            if counter_keys:
                lines.append("# HELP yuantus_jobs_total Total job lifecycle events")
                lines.append("# TYPE yuantus_jobs_total counter")
                for (task_type, status) in counter_keys:
                    lines.append(
                        f'yuantus_jobs_total{{task_type="{_escape(task_type)}",'
                        f'status="{_escape(status)}"}} {self._counters[(task_type, status)]}'
                    )

            hist_keys = sorted(self._hist_totals)
            if hist_keys:
                if lines:
                    lines.append("")
                lines.append(
                    "# HELP yuantus_job_duration_ms Job execution duration in milliseconds"
                )
                lines.append("# TYPE yuantus_job_duration_ms histogram")
                for key in hist_keys:
                    task_type, status = key
                    buckets = self._hist_counts.get(key, [0] * len(_DURATION_BUCKETS_MS))
                    for upper, count in zip(_DURATION_BUCKETS_MS, buckets):
                        lines.append(
                            f'yuantus_job_duration_ms_bucket{{task_type="{_escape(task_type)}",'
                            f'status="{_escape(status)}",le="{upper}"}} {count}'
                        )
                    total = self._hist_totals[key]
                    lines.append(
                        f'yuantus_job_duration_ms_bucket{{task_type="{_escape(task_type)}",'
                        f'status="{_escape(status)}",le="+Inf"}} {total}'
                    )
                    lines.append(
                        f'yuantus_job_duration_ms_sum{{task_type="{_escape(task_type)}",'
                        f'status="{_escape(status)}"}} {self._hist_sums[key]}'
                    )
                    lines.append(
                        f'yuantus_job_duration_ms_count{{task_type="{_escape(task_type)}",'
                        f'status="{_escape(status)}"}} {total}'
                    )
        return "\n".join(lines) + ("\n" if lines else "")


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


_registry = _Registry()


def record_job_lifecycle(
    task_type: str,
    status: str,
    duration_ms: Optional[float] = None,
) -> None:
    _registry.record_job_lifecycle(task_type, status, duration_ms)


def render_prometheus_text() -> str:
    return _registry.render_prometheus_text()


def render_runtime_prometheus_text() -> str:
    from yuantus.meta_engine.services import search_indexer

    return _join_metric_sections(
        (
            render_prometheus_text(),
            render_search_indexer_metrics(search_indexer.indexer_status()),
        )
    )


def render_search_indexer_metrics(status: Mapping[str, Any]) -> str:
    handlers = _status_handlers(status)
    health = str(status.get("health") or "unknown")
    health_reasons = sorted({str(reason) for reason in status.get("health_reasons") or []})
    lines: List[str] = [
        "# HELP yuantus_search_indexer_registered Search indexer handlers are registered",
        "# TYPE yuantus_search_indexer_registered gauge",
        f"yuantus_search_indexer_registered {_bool_metric(status.get('registered'))}",
        "",
        "# HELP yuantus_search_indexer_uptime_seconds Search indexer uptime seconds",
        "# TYPE yuantus_search_indexer_uptime_seconds gauge",
        f"yuantus_search_indexer_uptime_seconds {_int_metric(status.get('uptime_seconds'))}",
        "",
        "# HELP yuantus_search_indexer_health Search indexer health state",
        "# TYPE yuantus_search_indexer_health gauge",
    ]
    for state in _SEARCH_INDEXER_HEALTH_STATES:
        lines.append(
            f'yuantus_search_indexer_health{{state="{_escape(state)}"}} '
            f"{1 if health == state else 0}"
        )
    if health not in _SEARCH_INDEXER_HEALTH_STATES:
        lines.append(
            f'yuantus_search_indexer_health{{state="{_escape(health)}"}} 1'
        )

    if health_reasons:
        lines.extend(
            [
                "",
                "# HELP yuantus_search_indexer_health_reason Active search indexer health reasons",
                "# TYPE yuantus_search_indexer_health_reason gauge",
            ]
        )
        for reason in health_reasons:
            lines.append(
                f'yuantus_search_indexer_health_reason{{reason="{_escape(reason)}"}} 1'
            )

    lines.extend(
        [
            "",
            "# HELP yuantus_search_indexer_index_ready Search index readiness by index",
            "# TYPE yuantus_search_indexer_index_ready gauge",
            f'yuantus_search_indexer_index_ready{{index="item"}} '
            f"{_bool_metric(status.get('item_index_ready'))}",
            f'yuantus_search_indexer_index_ready{{index="eco"}} '
            f"{_bool_metric(status.get('eco_index_ready'))}",
            "",
            "# HELP yuantus_search_indexer_subscriptions Search indexer subscriptions",
            "# TYPE yuantus_search_indexer_subscriptions gauge",
        ]
    )
    subscription_counts = _status_map(status, "subscription_counts")
    for event_type in handlers:
        lines.append(
            f'yuantus_search_indexer_subscriptions{{event_type="{_escape(event_type)}"}} '
            f"{_int_metric(subscription_counts.get(event_type))}"
        )

    lines.extend(
        [
            "",
            "# HELP yuantus_search_indexer_events_total Search indexer event outcomes",
            "# TYPE yuantus_search_indexer_events_total counter",
        ]
    )
    for outcome, field_name in _SEARCH_INDEXER_OUTCOME_FIELDS:
        counts = _status_map(status, field_name)
        for event_type in handlers:
            lines.append(
                f'yuantus_search_indexer_events_total{{event_type="{_escape(event_type)}",'
                f'outcome="{_escape(outcome)}"}} {_int_metric(counts.get(event_type))}'
            )
    return "\n".join(lines) + "\n"


def reset_registry() -> None:
    """Test-only helper to clear in-memory metric state between cases."""
    _registry.reset()


def duration_buckets() -> Iterable[int]:
    return _DURATION_BUCKETS_MS


def _join_metric_sections(sections: Iterable[str]) -> str:
    chunks = [section.strip() for section in sections if section.strip()]
    return "\n\n".join(chunks) + ("\n" if chunks else "")


def _status_handlers(status: Mapping[str, Any]) -> List[str]:
    handlers = {str(event_type) for event_type in status.get("handlers") or []}
    for _outcome, field_name in _SEARCH_INDEXER_OUTCOME_FIELDS:
        handlers.update(_status_map(status, field_name))
    handlers.update(_status_map(status, "subscription_counts"))
    return sorted(handlers)


def _status_map(status: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    value = status.get(field_name)
    return value if isinstance(value, Mapping) else {}


def _bool_metric(value: Any) -> int:
    return 1 if bool(value) else 0


def _int_metric(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
