#!/usr/bin/env python3
"""
Backward-compatible entrypoint for the perf gate script.

Historically this repo used `scripts/perf_p5_reports_gate.py`. The implementation
has moved to `scripts/perf_gate.py`, but we keep this wrapper so existing docs
and CI invocations keep working.
"""

from __future__ import annotations

import perf_gate


def main() -> int:
    # Preserve the historical default baseline glob for P5 artifacts.
    return perf_gate.main(default_baseline_glob="P5_REPORTS_PERF_*.md")


if __name__ == "__main__":
    raise SystemExit(main())

