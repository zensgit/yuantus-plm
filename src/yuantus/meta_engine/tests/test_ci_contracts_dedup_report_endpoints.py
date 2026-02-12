from __future__ import annotations

from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "src").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + src/)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_dedup_report_and_export_endpoints_exist() -> None:
    repo_root = _find_repo_root(Path(__file__))
    router_py = repo_root / "src" / "yuantus" / "meta_engine" / "web" / "dedup_router.py"
    service_py = repo_root / "src" / "yuantus" / "meta_engine" / "dedup" / "service.py"

    router_text = _read(router_py)
    assert '@dedup_router.get("/report"' in router_text, (
        "Dedup router must expose GET /api/v1/dedup/report for operational reporting."
    )
    assert '@dedup_router.get("/report/export")' in router_text, (
        "Dedup router must expose GET /api/v1/dedup/report/export for CSV export."
    )

    service_text = _read(service_py)
    assert "def generate_report(" in service_text, (
        "DedupService must implement generate_report(...) used by /dedup/report."
    )
    assert "def list_records_for_export(" in service_text, (
        "DedupService must implement list_records_for_export(...) used by /dedup/report/export."
    )
