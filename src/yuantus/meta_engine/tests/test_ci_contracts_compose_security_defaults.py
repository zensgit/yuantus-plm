from __future__ import annotations

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
    raise AssertionError("Could not locate repo root (expected pyproject.toml + docker-compose.yml)")


def _env_to_dict(env):
    if env is None:
        return {}
    if isinstance(env, dict):
        return env
    if isinstance(env, list):
        out = {}
        for item in env:
            if isinstance(item, str) and "=" in item:
                key, value = item.split("=", 1)
                out[key] = value
        return out
    raise AssertionError(f"Unexpected environment type: {type(env)}")


def test_compose_api_defaults_disable_plugin_autoload() -> None:
    repo_root = _find_repo_root(Path(__file__))
    doc = yaml.safe_load((repo_root / "docker-compose.yml").read_text(encoding="utf-8"))
    services = (doc or {}).get("services") or {}

    api_env = _env_to_dict((services.get("api") or {}).get("environment"))

    assert "false" in str(api_env.get("YUANTUS_PLUGINS_AUTOLOAD") or "").lower(), (
        "api compose defaults should keep plugin autoload disabled."
    )


def test_compose_cad_extractor_defaults_to_required_auth() -> None:
    repo_root = _find_repo_root(Path(__file__))
    doc = yaml.safe_load((repo_root / "docker-compose.yml").read_text(encoding="utf-8"))
    services = (doc or {}).get("services") or {}

    cad_extractor_env = _env_to_dict((services.get("cad-extractor") or {}).get("environment"))
    api_env = _env_to_dict((services.get("api") or {}).get("environment"))
    worker_env = _env_to_dict((services.get("worker") or {}).get("environment"))

    assert "required" in str(cad_extractor_env.get("CAD_EXTRACTOR_AUTH_MODE") or ""), (
        "cad-extractor should default to required auth in compose."
    )
    assert "CAD_EXTRACTOR_SERVICE_TOKEN" in str(
        cad_extractor_env.get("CAD_EXTRACTOR_SERVICE_TOKEN") or ""
    ), "cad-extractor should keep its bearer token configurable via CAD_EXTRACTOR_SERVICE_TOKEN."

    for service_name, env in (("api", api_env), ("worker", worker_env)):
        token = env.get("YUANTUS_CAD_EXTRACTOR_SERVICE_TOKEN")
        assert "CAD_EXTRACTOR_SERVICE_TOKEN" in str(token or ""), (
            f"{service_name} should source YUANTUS_CAD_EXTRACTOR_SERVICE_TOKEN from the shared "
            "CAD_EXTRACTOR_SERVICE_TOKEN variable so the internal caller and sidecar stay aligned."
        )
