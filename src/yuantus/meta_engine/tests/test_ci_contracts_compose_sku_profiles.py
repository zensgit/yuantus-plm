from __future__ import annotations

import subprocess
from pathlib import Path

import yaml


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "docker-compose.yml").is_file():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError(
        "Could not locate repo root (expected pyproject.toml + docker-compose.yml)"
    )


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8", errors="replace")) or {}


def _env_to_dict(env: object) -> dict[str, object]:
    if env is None:
        return {}
    if isinstance(env, dict):
        return dict(env)
    if isinstance(env, list):
        out: dict[str, object] = {}
        for item in env:
            if isinstance(item, str) and "=" in item:
                key, value = item.split("=", 1)
                out[key] = value
        return out
    raise AssertionError(f"Unexpected environment type: {type(env)}")


def test_compose_sku_profiles_define_expected_runtime_shapes() -> None:
    repo_root = _find_repo_root(Path(__file__))

    root_doc = _load_yaml(repo_root / "docker-compose.yml")
    base_doc = _load_yaml(repo_root / "docker-compose.profile-base.yml")
    collab_doc = _load_yaml(repo_root / "docker-compose.profile-collab.yml")
    combined_doc = _load_yaml(repo_root / "docker-compose.profile-combined.yml")

    root_services = (root_doc or {}).get("services") or {}
    for service_name in ("api", "worker", "postgres", "minio"):
        assert service_name in root_services, (
            "docker-compose.yml must keep the base Yuantus runtime intact before SKU overlays "
            f"are applied (missing service: {service_name})"
        )

    def assert_profile_env(doc: dict, expected_profile: str, expected_collab_flag: str) -> None:
        services = (doc or {}).get("services") or {}
        for service_name in ("api", "worker"):
            service = services.get(service_name) or {}
            env = _env_to_dict(service.get("environment"))
            assert env.get("YUANTUS_DELIVERY_PROFILE") == f"${{YUANTUS_DELIVERY_PROFILE:-{expected_profile}}}", (
                f"{service_name} should pin delivery profile to {expected_profile!r}"
            )
            assert env.get("YUANTUS_ENABLE_COLLAB") == f"${{YUANTUS_ENABLE_COLLAB:-{expected_collab_flag}}}", (
                f"{service_name} should set YUANTUS_ENABLE_COLLAB default to {expected_collab_flag!r}"
            )

    assert_profile_env(base_doc, "base", "false")
    assert_profile_env(collab_doc, "collab", "true")
    assert_profile_env(combined_doc, "combined", "true")

    combined_services = (combined_doc or {}).get("services") or {}
    for service_name in ("metasheet-postgres", "metasheet-redis", "backend", "web"):
        assert service_name in combined_services, (
            "docker-compose.profile-combined.yml must add the Metasheet sidecar runtime "
            f"(missing service: {service_name})"
        )

    backend = combined_services["backend"]
    backend_build = backend.get("build") or {}
    assert backend_build.get("context") == "${METASHEET2_ROOT:-../metasheet2}", (
        "combined profile backend must build from sibling metasheet2 checkout by default"
    )
    assert backend_build.get("dockerfile") == "Dockerfile.backend"

    backend_env = _env_to_dict(backend.get("environment"))
    for key, expected in {
        "PRODUCT_MODE": "plm-workbench",
        "ENABLE_PLM": "true",
        "PLM_BASE_URL": "http://api:7910",
        "PLM_API_MODE": "yuantus",
        "DATABASE_URL": "postgres://metasheet:metasheet@metasheet-postgres:5432/metasheet",
        "REDIS_HOST": "metasheet-redis",
        "REDIS_PORT": 6379,
    }.items():
        assert backend_env.get(key) == expected, (
            f"combined profile backend must set {key}={expected!r} for Yuantus federation wiring"
        )

    web = combined_services["web"]
    web_build = web.get("build") or {}
    assert web_build.get("context") == "${METASHEET2_ROOT:-../metasheet2}"
    assert web_build.get("dockerfile") == "Dockerfile.frontend"
    assert web.get("depends_on") == ["backend"], (
        "combined profile web service must depend on the Metasheet backend"
    )


def test_verify_compose_sku_profiles_script_is_documented_and_has_help() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "verify_compose_sku_profiles.sh"
    index_path = repo_root / "docs" / "DELIVERY_SCRIPTS_INDEX_20260202.md"

    assert script.is_file(), f"Missing script: {script}"
    assert index_path.is_file(), f"Missing scripts index: {index_path}"

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--help"],
        text=True,
        capture_output=True,
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = cp.stdout or ""
    for token in (
        "Usage:",
        "verify_compose_sku_profiles.sh",
        "--render PROFILE",
        "base",
        "collab",
        "combined",
        "METASHEET2_ROOT",
    ):
        assert token in out, f"help output missing token: {token}"

    index_text = index_path.read_text(encoding="utf-8", errors="replace")
    assert "verify_compose_sku_profiles.sh" in index_text, (
        "docs/DELIVERY_SCRIPTS_INDEX_20260202.md must include the compose SKU profile verifier"
    )
