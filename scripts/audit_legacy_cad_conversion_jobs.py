#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from sqlalchemy import MetaData, Table, inspect, select

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from yuantus.config import get_settings
from yuantus.context import org_id_var, tenant_id_var
from yuantus.database import SessionLocal, get_sessionmaker_for_scope
from yuantus.meta_engine.models.file import FileContainer
from yuantus.security.rbac.models import RBACUser  # noqa: F401  # mapper registration


_ACTIVE_STATUSES = {"pending", "processing"}
_TERMINAL_STATUSES = {"completed", "failed", "cancelled"}
_DEFAULT_SCAN_ROOTS = ("src", "scripts")
_LEGACY_CONVERSION_TABLE_NAME = "cad_conversion_jobs"

_REFERENCE_PATTERNS: Sequence[tuple[str, str]] = (
    ("table_name", "cad_conversion_jobs"),
    ("legacy_service_definition", "def create_conversion_job("),
    ("legacy_service_call", "create_conversion_job("),
    ("legacy_model_import", "meta_engine.models.file import ConversionJob"),
    ("legacy_dual_read_query", "query(ConversionJob)"),
    ("legacy_dual_read_get", "get(ConversionJob"),
)
_NON_BLOCKING_REFERENCE_KINDS = {"legacy_service_definition"}


@dataclass
class LegacyConversionJobAuditRow:
    job_id: str
    source_file_id: Optional[str]
    result_file_id: Optional[str]
    target_format: Optional[str]
    operation_type: Optional[str]
    status: Optional[str]
    error_message: Optional[str]
    created_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    source_file_exists: bool
    result_file_exists: Optional[bool]
    flags: List[str]


@dataclass
class LegacyCodeReferenceRow:
    path: str
    line_no: int
    scope: str
    kind: str
    text: str


def _open_session(tenant: Optional[str], org: Optional[str]):
    settings = get_settings()
    if settings.TENANCY_MODE in ("db-per-tenant", "db-per-tenant-org"):
        if not tenant:
            raise SystemExit("TENANCY_MODE requires --tenant")
        tenant_id_var.set(tenant)
        if settings.TENANCY_MODE == "db-per-tenant-org":
            if not org:
                raise SystemExit("TENANCY_MODE=db-per-tenant-org requires --org")
            org_id_var.set(org)
        session_factory = get_sessionmaker_for_scope(tenant, org)
        return session_factory()
    return SessionLocal()


def _iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    try:
        return value.isoformat()
    except Exception:
        return str(value)


def _flags_for_job(
    *,
    status: Optional[str],
    result_file_id: Optional[str],
    error_message: Optional[str],
    source_exists: bool,
    result_exists: Optional[bool],
) -> List[str]:
    flags: List[str] = []
    status = str(status or "").strip().lower()
    if not source_exists:
        flags.append("missing_source_file")
    if status == "completed" and not result_file_id:
        flags.append("completed_without_result")
    if result_file_id and result_exists is False:
        flags.append("missing_result_file")
    if status == "failed" and not str(error_message or "").strip():
        flags.append("failed_without_error")
    return flags


def collect_legacy_conversion_job_rows(
    session, *, limit: Optional[int] = None
) -> List[LegacyConversionJobAuditRow]:
    rows: List[LegacyConversionJobAuditRow] = []
    jobs_table = _get_legacy_jobs_table(session)
    if jobs_table is None:
        return rows
    files_table = FileContainer.__table__
    stmt = select(jobs_table).order_by(jobs_table.c.created_at.asc())
    if limit and limit > 0:
        stmt = stmt.limit(limit)
    job_rows = list(session.execute(stmt).mappings())

    file_ids = {
        str(fid)
        for row in job_rows
        for fid in (row.get("source_file_id"), row.get("result_file_id"))
        if fid
    }
    existing_file_ids: set[str] = set()
    if file_ids:
        existing_file_ids = {
            str(fid)
            for fid in session.execute(
                select(files_table.c.id).where(files_table.c.id.in_(sorted(file_ids)))
            ).scalars()
        }

    for job in job_rows:
        source_file_id = job.get("source_file_id")
        result_file_id = job.get("result_file_id")
        source_exists = bool(source_file_id and str(source_file_id) in existing_file_ids)
        result_exists: Optional[bool]
        if result_file_id:
            result_exists = str(result_file_id) in existing_file_ids
        else:
            result_exists = None
        rows.append(
            LegacyConversionJobAuditRow(
                job_id=str(job.get("id")),
                source_file_id=str(source_file_id) if source_file_id else None,
                result_file_id=str(result_file_id) if result_file_id else None,
                target_format=job.get("target_format"),
                operation_type=job.get("operation_type"),
                status=job.get("status"),
                error_message=job.get("error_message"),
                created_at=_iso(job.get("created_at")),
                started_at=_iso(job.get("started_at")),
                completed_at=_iso(job.get("completed_at")),
                source_file_exists=source_exists,
                result_file_exists=result_exists,
                flags=_flags_for_job(
                    status=job.get("status"),
                    result_file_id=str(result_file_id) if result_file_id else None,
                    error_message=job.get("error_message"),
                    source_exists=source_exists,
                    result_exists=result_exists,
                ),
            )
        )
    return rows


def legacy_table_present(session) -> bool:
    bind = session.get_bind()
    if bind is None:
        return False
    return bool(inspect(bind).has_table(_LEGACY_CONVERSION_TABLE_NAME))


def _get_legacy_jobs_table(session) -> Optional[Table]:
    bind = session.get_bind()
    if bind is None:
        return None
    inspector = inspect(bind)
    if not inspector.has_table(_LEGACY_CONVERSION_TABLE_NAME):
        return None
    metadata = MetaData()
    return Table(_LEGACY_CONVERSION_TABLE_NAME, metadata, autoload_with=bind)


def _classify_scope(relative_path: Path) -> str:
    path_str = relative_path.as_posix()
    if "/tests/" in f"/{path_str}":
        return "test"
    if path_str.startswith("scripts/"):
        return "script"
    if path_str.startswith("docs/"):
        return "doc"
    return "production"


def _extract_legacy_conversion_job_aliases(
    text: str, lines: Sequence[str]
) -> tuple[set[str], List[tuple[int, str]]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set(), []
    aliases: set[str] = set()
    import_rows: List[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "yuantus.meta_engine.models.file":
            continue
        for alias in node.names:
            if alias.name != "ConversionJob":
                continue
            aliases.add(alias.asname or alias.name)
            lineno = getattr(node, "lineno", 1)
            text_line = lines[lineno - 1].strip() if 0 < lineno <= len(lines) else ""
            import_rows.append((lineno, text_line))
    return aliases, import_rows


def collect_legacy_code_references(
    repo_root: Path,
    *,
    scan_roots: Sequence[str] = _DEFAULT_SCAN_ROOTS,
) -> List[LegacyCodeReferenceRow]:
    rows: List[LegacyCodeReferenceRow] = []
    seen: set[tuple[str, int, str]] = set()
    for root_name in scan_roots:
        root = repo_root / root_name
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            rel = path.relative_to(repo_root)
            try:
                text = path.read_text(encoding="utf-8")
                lines = text.splitlines()
            except UnicodeDecodeError:
                continue
            scope = _classify_scope(rel)
            legacy_aliases, legacy_import_rows = _extract_legacy_conversion_job_aliases(
                text, lines
            )
            for lineno, import_text in legacy_import_rows:
                key = (rel.as_posix(), lineno, "legacy_model_import")
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    LegacyCodeReferenceRow(
                        path=rel.as_posix(),
                        line_no=lineno,
                        scope=scope,
                        kind="legacy_model_import",
                        text=import_text,
                    )
                )
            for idx, line in enumerate(lines, start=1):
                stripped = line.strip()
                for kind, needle in _REFERENCE_PATTERNS:
                    if kind == "legacy_model_import":
                        continue
                    if kind == "legacy_dual_read_query":
                        if not any(f"query({alias})" in line for alias in legacy_aliases):
                            continue
                    elif kind == "legacy_dual_read_get":
                        if not any(f"get({alias}" in line for alias in legacy_aliases):
                            continue
                    elif needle not in line:
                        continue
                    if kind == "legacy_service_call" and stripped.startswith(
                        "def create_conversion_job("
                    ):
                        continue
                    key = (rel.as_posix(), idx, kind)
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append(
                        LegacyCodeReferenceRow(
                            path=rel.as_posix(),
                            line_no=idx,
                            scope=scope,
                            kind=kind,
                            text=stripped,
                        )
                    )
    rows.sort(key=lambda row: (row.scope, row.path, row.line_no, row.kind))
    return rows


def build_report(
    rows: List[LegacyConversionJobAuditRow],
    *,
    detail_limit: int = 50,
    code_references: Optional[List[LegacyCodeReferenceRow]] = None,
    legacy_table_present_flag: bool = True,
) -> Dict[str, Any]:
    counts_by_status: Dict[str, int] = {}
    counts_by_target_format: Dict[str, int] = {}
    counts_by_operation_type: Dict[str, int] = {}
    counts_by_flag: Dict[str, int] = {}
    active_count = 0
    terminal_count = 0
    for row in rows:
        status = str(row.status or "unknown")
        target_format = str(row.target_format or "unknown")
        operation_type = str(row.operation_type or "unknown")
        counts_by_status[status] = counts_by_status.get(status, 0) + 1
        counts_by_target_format[target_format] = (
            counts_by_target_format.get(target_format, 0) + 1
        )
        counts_by_operation_type[operation_type] = (
            counts_by_operation_type.get(operation_type, 0) + 1
        )
        if status in _ACTIVE_STATUSES:
            active_count += 1
        if status in _TERMINAL_STATUSES:
            terminal_count += 1
        for flag in row.flags:
            counts_by_flag[flag] = counts_by_flag.get(flag, 0) + 1

    details = [asdict(row) for row in rows[: max(0, int(detail_limit))]]
    report: Dict[str, Any] = {
        "job_count": len(rows),
        "counts_by_status": counts_by_status,
        "counts_by_target_format": counts_by_target_format,
        "counts_by_operation_type": counts_by_operation_type,
        "counts_by_flag": counts_by_flag,
        "active_job_count": active_count,
        "terminal_job_count": terminal_count,
        "legacy_table_present": legacy_table_present_flag,
        "legacy_queue_drain_complete": active_count == 0,
        "legacy_dual_read_zero_rows": (len(rows) == 0) or (legacy_table_present_flag is False),
        "details": details,
    }

    refs = code_references or []
    counts_by_scope: Dict[str, int] = {}
    counts_by_kind: Dict[str, int] = {}
    for row in refs:
        counts_by_scope[row.scope] = counts_by_scope.get(row.scope, 0) + 1
        counts_by_kind[row.kind] = counts_by_kind.get(row.kind, 0) + 1
    report["code_reference_count"] = len(refs)
    report["code_reference_counts_by_scope"] = counts_by_scope
    report["code_reference_counts_by_kind"] = counts_by_kind
    blocking_production_refs = [
        row
        for row in refs
        if row.scope == "production"
        and row.kind not in _NON_BLOCKING_REFERENCE_KINDS
    ]
    report["blocking_production_reference_count"] = len(blocking_production_refs)
    report["delete_window_ready"] = (
        report["legacy_queue_drain_complete"] is True
        and report["legacy_dual_read_zero_rows"] is True
        and len(blocking_production_refs) == 0
    )
    return report


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_evidence_pack(
    out_dir: Path,
    *,
    report: Dict[str, Any],
    rows: List[LegacyConversionJobAuditRow],
    code_references: List[LegacyCodeReferenceRow],
) -> Dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "summary.json"
    jobs_path = out_dir / "jobs.jsonl"
    pending_path = out_dir / "pending.jsonl"
    anomalies_path = out_dir / "anomalies.jsonl"
    samples_path = out_dir / "samples.json"
    refs_path = out_dir / "code_references.jsonl"
    evidence_paths = {
        "summary": str(summary_path),
        "jobs": str(jobs_path),
        "pending": str(pending_path),
        "anomalies": str(anomalies_path),
        "samples": str(samples_path),
        "code_references": str(refs_path),
    }
    summary_payload = dict(report)
    summary_payload["evidence_dir"] = str(out_dir)
    summary_payload["evidence_files"] = evidence_paths
    _write_json(summary_path, summary_payload)
    all_rows = [asdict(row) for row in rows]
    _write_jsonl(jobs_path, all_rows)
    _write_jsonl(
        pending_path,
        [
            row
            for row in all_rows
            if str(row.get("status") or "").strip().lower() in _ACTIVE_STATUSES
        ],
    )
    _write_jsonl(anomalies_path, [row for row in all_rows if row.get("flags")])
    _write_json(samples_path, report.get("details") or [])
    _write_jsonl(refs_path, [asdict(row) for row in code_references])
    return evidence_paths


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit legacy cad_conversion_jobs rows and code references, and "
            "write an evidence pack."
        )
    )
    parser.add_argument(
        "--tenant", default=None, help="Tenant ID for multi-tenant modes"
    )
    parser.add_argument("--org", default=None, help="Org ID for db-per-tenant-org mode")
    parser.add_argument(
        "--limit", type=int, default=None, help="Optional max number of legacy jobs to scan"
    )
    parser.add_argument(
        "--detail-limit",
        type=int,
        default=50,
        help="How many job detail rows to include in the JSON report",
    )
    parser.add_argument("--json-out", default=None, help="Optional path to write the JSON report")
    parser.add_argument("--out-dir", default=None, help="Optional directory to write summary/evidence files")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Repository root used for code reference scanning",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    code_references = collect_legacy_code_references(repo_root)

    session = _open_session(args.tenant, args.org)
    try:
        table_present = legacy_table_present(session)
        rows = (
            collect_legacy_conversion_job_rows(session, limit=args.limit)
            if table_present
            else []
        )
        report = build_report(
            rows,
            detail_limit=args.detail_limit,
            code_references=code_references,
            legacy_table_present_flag=table_present,
        )
        report["tenant"] = args.tenant
        report["org"] = args.org
        report["repo_root"] = str(repo_root)
        if args.out_dir:
            evidence_paths = _write_evidence_pack(
                Path(args.out_dir),
                report=report,
                rows=rows,
                code_references=code_references,
            )
            report["evidence_dir"] = str(Path(args.out_dir))
            report["evidence_files"] = evidence_paths
        output = json.dumps(report, indent=2, ensure_ascii=False)
        if args.json_out:
            Path(args.json_out).write_text(output + "\n", encoding="utf-8")
        print(output)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
