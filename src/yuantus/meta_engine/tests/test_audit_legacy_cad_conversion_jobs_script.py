from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import Column, DateTime, MetaData, String, Table, Text, create_engine, insert
from sqlalchemy.orm import sessionmaker

from yuantus.meta_engine.models.file import FileContainer, Vault
from yuantus.models.base import Base
from yuantus.security.rbac.models import RBACUser


def _load_script_module():
    repo_root = Path(__file__).resolve().parents[4]
    script_path = repo_root / "scripts" / "audit_legacy_cad_conversion_jobs.py"
    spec = importlib.util.spec_from_file_location(
        "audit_legacy_cad_conversion_jobs", script_path
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _create_legacy_jobs_table(bind):
    table = Table(
        "cad_conversion_jobs",
        MetaData(),
        Column("id", String, primary_key=True),
        Column("source_file_id", String, nullable=False),
        Column("target_format", String, nullable=False),
        Column("operation_type", String, nullable=True),
        Column("status", String, nullable=True),
        Column("error_message", Text, nullable=True),
        Column("result_file_id", String, nullable=True),
        Column("created_at", DateTime, nullable=True),
        Column("started_at", DateTime, nullable=True),
        Column("completed_at", DateTime, nullable=True),
    )
    table.create(bind=bind)
    return table
def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Vault.__table__,
            RBACUser.__table__,
            FileContainer.__table__,
        ],
    )
    legacy_jobs_table = _create_legacy_jobs_table(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    session.info["legacy_jobs_table"] = legacy_jobs_table
    return session


def test_collect_rows_and_report_counts_anomalies():
    module = _load_script_module()
    session = _session()
    now = datetime.utcnow()

    session.execute(
        insert(FileContainer.__table__).values(
            id="fc-src-1",
            filename="part.step",
            file_type="step",
            system_path="3d/fc/fc-src-1.step",
        )
    )
    session.execute(
        insert(FileContainer.__table__).values(
            id="fc-res-1",
            filename="part.gltf",
            file_type="gltf",
            system_path="geometry/fc/fc-src-1.gltf",
        )
    )
    session.execute(
        insert(session.info["legacy_jobs_table"]).values(
            id="legacy-1",
            source_file_id="fc-src-1",
            target_format="png",
            operation_type="preview",
            status="pending",
            created_at=now - timedelta(hours=3),
        )
    )
    session.execute(
        insert(session.info["legacy_jobs_table"]).values(
            id="legacy-2",
            source_file_id="fc-src-1",
            target_format="gltf",
            operation_type="convert",
            status="completed",
            result_file_id="fc-res-1",
            created_at=now - timedelta(hours=2),
            completed_at=now - timedelta(hours=1),
        )
    )
    session.execute(
        insert(session.info["legacy_jobs_table"]).values(
            id="legacy-3",
            source_file_id="missing-src",
            target_format="obj",
            operation_type="convert",
            status="failed",
            error_message="",
            result_file_id="missing-res",
            created_at=now - timedelta(hours=1),
        )
    )
    session.commit()

    rows = module.collect_legacy_conversion_job_rows(session)
    code_refs = [
        module.LegacyCodeReferenceRow(
            path="src/yuantus/meta_engine/web/file_router.py",
            line_no=10,
            scope="production",
            kind="legacy_service_call",
            text="converter.create_conversion_job(",
        )
    ]
    report = module.build_report(rows, detail_limit=10, code_references=code_refs)

    assert report["job_count"] == 3
    assert report["counts_by_status"]["pending"] == 1
    assert report["counts_by_status"]["completed"] == 1
    assert report["counts_by_status"]["failed"] == 1
    assert report["counts_by_target_format"]["png"] == 1
    assert report["counts_by_flag"]["missing_source_file"] == 1
    assert report["counts_by_flag"]["missing_result_file"] == 1
    assert report["counts_by_flag"]["failed_without_error"] == 1
    assert report["active_job_count"] == 1
    assert report["legacy_queue_drain_complete"] is False
    assert report["legacy_dual_read_zero_rows"] is False
    assert report["code_reference_count"] == 1
    assert report["code_reference_counts_by_scope"]["production"] == 1
    assert report["blocking_production_reference_count"] == 1
    assert report["delete_window_ready"] is False


def test_collect_code_references_scans_repo_roots(tmp_path):
    module = _load_script_module()
    (tmp_path / "src" / "yuantus" / "meta_engine" / "web").mkdir(parents=True)
    (tmp_path / "src" / "yuantus" / "meta_engine" / "services").mkdir(parents=True)
    (tmp_path / "src" / "yuantus" / "api" / "routers").mkdir(parents=True)
    (tmp_path / "scripts").mkdir(parents=True)
    prod = tmp_path / "src" / "yuantus" / "meta_engine" / "web" / "file_router.py"
    prod.write_text(
        "from yuantus.meta_engine.models.file import ConversionJob\n"
        "db.get(ConversionJob, job_id)\n"
        "db.query(ConversionJob)\n"
        "x = 'cad_conversion_jobs'\n",
        encoding="utf-8",
    )
    svc = (
        tmp_path
        / "src"
        / "yuantus"
        / "meta_engine"
        / "services"
        / "cad_converter_service.py"
    )
    svc.write_text("def create_conversion_job(\n", encoding="utf-8")
    meta = tmp_path / "src" / "yuantus" / "api" / "routers" / "jobs.py"
    meta.write_text(
        "from yuantus.meta_engine.models.job import ConversionJob\n"
        "db.get(ConversionJob, job_id)\n"
        "db.query(ConversionJob)\n",
        encoding="utf-8",
    )
    script = tmp_path / "scripts" / "helper.py"
    script.write_text("converter.create_conversion_job(\n", encoding="utf-8")

    rows = module.collect_legacy_code_references(tmp_path)

    assert len(rows) == 6
    assert {row.scope for row in rows} == {"production", "script"}
    assert {row.kind for row in rows} == {
        "legacy_model_import",
        "table_name",
        "legacy_service_call",
        "legacy_service_definition",
        "legacy_dual_read_query",
        "legacy_dual_read_get",
    }
    assert not any(row.path == "src/yuantus/api/routers/jobs.py" for row in rows)


def test_main_out_dir_writes_summary_and_evidence_files(tmp_path, monkeypatch):
    module = _load_script_module()
    session = _session()
    now = datetime.utcnow()
    session.execute(
        insert(FileContainer.__table__).values(
            id="fc-src-2",
            filename="part.step",
            file_type="step",
            system_path="3d/fc/fc-src-2.step",
        )
    )
    session.execute(
        insert(session.info["legacy_jobs_table"]).values(
            id="legacy-10",
            source_file_id="fc-src-2",
            target_format="png",
            operation_type="preview",
            status="pending",
            created_at=now,
        )
    )
    session.commit()

    monkeypatch.setattr(module, "_open_session", lambda tenant, org: session)
    monkeypatch.setattr(
        module,
        "collect_legacy_code_references",
        lambda repo_root: [
            module.LegacyCodeReferenceRow(
                path="src/yuantus/meta_engine/web/file_router.py",
                line_no=1,
                scope="production",
                kind="table_name",
                text="cad_conversion_jobs",
            )
        ],
    )
    out_dir = tmp_path / "evidence"

    exit_code = module.main(
        ["--out-dir", str(out_dir), "--detail-limit", "5", "--repo-root", str(tmp_path)]
    )

    assert exit_code == 0
    summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    jobs_rows = (out_dir / "jobs.jsonl").read_text(encoding="utf-8").splitlines()
    pending_rows = (out_dir / "pending.jsonl").read_text(encoding="utf-8").splitlines()
    anomalies_rows = (out_dir / "anomalies.jsonl").read_text(encoding="utf-8").splitlines()
    samples = json.loads((out_dir / "samples.json").read_text(encoding="utf-8"))
    code_refs = (out_dir / "code_references.jsonl").read_text(encoding="utf-8").splitlines()

    assert summary["job_count"] == 1
    assert summary["legacy_queue_drain_complete"] is False
    assert summary["code_reference_count"] == 1
    assert summary["blocking_production_reference_count"] == 1
    assert len(jobs_rows) == 1
    assert len(pending_rows) == 1
    assert anomalies_rows == []
    assert len(samples) == 1
    assert len(code_refs) == 1


def test_build_report_treats_legacy_model_table_definition_as_non_blocking():
    module = _load_script_module()
    refs = [
        module.LegacyCodeReferenceRow(
            path="src/yuantus/meta_engine/models/file.py",
            line_no=256,
            scope="production",
            kind="table_name",
            text='__tablename__ = "cad_conversion_jobs"',
        )
    ]

    report = module.build_report([], code_references=refs, legacy_table_present_flag=False)

    assert report["code_reference_count"] == 1
    assert report["blocking_production_reference_count"] == 1
    assert report["delete_window_ready"] is False
