"""Statistical Process Control (SPC) service for quality measurements.

Computes Cp/Cpk/Pp/Ppk capability indices, control chart data (X-bar),
and out-of-control point detection.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class SpcResult:
    """Container for SPC computation results."""

    mean: float
    std_dev: float
    cp: Optional[float]
    cpk: Optional[float]
    pp: Optional[float]
    ppk: Optional[float]
    is_capable: bool
    ucl: float
    lcl: float
    points: List[Dict[str, Any]]
    out_of_control_indices: List[int]


class QualitySpcService:
    """Pure-Python SPC calculations over a list of measurements.

    Parameters
    ----------
    measurements : list[float]
        Raw measurement values in collection order.
    lsl : float
        Lower specification limit.
    usl : float
        Upper specification limit.
    """

    CAPABILITY_THRESHOLD = 1.33

    def __init__(
        self,
        measurements: List[float],
        lsl: float,
        usl: float,
    ) -> None:
        self._measurements = list(measurements)
        self._lsl = lsl
        self._usl = usl
        self._n = len(self._measurements)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_checks(
        cls,
        checks: List[Any],
        point: Any,
    ) -> "QualitySpcService":
        """Build from QualityCheck objects and their parent QualityPoint.

        Uses ``measure_value`` from each check and ``measure_min`` /
        ``measure_max`` from the point as LSL / USL.
        """
        measurements = [
            c.measure_value
            for c in checks
            if c.measure_value is not None
        ]
        lsl = getattr(point, "measure_min", 0.0) or 0.0
        usl = getattr(point, "measure_max", 0.0) or 0.0
        return cls(measurements, lsl, usl)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def capability_indices(self) -> Dict[str, Any]:
        """Return Cp, Cpk, Pp, Ppk and is_capable flag."""
        if self._n < 2:
            return {
                "cp": None,
                "cpk": None,
                "pp": None,
                "ppk": None,
                "is_capable": False,
                "sample_size": self._n,
            }

        mean = self._mean()
        sigma = self._std_dev()

        if sigma == 0:
            return {
                "cp": None,
                "cpk": None,
                "pp": None,
                "ppk": None,
                "is_capable": self._lsl <= mean <= self._usl,
                "sample_size": self._n,
            }

        spec_range = self._usl - self._lsl
        cp = spec_range / (6 * sigma)
        cpu = (self._usl - mean) / (3 * sigma)
        cpl = (mean - self._lsl) / (3 * sigma)
        cpk = min(cpu, cpl)

        # Pp / Ppk use overall std dev (same as sigma for single subgroup)
        pp = cp
        ppk = cpk

        return {
            "cp": round(cp, 4),
            "cpk": round(cpk, 4),
            "pp": round(pp, 4),
            "ppk": round(ppk, 4),
            "is_capable": cpk >= self.CAPABILITY_THRESHOLD,
            "sample_size": self._n,
        }

    def control_chart_data(self) -> Dict[str, Any]:
        """Return mean, UCL, LCL, and per-point data with OOC flags."""
        if self._n < 2:
            return {
                "mean": self._mean() if self._n else None,
                "ucl": None,
                "lcl": None,
                "points": [
                    {"index": i, "value": v, "out_of_control": False}
                    for i, v in enumerate(self._measurements)
                ],
            }

        mean = self._mean()
        sigma = self._std_dev()
        ucl = mean + 3 * sigma
        lcl = mean - 3 * sigma

        points = []
        for i, v in enumerate(self._measurements):
            ooc = v < lcl or v > ucl
            points.append({"index": i, "value": v, "out_of_control": ooc})

        return {
            "mean": round(mean, 4),
            "ucl": round(ucl, 4),
            "lcl": round(lcl, 4),
            "points": points,
        }

    def out_of_control_indices(self) -> List[int]:
        """Return 0-based indices of out-of-control points."""
        chart = self.control_chart_data()
        return [p["index"] for p in chart["points"] if p["out_of_control"]]

    def full_result(self) -> SpcResult:
        """Combined result object."""
        cap = self.capability_indices()
        chart = self.control_chart_data()
        return SpcResult(
            mean=chart["mean"] if chart["mean"] is not None else 0.0,
            std_dev=round(self._std_dev(), 4) if self._n >= 2 else 0.0,
            cp=cap["cp"],
            cpk=cap["cpk"],
            pp=cap["pp"],
            ppk=cap["ppk"],
            is_capable=cap["is_capable"],
            ucl=chart["ucl"] if chart["ucl"] is not None else 0.0,
            lcl=chart["lcl"] if chart["lcl"] is not None else 0.0,
            points=chart["points"],
            out_of_control_indices=[
                p["index"] for p in chart["points"] if p["out_of_control"]
            ],
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _mean(self) -> float:
        if not self._measurements:
            return 0.0
        return sum(self._measurements) / self._n

    def _std_dev(self) -> float:
        if self._n < 2:
            return 0.0
        mean = self._mean()
        variance = sum((x - mean) ** 2 for x in self._measurements) / (self._n - 1)
        return math.sqrt(variance)
