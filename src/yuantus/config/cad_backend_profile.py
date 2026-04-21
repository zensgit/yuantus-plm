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

_STEP_IGES_BACKEND_ALIASES = {
    "auto": "auto",
    "local": "local",
    "local-baseline": "local",
    "builtin": "local",
    "built-in": "local",
    "connector": "connector",
    "external": "connector",
    "external-enterprise": "connector",
}


def available_cad_backend_profiles() -> list[str]:
    return [
        _PROFILE_LABELS["local"],
        _PROFILE_LABELS["hybrid"],
        _PROFILE_LABELS["external"],
    ]


def available_cad_step_iges_backends() -> list[str]:
    return ["auto", "local", "connector"]


def normalize_cad_connector_mode(raw: Optional[str]) -> str:
    mode = (raw or "optional").strip().lower()
    if mode not in {"disabled", "optional", "required"}:
        return "optional"
    return mode


def normalize_cad_backend_profile(raw: Optional[str]) -> str:
    profile = (raw or "auto").strip().lower()
    return _PROFILE_ALIASES.get(profile, "auto")


def normalize_cad_step_iges_backend(raw: Optional[str]) -> str:
    backend = (raw or "auto").strip().lower()
    return _STEP_IGES_BACKEND_ALIASES.get(backend, "auto")


def configured_cad_step_iges_backend_name(settings: Any) -> str:
    return normalize_cad_step_iges_backend(
        getattr(settings, "CAD_STEP_IGES_BACKEND", "auto")
    )


def _profile_label(value: Optional[str]) -> str:
    normalized = normalize_cad_backend_profile(value)
    if normalized == "auto":
        return ""
    return _PROFILE_LABELS[normalized]


def effective_cad_step_iges_backend(
    settings: Any, *, effective_profile: Optional[str] = None
) -> str:
    profile = _profile_label(effective_profile) or effective_cad_backend_profile_name(
        settings
    )
    if profile == "local-baseline":
        return "local"
    if profile == "external-enterprise":
        return "connector"

    configured = configured_cad_step_iges_backend_name(settings)
    if configured != "auto":
        return configured

    if profile == "hybrid-auto" and cad_connector_base_url_configured(settings):
        return "connector"
    return "local"


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


def cad_connector_base_url_configured(settings: Any) -> bool:
    return bool(str(getattr(settings, "CAD_CONNECTOR_BASE_URL", "") or "").strip())


def cad_connector_enabled_for_profile(settings: Any) -> bool:
    effective = effective_cad_backend_profile(settings)
    if effective == "local":
        return False
    return cad_connector_base_url_configured(settings)


def cad_connector_failure_is_fatal(settings: Any) -> bool:
    return effective_cad_backend_profile(settings) == "external"
