from __future__ import annotations

from typing import Any, Optional

_PROFILE_LABELS = {
    "local": "local-baseline",
    "hybrid": "hybrid-auto",
    "external": "external-enterprise",
}

_PROFILE_ALIASES = {
    "auto": "auto",
    "local": "local",
    "local-baseline": "local",
    "hybrid": "hybrid",
    "hybrid-auto": "hybrid",
    "external": "external",
    "external-enterprise": "external",
}


def available_cad_backend_profiles() -> list[str]:
    return [
        _PROFILE_LABELS["local"],
        _PROFILE_LABELS["hybrid"],
        _PROFILE_LABELS["external"],
    ]


def normalize_cad_connector_mode(raw: Optional[str]) -> str:
    mode = (raw or "optional").strip().lower()
    if mode not in {"disabled", "optional", "required"}:
        return "optional"
    return mode


def normalize_cad_backend_profile(raw: Optional[str]) -> str:
    profile = (raw or "auto").strip().lower()
    return _PROFILE_ALIASES.get(profile, "auto")


def cad_backend_profile_source(settings: Any) -> str:
    profile = normalize_cad_backend_profile(
        getattr(settings, "CAD_CONVERSION_BACKEND_PROFILE", "auto")
    )
    return "profile" if profile != "auto" else "legacy-mode"


def configured_cad_backend_profile_name(settings: Any) -> str:
    profile = normalize_cad_backend_profile(
        getattr(settings, "CAD_CONVERSION_BACKEND_PROFILE", "auto")
    )
    if profile == "auto":
        return "auto"
    return _PROFILE_LABELS[profile]


def effective_cad_backend_profile(settings: Any) -> str:
    profile = normalize_cad_backend_profile(
        getattr(settings, "CAD_CONVERSION_BACKEND_PROFILE", "auto")
    )
    if profile != "auto":
        return profile

    connector_mode = normalize_cad_connector_mode(
        getattr(settings, "CAD_CONNECTOR_MODE", "optional")
    )
    connector_base_url = str(getattr(settings, "CAD_CONNECTOR_BASE_URL", "") or "").strip()
    if connector_base_url and connector_mode == "required":
        return "external"
    if connector_base_url and connector_mode != "disabled":
        return "hybrid"
    return "local"


def effective_cad_backend_profile_name(settings: Any) -> str:
    return _PROFILE_LABELS[effective_cad_backend_profile(settings)]


def cad_connector_enabled_for_profile(settings: Any) -> bool:
    effective = effective_cad_backend_profile(settings)
    if effective == "local":
        return False
    return bool(str(getattr(settings, "CAD_CONNECTOR_BASE_URL", "") or "").strip())


def cad_connector_failure_is_fatal(settings: Any) -> bool:
    return effective_cad_backend_profile(settings) == "external"
