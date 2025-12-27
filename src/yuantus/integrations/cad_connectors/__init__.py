from typing import Optional

from .base import (
    CadConnector,
    CadConnectorInfo,
    KeyValueCadConnector,
    build_keyvalue_connector,
    normalize_cad_format,
    resolve_cad_sync_key,
)
from .builtin import register_builtin_connectors
from .config_loader import CadConnectorLoadResult, load_connector_config, load_connector_payload
from .registry import CadConnectorRegistry, CadResolvedMetadata
from yuantus.config import get_settings

registry = CadConnectorRegistry()


def reload_connectors(
    config_path: Optional[str] = None,
    *,
    config_payload: Optional[object] = None,
) -> CadConnectorLoadResult:
    registry.clear()
    register_builtin_connectors(registry)

    settings = get_settings()
    path = config_path if config_path is not None else settings.CAD_CONNECTORS_CONFIG_PATH
    if config_payload is not None:
        result = load_connector_payload(config_payload, source="inline")
    else:
        result = load_connector_config(path)
    for entry in result.entries:
        registry.register(entry.connector, replace=entry.replace)
    return result


reload_connectors()

__all__ = [
    "CadConnector",
    "CadConnectorInfo",
    "KeyValueCadConnector",
    "CadConnectorRegistry",
    "CadResolvedMetadata",
    "build_keyvalue_connector",
    "normalize_cad_format",
    "resolve_cad_sync_key",
    "reload_connectors",
    "registry",
]
