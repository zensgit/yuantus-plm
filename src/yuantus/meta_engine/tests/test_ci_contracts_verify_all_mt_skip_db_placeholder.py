from __future__ import annotations

from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "scripts").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + scripts/)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_verify_all_avoids_mt_skip_placeholder_database_url() -> None:
    repo_root = _find_repo_root(Path(__file__))
    verify_all = repo_root / "scripts" / "verify_all.sh"
    assert verify_all.is_file(), f"Missing {verify_all}"
    text = _read(verify_all)

    assert "is_mt_skip_database_url()" in text, (
        "verify_all.sh should detect db-per-tenant-org placeholder DB URLs."
    )
    assert "yuantus_mt_skip.db" in text, (
        "verify_all.sh should explicitly recognize sqlite mt-skip placeholder pattern."
    )
    assert "ignoring placeholder YUANTUS_DATABASE_URL" in text, (
        "verify_all.sh should warn and ignore placeholder YUANTUS_DATABASE_URL."
    )
    assert "if ! is_mt_skip_database_url \"$DB_URL\"; then" in text, (
        "verify_all.sh should avoid deriving identity DB URL from mt-skip placeholder DB URL."
    )


def test_verify_all_can_resolve_postgres_port_from_running_api_compose_project() -> None:
    repo_root = _find_repo_root(Path(__file__))
    verify_all = repo_root / "scripts" / "verify_all.sh"
    assert verify_all.is_file(), f"Missing {verify_all}"
    text = _read(verify_all)

    assert "resolve_api_compose_project()" in text, (
        "verify_all.sh should detect compose project from running API container."
    )
    assert "resolve_postgres_port_line_from_api_project()" in text, (
        "verify_all.sh should probe postgres host port from the detected compose project."
    )
    assert "resolve_postgres_container_id_from_api_project()" in text, (
        "verify_all.sh should resolve postgres container id from the detected compose project."
    )
    assert "resolve_identity_db_name_for_runtime()" in text, (
        "verify_all.sh should resolve identity DB name from runtime postgres database list."
    )
    assert "yuantus_identity_mt_pg" in text and "yuantus_identity" in text, (
        "verify_all.sh should support both identity DB naming variants."
    )
    assert '--filter "publish=${base_port}"' in text, (
        "verify_all.sh should detect API container by published BASE_URL port."
    )
    assert "label=com.docker.compose.service=postgres" in text, (
        "verify_all.sh should locate postgres container from compose labels."
    )
    assert "DOCKER_POSTGRES_PORT_LINE=\"$(resolve_postgres_port_line_from_api_project || true)\"" in text, (
        "verify_all.sh should fallback to API-project-based postgres port probing when static compose probing fails."
    )
