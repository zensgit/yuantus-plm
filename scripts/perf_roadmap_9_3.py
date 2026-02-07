#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import socket


REPO_ROOT = Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _git_short_sha() -> str:
    try:
        out = subprocess.check_output(
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


@dataclass
class ScenarioResult:
    name: str
    target: str
    threshold_s: Optional[float]
    measured_s: Optional[float]
    status: str
    notes: str = ""


def _measure(fn) -> Tuple[float, Any]:
    start = time.perf_counter()
    value = fn()
    end = time.perf_counter()
    return end - start, value


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    # Nearest-rank percentile (ceil(p * N)).
    idx = int(math.ceil(p * len(sorted_vals))) - 1
    idx = max(0, min(len(sorted_vals) - 1, idx))
    return sorted_vals[idx]


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _http_get_status(url: str, *, timeout_s: float = 2.0) -> Optional[int]:
    import urllib.request

    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return int(getattr(resp, "status", 200))
    except Exception:
        return None


def _wait_http_200(url: str, *, timeout_s: float = 30.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        status = _http_get_status(url, timeout_s=2.0)
        if status == 200:
            return True
        time.sleep(0.5)
    return False


def _find_dedup_vision_root() -> Optional[Path]:
    candidates = [
        REPO_ROOT / ".." / "dedupcad-vision",
        Path("/Users/huazhou/Downloads/Github/dedupcad-vision"),
    ]
    for candidate in candidates:
        start = candidate / "start_server.py"
        if start.is_file():
            return candidate.resolve()
    return None


def _start_dedup_vision_server(*, port: int, log_path: Path) -> Optional[subprocess.Popen]:
    """
    Start DedupCAD Vision as a sidecar process for the perf harness.

    We intentionally keep this dependency opt-in: if the repo isn't available,
    we return None and allow the scenario to SKIP.
    """
    root = _find_dedup_vision_root()
    if root is None:
        return None

    cmd = [
        "python3",
        str(root / "start_server.py"),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]

    env = dict(os.environ)
    # Disable optional integrations to keep the perf harness self-contained.
    env.setdefault("S3_ENABLED", "false")
    env.setdefault("EVENT_BUS_ENABLED", "false")
    env.setdefault("INTEGRATION_AUTH_MODE", "disabled")

    _ensure_dir(log_path.parent)
    log_f = open(log_path, "ab", buffering=0)
    return subprocess.Popen(  # noqa: S603,S607
        cmd,
        env=env,
        stdout=log_f,
        stderr=subprocess.STDOUT,
    )


def _stop_process(proc: Optional[subprocess.Popen]) -> None:
    if not proc:
        return
    try:
        proc.terminate()
        proc.wait(timeout=10)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _create_minimal_png_bytes(width: int, height: int) -> bytes:
    import struct
    import zlib

    width = max(1, int(width))
    height = max(1, int(height))
    row = b"\x00" + (b"\x80\x80\x80" * width)
    raw = row * height
    compressed = zlib.compress(raw)

    def _chunk(tag: bytes, payload: bytes) -> bytes:
        length = struct.pack(">I", len(payload))
        crc = struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        return length + tag + payload + crc

    # PNG signature + IHDR + IDAT + IEND
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            _chunk(b"IHDR", ihdr),
            _chunk(b"IDAT", compressed),
            _chunk(b"IEND", b""),
        ]
    )


def _ensure_item_types(session) -> None:
    from yuantus.meta_engine.models.meta_schema import ItemType

    def upsert(
        item_type_id: str,
        *,
        label: Optional[str] = None,
        is_relationship: bool = False,
        source_item_type_id: Optional[str] = None,
        related_item_type_id: Optional[str] = None,
    ) -> None:
        existing = session.get(ItemType, item_type_id)
        if existing:
            return
        session.add(
            ItemType(
                id=item_type_id,
                label=label or item_type_id,
                is_relationship=bool(is_relationship),
                source_item_type_id=source_item_type_id,
                related_item_type_id=related_item_type_id,
            )
        )

    upsert("Part", label="Part", is_relationship=False)
    upsert(
        "Part BOM",
        label="Part BOM",
        is_relationship=True,
        source_item_type_id="Part",
        related_item_type_id="Part",
    )
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


def _create_parts(session, *, count: int, prefix: str) -> List[str]:
    from yuantus.meta_engine.models.item import Item

    ids: List[str] = []
    items: List[Item] = []
    for i in range(count):
        item_id = str(uuid.uuid4())
        ids.append(item_id)
        items.append(
            Item(
                id=item_id,
                item_type_id="Part",
                config_id=str(uuid.uuid4()),
                generation=1,
                is_current=True,
                state="Draft",
                properties={
                    "item_number": f"{prefix}-{i:06d}",
                    "name": f"{prefix} Part {i}",
                },
            )
        )
    session.add_all(items)
    session.commit()
    return ids


def _create_bom_relationships(
    session,
    *,
    edges: List[Tuple[str, str]],
    config_condition: Optional[str] = None,
) -> None:
    from yuantus.meta_engine.models.item import Item

    rels: List[Item] = []
    for parent_id, child_id in edges:
        props: Dict[str, Any] = {"quantity": 1, "uom": "EA"}
        if config_condition is not None:
            props["config_condition"] = config_condition
        rels.append(
            Item(
                id=str(uuid.uuid4()),
                item_type_id="Part BOM",
                config_id=str(uuid.uuid4()),
                generation=1,
                is_current=True,
                state="Active",
                source_id=parent_id,
                related_id=child_id,
                properties=props,
            )
        )
    session.add_all(rels)
    session.commit()


def _scenario_config_bom_500_levels(session) -> ScenarioResult:
    from yuantus.meta_engine.services.bom_service import BOMService

    part_ids = _create_parts(session, count=500, prefix="PERF-CFG")

    edges = list(zip(part_ids[:-1], part_ids[1:]))
    _create_bom_relationships(session, edges=edges, config_condition="Color=Red")

    svc = BOMService(session)
    selection = {"Color": "Red"}
    measured_s, tree = _measure(lambda: svc.get_tree(part_ids[0], depth=500, config_selection=selection))
    # Basic sanity check to prevent measuring a broken empty traversal.
    if not isinstance(tree, dict) or not tree.get("children"):
        return ScenarioResult(
            name="Config BOM calculation (500 levels)",
            target="< 5s",
            threshold_s=5.0,
            measured_s=measured_s,
            status="FAIL",
            notes="tree empty/unexpected response",
        )

    status = "PASS" if measured_s < 5.0 else "FAIL"
    return ScenarioResult(
        name="Config BOM calculation (500 levels)",
        target="< 5s",
        threshold_s=5.0,
        measured_s=measured_s,
        status=status,
        notes=f"depth=500, config_selection_keys={list(selection.keys())}",
    )


def _scenario_mbom_convert_1000_lines(session) -> ScenarioResult:
    from yuantus.meta_engine.services.bom_conversion_service import BOMConversionService

    # Root + 1000 children => 1000 EBOM BOM lines.
    part_ids = _create_parts(session, count=1001, prefix="PERF-EBOM")
    root_id = part_ids[0]
    edges = [(root_id, child_id) for child_id in part_ids[1:]]
    _create_bom_relationships(session, edges=edges)

    svc = BOMConversionService(session)
    measured_s, mbom_root = _measure(lambda: svc.convert_ebom_to_mbom(root_id, user_id=1))
    status = "PASS" if measured_s < 30.0 else "FAIL"
    notes = "lines=1000, substitutes=0"
    if not getattr(mbom_root, "id", None):
        status = "FAIL"
        notes = "conversion returned empty root"

    return ScenarioResult(
        name="MBOM conversion (1000 lines)",
        target="< 30s",
        threshold_s=30.0,
        measured_s=measured_s,
        status=status,
        notes=notes,
    )


def _scenario_baseline_create_2000_members(session) -> ScenarioResult:
    from yuantus.meta_engine.services.baseline_service import BaselineService

    # Root + 1999 children => 2000 members (star topology, depth=1).
    part_ids = _create_parts(session, count=2000, prefix="PERF-BL")
    root_id = part_ids[0]
    edges = [(root_id, child_id) for child_id in part_ids[1:]]
    _create_bom_relationships(session, edges=edges)

    svc = BaselineService(session)
    measured_s, baseline = _measure(
        lambda: svc.create_baseline(
            name=f"perf-baseline-{uuid.uuid4().hex[:6]}",
            description=None,
            root_item_id=root_id,
            root_version_id=None,
            max_levels=1,
            effective_at=None,
            include_substitutes=False,
            include_effectivity=False,
            line_key="child_config",
            created_by_id=1,
            roles=["admin"],
            baseline_type="bom",
            scope="product",
        )
    )

    status = "PASS" if measured_s < 60.0 else "FAIL"
    item_count = int(getattr(baseline, "item_count", 0) or 0)
    if item_count < 2000:
        status = "FAIL"

    return ScenarioResult(
        name="Baseline create (2000 members)",
        target="< 60s",
        threshold_s=60.0,
        measured_s=measured_s,
        status=status,
        notes=f"max_levels=1, item_count={item_count}",
    )


def _scenario_search_response(session) -> ScenarioResult:
    from yuantus.meta_engine.services.search_service import SearchService

    # Seed a moderate dataset for fallback DB search. The ES path is environment-dependent.
    _create_parts(session, count=5000, prefix="PERF-SEARCH")

    svc = SearchService(session)
    query = "PERF-SEARCH"
    timings: List[float] = []
    # Warm-up (SQLite page cache + query plan)
    svc.search(query, filters={"item_type_id": "Part"}, limit=20)
    for _ in range(10):
        t_s, _result = _measure(lambda: svc.search(query, filters={"item_type_id": "Part"}, limit=20))
        timings.append(t_s)

    p50 = statistics.median(timings)
    p95 = _percentile(timings, 0.95)
    measured_s = p95
    status = "PASS" if measured_s < 0.5 else "FAIL"
    engine = "db" if svc.client is None else "elasticsearch"

    return ScenarioResult(
        name="Full-text search response (p95 over 10 runs)",
        target="< 500ms",
        threshold_s=0.5,
        measured_s=measured_s,
        status=status,
        notes=f"engine={engine}, query={query!r}, p50={_fmt_duration_s(p50)}, p95={_fmt_duration_s(p95)}",
    )


def _scenario_esign_verify(session) -> ScenarioResult:
    from yuantus.meta_engine.esign.service import ElectronicSignatureService
    from yuantus.meta_engine.models.item import Item

    _ensure_rbac_user(session, user_id=1, username="admin")

    item = Item(
        id=str(uuid.uuid4()),
        item_type_id="Part",
        config_id=str(uuid.uuid4()),
        generation=1,
        is_current=True,
        state="Draft",
        properties={"item_number": "PERF-ESIGN-0001", "name": "Perf Sign"},
        created_by_id=1,
    )
    session.add(item)
    session.commit()

    svc = ElectronicSignatureService(session, secret_key="perf-dev-secret")
    signature = svc.sign(
        item_id=item.id,
        user_id=1,
        tenant_id=None,
        meaning="approve",
        password=None,
        reason_id=None,
        reason_text="perf",
        comment="perf",
    )

    timings: List[float] = []
    for _ in range(20):
        t_s, result = _measure(lambda: svc.verify(signature.id, actor_id=1, actor_username="admin"))
        timings.append(t_s)
        if not result.get("is_valid", False):
            return ScenarioResult(
                name="Electronic signature verify",
                target="< 100ms",
                threshold_s=0.1,
                measured_s=t_s,
                status="FAIL",
                notes="signature verification returned invalid",
            )

    p50 = statistics.median(timings)
    p95 = _percentile(timings, 0.95)
    measured_s = p95
    status = "PASS" if measured_s < 0.1 else "FAIL"

    return ScenarioResult(
        name="Electronic signature verify (p95 over 20 runs)",
        target="< 100ms",
        threshold_s=0.1,
        measured_s=measured_s,
        status=status,
        notes=f"p50={_fmt_duration_s(p50)}, p95={_fmt_duration_s(p95)}",
    )


def _scenario_dedup_batch_enqueue_1000(session) -> ScenarioResult:
    """
    Roadmap 9.3 defines "dedup batch processing 1000 files < 10 minutes".

    This scenario measures end-to-end job execution:
    - create 1000 FileContainer rows + local files
    - enqueue 1000 `cad_dedup_vision` jobs via DedupService.run_batch()
    - process all jobs synchronously in-process using cad_dedup_vision() handler
    """

    from yuantus.meta_engine.dedup.service import DedupService
    from yuantus.meta_engine.models.file import FileContainer
    from yuantus.meta_engine.services.job_service import JobService
    from yuantus.meta_engine.tasks.cad_pipeline_tasks import cad_dedup_vision

    base_url = os.environ.get("YUANTUS_DEDUP_VISION_BASE_URL", "").strip()
    if not base_url:
        # Keep this in sync with Settings default.
        base_url = "http://127.0.0.1:8100"

    if _http_get_status(f"{base_url}/health", timeout_s=1.0) != 200:
        return ScenarioResult(
            name="Dedup batch (1000 files) processing",
            target="< 10m",
            threshold_s=600.0,
            measured_s=None,
            status="SKIP",
            notes=f"Dedup Vision not healthy at {base_url} (expected /health=200)",
        )

    storage_path_raw = (os.environ.get("YUANTUS_LOCAL_STORAGE_PATH") or "").strip()
    if not storage_path_raw:
        return ScenarioResult(
            name="Dedup batch (1000 files) processing",
            target="< 10m",
            threshold_s=600.0,
            measured_s=None,
            status="SKIP",
            notes="YUANTUS_LOCAL_STORAGE_PATH not set (perf harness requires isolated local storage)",
        )

    storage_base = Path(storage_path_raw).resolve()
    if not storage_base.exists():
        return ScenarioResult(
            name="Dedup batch (1000 files) processing",
            target="< 10m",
            threshold_s=600.0,
            measured_s=None,
            status="SKIP",
            notes=f"Local storage path missing: {storage_base}",
        )

    png_bytes = _create_minimal_png_bytes(128, 128)

    files: List[FileContainer] = []
    for i in range(1000):
        rel_path = f"perf/dedup/{i:04d}.png"
        full_path = storage_base / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(png_bytes)
        files.append(
            FileContainer(
                id=str(uuid.uuid4()),
                filename=f"perf_{i:04d}.png",
                file_type="png",
                mime_type="image/png",
                file_size=len(png_bytes),
                checksum=str(uuid.uuid4()).replace("-", ""),
                system_path=f"/{rel_path}",
                document_type="2d",
            )
        )
    session.add_all(files)
    session.commit()

    svc = DedupService(session)
    batch = svc.create_batch({"name": "perf-dedup", "scope_type": "all"}, user_id=1)

    enqueue_s, (job_count, _job_ids) = _measure(
        lambda: svc.run_batch(
            batch,
            user_id=1,
            user_name="admin",
            mode="fast",
            limit=1000,
            priority=30,
            dedupe=True,
        )
    )

    job_service = JobService(session)
    processed = 0
    start = time.perf_counter()
    deadline = start + 600.0
    last_error: Optional[str] = None

    while True:
        if time.perf_counter() > deadline:
            break
        job = job_service.poll_next_job("perf-worker")
        if not job:
            break
        try:
            result = cad_dedup_vision(job.payload, session)
            job_service.complete_job(job.id, result=result)
        except Exception as exc:
            last_error = str(exc)
            job_service.fail_job(job.id, str(exc), retry=False)
        processed += 1

    measured_s = time.perf_counter() - start
    status = "PASS" if processed == job_count and measured_s < 600.0 and not last_error else "FAIL"
    notes = (
        f"base_url={base_url}, mode=fast, files=1000, jobs={job_count}, "
        f"processed={processed}, enqueue_time={_fmt_duration_s(enqueue_s)}"
    )
    if last_error:
        notes += f", last_error={last_error}"

    return ScenarioResult(
        name="Dedup batch (1000 files) processing",
        target="< 10m",
        threshold_s=600.0,
        measured_s=measured_s if processed == job_count else None,
        status=status,
        notes=notes,
    )


def _write_report(path: Path, *, results: List[ScenarioResult], db_url: str) -> None:
    sha = _git_short_sha()
    started = _now_iso()
    host = platform.node()
    py = sys.version.split()[0]
    os_name = f"{platform.system()} {platform.release()}"
    storage_root = (os.environ.get("YUANTUS_LOCAL_STORAGE_PATH") or "").strip()
    dedup_base_url = (os.environ.get("YUANTUS_DEDUP_VISION_BASE_URL") or "").strip()
    dedup_log = (os.environ.get("PERF_DEDUP_VISION_LOG_PATH") or "").strip()

    pass_count = sum(1 for r in results if r.status == "PASS")
    fail_count = sum(1 for r in results if r.status == "FAIL")
    skip_count = sum(1 for r in results if r.status == "SKIP")

    lines: List[str] = []
    lines.append("# Roadmap 9.3 Performance Benchmark Report")
    lines.append("")
    lines.append(f"- Started: `{started}`")
    lines.append(f"- Git: `{sha}`")
    lines.append(f"- Host: `{host}`")
    lines.append(f"- OS: `{os_name}`")
    lines.append(f"- Python: `{py}`")
    lines.append(f"- DB: `{db_url}`")
    if storage_root:
        lines.append(f"- Local storage: `{storage_root}`")
    if dedup_base_url:
        lines.append(f"- Dedup Vision: `{dedup_base_url}`")
    if dedup_log:
        lines.append(f"- Dedup Vision log: `{dedup_log}`")
    lines.append("- Method: In-process SQLAlchemy service calls; dedup scenario uses HTTP to Dedup Vision when available.")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| Scenario | Target | Measured | Status | Notes |")
    lines.append("| --- | --- | --- | --- | --- |")
    for r in results:
        measured = _fmt_duration_s(r.measured_s) if r.measured_s is not None else "-"
        notes = r.notes.replace("\n", " ").strip()
        lines.append(f"| {r.name} | {r.target} | {measured} | {r.status} | {notes} |")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- PASS: {pass_count}")
    lines.append(f"- FAIL: {fail_count}")
    lines.append(f"- SKIP: {skip_count}")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- SKIP entries indicate missing external dependencies or not-yet-wired benchmark harness paths.")
    lines.append("- Search measurement uses p95 over 10 runs; e-sign verification uses p95 over 20 runs.")
    lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Roadmap 9.3 performance benchmark harness")
    parser.add_argument(
        "--out",
        default="",
        help="Output markdown path (default: docs/PERFORMANCE_REPORTS/ROADMAP_9_3_<timestamp>.md)",
    )
    parser.add_argument(
        "--db-url",
        default="",
        help="SQLAlchemy database URL (default: sqlite under tmp/perf)",
    )
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = Path(args.out) if args.out else REPO_ROOT / "docs" / "PERFORMANCE_REPORTS" / f"ROADMAP_9_3_{timestamp}.md"
    _ensure_dir(out_path.parent)

    db_url = args.db_url
    if not db_url:
        db_dir = REPO_ROOT / "tmp" / "perf"
        _ensure_dir(db_dir)
        db_path = db_dir / f"roadmap_9_3_{timestamp}.db"
        db_url = f"sqlite:///{db_path}"

    # Set env for any sub-components that rely on get_settings() defaults.
    os.environ.setdefault("YUANTUS_DATABASE_URL", db_url)
    os.environ.setdefault("YUANTUS_IDENTITY_DATABASE_URL", db_url)
    os.environ.setdefault("YUANTUS_ENVIRONMENT", "dev")
    os.environ.setdefault("YUANTUS_SCHEMA_MODE", "create_all")

    storage_dir = REPO_ROOT / "tmp" / "perf" / f"storage_{timestamp}"
    _ensure_dir(storage_dir)
    # Force an isolated local storage root so the benchmark doesn't pollute dev data.
    os.environ["YUANTUS_STORAGE_TYPE"] = "local"
    os.environ["YUANTUS_LOCAL_STORAGE_PATH"] = str(storage_dir)
    os.environ.setdefault("YUANTUS_LOCAL_STORAGE_PUBLIC_URL_PREFIX", "")

    # Best-effort sidecar: start Dedup Vision if the base URL is local and not already healthy.
    dedup_proc: Optional[subprocess.Popen] = None
    dedup_log_path = REPO_ROOT / "tmp" / "perf" / f"dedup_vision_{timestamp}.log"
    dedup_base_url = (os.environ.get("YUANTUS_DEDUP_VISION_BASE_URL") or "").strip()
    if not dedup_base_url:
        dedup_port = _pick_free_port()
        dedup_base_url = f"http://127.0.0.1:{dedup_port}"
        os.environ["YUANTUS_DEDUP_VISION_BASE_URL"] = dedup_base_url
    dedup_base_url = dedup_base_url.rstrip("/")

    if _http_get_status(f"{dedup_base_url}/health", timeout_s=1.0) != 200:
        from urllib.parse import urlparse

        parsed = urlparse(dedup_base_url)
        host = (parsed.hostname or "").strip().lower()
        port = int(parsed.port or (443 if parsed.scheme == "https" else 80))
        if host in {"127.0.0.1", "localhost"}:
            dedup_proc = _start_dedup_vision_server(port=port, log_path=dedup_log_path)
            if dedup_proc and not _wait_http_200(f"{dedup_base_url}/health", timeout_s=30.0):
                _stop_process(dedup_proc)
                dedup_proc = None
        os.environ.setdefault("PERF_DEDUP_VISION_LOG_PATH", str(dedup_log_path))

    # Import after env is set (some modules initialize engines at import time).
    from sqlalchemy.orm import sessionmaker

    from yuantus.database import create_db_engine, init_db
    from yuantus.meta_engine.bootstrap import import_all_models

    try:
        import_all_models()
        engine = create_db_engine(db_url)
        init_db(create_tables=True, bind_engine=engine)

        SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, expire_on_commit=False, bind=engine
        )

        with SessionLocal() as session:
            _ensure_item_types(session)
            _ensure_rbac_user(session, user_id=1, username="admin")

            results: List[ScenarioResult] = []
            results.append(_scenario_dedup_batch_enqueue_1000(session))
            results.append(_scenario_config_bom_500_levels(session))
            results.append(_scenario_mbom_convert_1000_lines(session))
            results.append(_scenario_baseline_create_2000_members(session))
            results.append(_scenario_search_response(session))
            results.append(_scenario_esign_verify(session))
    finally:
        _stop_process(dedup_proc)

    _write_report(out_path, results=results, db_url=db_url)
    print(f"Report: {out_path}")

    failed = [r for r in results if r.status == "FAIL"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
