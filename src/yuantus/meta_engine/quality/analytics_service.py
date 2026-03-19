"""Quality analytics service – defect rates, distributions, alert aging."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


class QualityAnalyticsService:
    """Pure-Python analytics over quality checks, alerts, and points.

    Parameters
    ----------
    checks : list
        QualityCheck-like objects (need ``point_id``, ``result``).
    alerts : list
        QualityAlert-like objects (need ``state``, ``created_at``, ``priority``).
    points : list
        QualityPoint-like objects (need ``id``, ``name``).
    """

    def __init__(
        self,
        checks: Optional[List[Any]] = None,
        alerts: Optional[List[Any]] = None,
        points: Optional[List[Any]] = None,
    ) -> None:
        self._checks = list(checks or [])
        self._alerts = list(alerts or [])
        self._points = list(points or [])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def defect_rate_by_point(self) -> Dict[str, Any]:
        """Per-point defect (fail) rate."""
        point_map: Dict[str, Dict[str, int]] = {}
        for chk in self._checks:
            pid = getattr(chk, "point_id", None)
            if pid is None:
                continue
            entry = point_map.setdefault(pid, {"total": 0, "fail": 0})
            entry["total"] += 1
            if getattr(chk, "result", None) == "fail":
                entry["fail"] += 1

        # Enrich with point name
        name_lookup = {p.id: getattr(p, "name", p.id) for p in self._points}

        rates = []
        for pid, counts in point_map.items():
            rate = counts["fail"] / counts["total"] if counts["total"] else 0.0
            rates.append({
                "point_id": pid,
                "point_name": name_lookup.get(pid, pid),
                "total_checks": counts["total"],
                "fail_count": counts["fail"],
                "defect_rate": round(rate, 4),
            })

        rates.sort(key=lambda r: r["defect_rate"], reverse=True)
        return {"points": rates}

    def check_result_distribution(self) -> Dict[str, Any]:
        """Aggregate pass / fail / warning counts and rates."""
        counts: Dict[str, int] = {"pass": 0, "fail": 0, "warning": 0, "none": 0}
        for chk in self._checks:
            result = getattr(chk, "result", "none")
            if result in counts:
                counts[result] += 1
            else:
                counts["none"] += 1

        total = len(self._checks)
        rates = {}
        for key, val in counts.items():
            rates[f"{key}_rate"] = round(val / total, 4) if total else 0.0

        return {
            "total_checks": total,
            **counts,
            **rates,
        }

    def alert_aging(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        """Bucket open alerts by age: under_24h, 24h_to_72h, over_72h."""
        now = now or datetime.utcnow()
        buckets = {"under_24h": 0, "24h_to_72h": 0, "over_72h": 0}
        open_states = {"new", "confirmed", "in_progress"}

        for alert in self._alerts:
            state = getattr(alert, "state", "")
            if state not in open_states:
                continue
            created = getattr(alert, "created_at", None)
            if created is None:
                continue
            age_hours = (now - created).total_seconds() / 3600
            if age_hours < 24:
                buckets["under_24h"] += 1
            elif age_hours < 72:
                buckets["24h_to_72h"] += 1
            else:
                buckets["over_72h"] += 1

        return {
            "total_open": sum(buckets.values()),
            **buckets,
        }

    def point_effectiveness(self) -> Dict[str, Any]:
        """Checks-to-alerts ratio per point.

        A high ratio means the point generates many checks but few alerts
        (low defect detection), suggesting the point might need tuning.
        """
        # Count checks per point
        checks_per_point: Dict[str, int] = {}
        for chk in self._checks:
            pid = getattr(chk, "point_id", None)
            if pid:
                checks_per_point[pid] = checks_per_point.get(pid, 0) + 1

        # Count alerts linked to checks per point
        check_to_point: Dict[str, str] = {}
        for chk in self._checks:
            cid = getattr(chk, "id", None)
            pid = getattr(chk, "point_id", None)
            if cid and pid:
                check_to_point[cid] = pid

        alerts_per_point: Dict[str, int] = {}
        for alert in self._alerts:
            cid = getattr(alert, "check_id", None)
            if cid and cid in check_to_point:
                pid = check_to_point[cid]
                alerts_per_point[pid] = alerts_per_point.get(pid, 0) + 1

        name_lookup = {p.id: getattr(p, "name", p.id) for p in self._points}

        rows = []
        all_point_ids = set(checks_per_point.keys()) | set(alerts_per_point.keys())
        for pid in all_point_ids:
            n_checks = checks_per_point.get(pid, 0)
            n_alerts = alerts_per_point.get(pid, 0)
            ratio = n_checks / n_alerts if n_alerts else None
            rows.append({
                "point_id": pid,
                "point_name": name_lookup.get(pid, pid),
                "check_count": n_checks,
                "alert_count": n_alerts,
                "checks_per_alert": round(ratio, 2) if ratio is not None else None,
            })

        rows.sort(key=lambda r: r["alert_count"], reverse=True)
        return {"points": rows}

    def full_analytics(self) -> Dict[str, Any]:
        """Combined analytics report."""
        return {
            "report": "quality-analytics",
            "generated_at": datetime.utcnow().isoformat(),
            "defect_rates": self.defect_rate_by_point(),
            "result_distribution": self.check_result_distribution(),
            "alert_aging": self.alert_aging(),
            "point_effectiveness": self.point_effectiveness(),
        }
