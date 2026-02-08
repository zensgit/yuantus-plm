#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import os
import statistics
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _git_short_sha() -> str:
    try:
        out = subprocess.check_output(  # noqa: S603,S607
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except Exception:
        return ""


def _fmt_duration_s(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.1f}ms"
    return f"{seconds:.3f}s"


def _measure(fn) -> Tuple[float, Any]:
    start = time.perf_counter()
    value = fn()
    end = time.perf_counter()
    return end - start, value


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(math.ceil(p * len(sorted_vals))) - 1
    idx = max(0, min(len(sorted_vals) - 1, idx))
    return sorted_vals[idx]


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


@dataclass
class ScenarioResult:
    name: str
    target: str
    threshold_s: Optional[float]
    measured_s: Optional[float]
    status: str
    notes: str = ""


def _ensure_item_types(session) -> None:
    from yuantus.meta_engine.models.meta_schema import ItemType

    existing = session.get(ItemType, "Part")
    if existing:
        return
    session.add(ItemType(id="Part", label="Part", is_relationship=False))
    session.commit()


def _ensure_rbac_user(session, *, user_id: int, username: str) -> None:
    from yuantus.security.rbac.models import RBACUser

    existing = session.query(RBACUser).filter(RBACUser.user_id == user_id).first()
    if existing:
        return
    session.add(
        RBACUser(
            user_id=user_id,
            username=username,
            email=f"{username}@example.com",
            is_active=True,
            is_superuser=True,
        )
    )
    session.commit()


def _create_parts(session, *, count: int, prefix: str) -> None:
    from yuantus.meta_engine.models.item import Item

    items: List[Item] = []
    for i in range(int(count)):
        item_id = str(uuid.uuid4())
        items.append(
            Item(
                id=item_id,
                item_type_id="Part",
                config_id=str(uuid.uuid4()),
                generation=1,
                is_current=True,
                state="Draft",
                properties={
                    "item_number": f"{prefix}-{i:05d}",
                    "name": f"{prefix} Part {i}",
                    "description": f"{prefix} Desc {i}",
                },
                created_by_id=1,
            )
        )
    session.add_all(items)
    session.commit()


def _create_conversion_jobs(session, *, count: int) -> None:
    from yuantus.meta_engine.models.job import ConversionJob

    statuses = ["pending", "processing", "completed", "failed"]
    task_types = ["cad_preview", "cad_geometry", "report_generation"]

    jobs: List[ConversionJob] = []
    for i in range(int(count)):
        jobs.append(
            ConversionJob(
                task_type=task_types[i % len(task_types)],
                payload={"seed": True, "i": i},
                status=statuses[i % len(statuses)],
                priority=10,
                created_by_id=1,
            )
        )

    session.add_all(jobs)
    session.commit()


def _create_files(session, *, count: int, prefix: str) -> None:
    from yuantus.meta_engine.models.file import DocumentType, FileContainer

    doc_types = [DocumentType.CAD_3D.value, DocumentType.CAD_2D.value, DocumentType.OTHER.value]

    files: List[FileContainer] = []
    for i in range(int(count)):
        file_id = str(uuid.uuid4())
        files.append(
            FileContainer(
                id=file_id,
                filename=f"{prefix}-{i:05d}.step",
                file_type="step",
                mime_type="model/step",
                file_size=1234,
                checksum=file_id.replace("-", ""),
                system_path=f"{prefix}/{file_id}/v1/{prefix}-{i:05d}.step",
                document_type=doc_types[i % len(doc_types)],
                is_native_cad=True,
                cad_format="STEP",
                cad_connector_id="perf",
                conversion_status="completed",
                created_by_id=1,
            )
        )

    session.add_all(files)
    session.commit()


def _scenario_reports_search(session, *, query: str) -> ScenarioResult:
    from yuantus.meta_engine.reports.search_service import AdvancedSearchService

    svc = AdvancedSearchService(session)
    timings: List[float] = []

    # Warm-up
    svc.search(item_type_id="Part", full_text=query, page=1, page_size=20, include_count=True)
    for _ in range(10):
        t_s, _ = _measure(
            lambda: svc.search(
                item_type_id="Part",
                full_text=query,
                page=1,
                page_size=20,
                include_count=True,
            )
        )
        timings.append(t_s)

    p50 = statistics.median(timings)
    p95 = _percentile(timings, 0.95)
    measured_s = p95
    status = "PASS" if measured_s < 0.8 else "FAIL"

    return ScenarioResult(
        name="Reports advanced search response (p95 over 10 runs)",
        target="< 800ms",
        threshold_s=0.8,
        measured_s=measured_s,
        status=status,
        notes=f"query={query!r}, p50={_fmt_duration_s(p50)}, p95={_fmt_duration_s(p95)}",
    )


def _scenario_reports_summary(session) -> ScenarioResult:
    from yuantus.meta_engine.services.report_service import ReportService

    svc = ReportService(session)
    timings: List[float] = []

    # Warm-up
    svc.get_summary()
    for _ in range(10):
        t_s, _ = _measure(lambda: svc.get_summary())
        timings.append(t_s)

    p50 = statistics.median(timings)
    p95 = _percentile(timings, 0.95)
    measured_s = p95
    status = "PASS" if measured_s < 0.2 else "FAIL"

    return ScenarioResult(
        name="Reports summary (p95 over 10 runs)",
        target="< 200ms",
        threshold_s=0.2,
        measured_s=measured_s,
        status=status,
        notes=f"p50={_fmt_duration_s(p50)}, p95={_fmt_duration_s(p95)}",
    )


def _scenario_saved_search_run(session, *, query: str) -> ScenarioResult:
    from yuantus.meta_engine.reports.search_service import SavedSearchService

    svc = SavedSearchService(session)
    saved = svc.create_saved_search(
        name="Perf Saved Search",
        description="perf harness",
        owner_id=1,
        is_public=False,
        item_type_id="Part",
        criteria={"item_type_id": "Part", "full_text": query},
        display_columns=None,
        page_size=20,
    )

    timings: List[float] = []

    # Warm-up
    svc.run_saved_search(saved.id, page=1, page_size=20)
    for _ in range(10):
        t_s, _ = _measure(lambda: svc.run_saved_search(saved.id, page=1, page_size=20))
        timings.append(t_s)

    p50 = statistics.median(timings)
    p95 = _percentile(timings, 0.95)
    measured_s = p95
    status = "PASS" if measured_s < 1.0 else "FAIL"

    return ScenarioResult(
        name="Saved search run (p95 over 10 runs)",
        target="< 1.0s",
        threshold_s=1.0,
        measured_s=measured_s,
        status=status,
        notes=f"page_size=20, query={query!r}, p50={_fmt_duration_s(p50)}, p95={_fmt_duration_s(p95)}",
    )


def _scenario_report_execute(session, *, query: str) -> ScenarioResult:
    from yuantus.meta_engine.reports.report_service import ReportDefinitionService

    svc = ReportDefinitionService(session)
    report = svc.create_definition(
        name="Perf Report Execute",
        code="PERF-P5-EXEC",
        description="perf harness",
        category="perf",
        report_type="table",
        data_source={"type": "query", "item_type_id": "Part", "full_text": query},
        layout=None,
        parameters=None,
        owner_id=1,
        is_public=False,
        allowed_roles=None,
        is_active=True,
        created_by_id=1,
    )

    timings: List[float] = []
    svc.execute_definition(report.id, page=1, page_size=200, user_id=1)
    for _ in range(5):
        t_s, _ = _measure(lambda: svc.execute_definition(report.id, page=1, page_size=200, user_id=1))
        timings.append(t_s)

    p50 = statistics.median(timings)
    p95 = _percentile(timings, 0.95)
    measured_s = p95
    status = "PASS" if measured_s < 1.2 else "FAIL"

    return ScenarioResult(
        name="Report execute (p95 over 5 runs)",
        target="< 1.2s",
        threshold_s=1.2,
        measured_s=measured_s,
        status=status,
        notes=f"page_size=200, query={query!r}, p50={_fmt_duration_s(p50)}, p95={_fmt_duration_s(p95)}",
    )


def _scenario_report_export_csv(session, *, query: str) -> ScenarioResult:
    from yuantus.meta_engine.reports.report_service import ReportDefinitionService

    svc = ReportDefinitionService(session)
    report = svc.create_definition(
        name="Perf Report Export",
        code="PERF-P5-EXPORT",
        description="perf harness",
        category="perf",
        report_type="table",
        data_source={"type": "query", "item_type_id": "Part", "full_text": query},
        layout=None,
        parameters=None,
        owner_id=1,
        is_public=False,
        allowed_roles=None,
        is_active=True,
        created_by_id=1,
    )

    timings: List[float] = []
    svc.export_definition(report.id, export_format="csv", page=1, page_size=500, user_id=1)
    for _ in range(5):
        t_s, _ = _measure(
            lambda: svc.export_definition(
                report.id,
                export_format="csv",
                page=1,
                page_size=500,
                user_id=1,
            )
        )
        timings.append(t_s)

    p50 = statistics.median(timings)
    p95 = _percentile(timings, 0.95)
    measured_s = p95
    status = "PASS" if measured_s < 1.5 else "FAIL"

    return ScenarioResult(
        name="Report export CSV (p95 over 5 runs)",
        target="< 1.5s",
        threshold_s=1.5,
        measured_s=measured_s,
        status=status,
        notes=f"page_size=500, query={query!r}, p50={_fmt_duration_s(p50)}, p95={_fmt_duration_s(p95)}",
    )


def _write_report(path: Path, *, results: List[ScenarioResult], db_url: str, started: str, ended: str, git: str) -> None:
    duration_s = 0.0
    try:
        start_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(ended.replace("Z", "+00:00"))
        duration_s = max(0.0, (end_dt - start_dt).total_seconds())
    except Exception:
        duration_s = 0.0

    pass_count = sum(1 for r in results if r.status == "PASS")
    fail_count = sum(1 for r in results if r.status == "FAIL")

    lines: List[str] = []
    lines.append("# Phase 5 Reports/Search Performance Report")
    lines.append("")
    lines.append(f"- Started: `{started}`")
    lines.append(f"- Ended: `{ended}`")
    lines.append(f"- Duration: `{int(duration_s)}s`")
    lines.append(f"- Git: `{git}`")
    lines.append(f"- DB: `{db_url}`")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| Scenario | Target | Measured | Status | Notes |")
    lines.append("| --- | --- | --- | --- | --- |")
    for r in results:
        measured = _fmt_duration_s(r.measured_s) if r.measured_s is not None else "-"
        notes = (r.notes or "").replace("\n", " ").strip()
        lines.append(f"| {r.name} | {r.target} | {measured} | {r.status} | {notes} |")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- PASS: {pass_count}")
    lines.append(f"- FAIL: {fail_count}")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Measurements use p95 across repeated runs to reduce noise.")
    lines.append("- This harness runs in-process SQLAlchemy against a local SQLite database by default.")
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 5 (reports/search) performance harness")
    parser.add_argument(
        "--out",
        default="",
        help="Output markdown path (default: docs/PERFORMANCE_REPORTS/P5_REPORTS_PERF_<timestamp>.md)",
    )
    parser.add_argument(
        "--db-url",
        default="",
        help="SQLAlchemy database URL (default: sqlite under tmp/perf)",
    )
    parser.add_argument(
        "--seed-items",
        type=int,
        default=5000,
        help="Number of Part items to seed (default: 5000)",
    )
    parser.add_argument(
        "--seed-jobs",
        type=int,
        default=500,
        help="Number of conversion jobs to seed (default: 500)",
    )
    parser.add_argument(
        "--seed-files",
        type=int,
        default=500,
        help="Number of file containers to seed (default: 500)",
    )
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = (
        Path(args.out)
        if args.out
        else REPO_ROOT / "docs" / "PERFORMANCE_REPORTS" / f"P5_REPORTS_PERF_{timestamp}.md"
    )
    _ensure_dir(out_path.parent)

    db_url = args.db_url
    if not db_url:
        db_dir = REPO_ROOT / "tmp" / "perf"
        _ensure_dir(db_dir)
        db_path = db_dir / f"p5_reports_{timestamp}.db"
        db_url = f"sqlite:///{db_path}"

    os.environ.setdefault("YUANTUS_DATABASE_URL", db_url)
    os.environ.setdefault("YUANTUS_IDENTITY_DATABASE_URL", db_url)
    os.environ.setdefault("YUANTUS_ENVIRONMENT", "dev")
    os.environ.setdefault("YUANTUS_SCHEMA_MODE", "create_all")

    from sqlalchemy.orm import sessionmaker

    from yuantus.database import create_db_engine, init_db
    from yuantus.meta_engine.bootstrap import import_all_models

    started = _now_iso()
    git = _git_short_sha()

    import_all_models()
    engine = create_db_engine(db_url)
    init_db(create_tables=True, bind_engine=engine)

    SessionLocal = sessionmaker(
        autocommit=False, autoflush=False, expire_on_commit=False, bind=engine
    )

    query = "PERF-P5-REPORTS"

    with SessionLocal() as session:
        _ensure_item_types(session)
        _ensure_rbac_user(session, user_id=1, username="admin")
        _create_parts(session, count=max(0, int(args.seed_items)), prefix=query)
        _create_conversion_jobs(session, count=max(0, int(args.seed_jobs)))
        _create_files(session, count=max(0, int(args.seed_files)), prefix=query)

        results: List[ScenarioResult] = []
        results.append(_scenario_reports_summary(session))
        results.append(_scenario_reports_search(session, query=query))
        results.append(_scenario_saved_search_run(session, query=query))
        results.append(_scenario_report_execute(session, query=query))
        results.append(_scenario_report_export_csv(session, query=query))

    ended = _now_iso()
    _write_report(out_path, results=results, db_url=db_url, started=started, ended=ended, git=git)
    print(f"Report: {out_path}")

    failed = [r for r in results if r.status == "FAIL"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
