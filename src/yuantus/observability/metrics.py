from __future__ import annotations

import threading
from typing import Dict, Iterable, List, Optional, Tuple


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


def reset_registry() -> None:
    """Test-only helper to clear in-memory metric state between cases."""
    _registry.reset()


def duration_buckets() -> Iterable[int]:
    return _DURATION_BUCKETS_MS
