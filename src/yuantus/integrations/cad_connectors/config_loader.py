from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .base import (
    CadConnector,
    CadConnectorInfo,
    StaticCadConnector,
    build_keyvalue_connector,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CadConnectorConfigEntry:
    connector: CadConnector
    replace: bool = False


@dataclass(frozen=True)
class CadConnectorLoadResult:
    entries: List[CadConnectorConfigEntry]
    errors: List[str]


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",")]
        return [item for item in items if item]
    if isinstance(value, Iterable):
        items = [str(item).strip() for item in value]
        return [item for item in items if item]
    return []


def _as_dict(value: Any) -> Dict[str, str]:
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items() if str(k).strip()}
    return {}


def load_connector_payload(payload: Any, *, source: str) -> CadConnectorLoadResult:
    if isinstance(payload, dict):
        connectors_payload = payload.get("connectors", [])
    elif isinstance(payload, list):
        connectors_payload = payload
    else:
        return CadConnectorLoadResult(
            entries=[],
            errors=[
                f"CAD connector config must be a list or {{\"connectors\": [...] }} ({source})"
            ],
        )

    entries: List[CadConnectorConfigEntry] = []
    errors: List[str] = []
    for idx, raw in enumerate(connectors_payload):
        if not isinstance(raw, dict):
            errors.append(f"Connector[{idx}] must be an object ({source})")
            continue

        connector_id = str(raw.get("id") or "").strip()
        label = str(raw.get("label") or "").strip()
        cad_format = str(raw.get("cad_format") or "").strip()
        document_type = str(raw.get("document_type") or "").strip()
        extensions = _as_list(raw.get("extensions"))

        if not connector_id or not label or not cad_format or not document_type:
            errors.append(f"Connector[{idx}] missing required fields ({source})")
            continue
        if not extensions:
            errors.append(f"Connector[{idx}] missing extensions ({source})")
            continue

        aliases = _as_list(raw.get("aliases"))
        signature_tokens = _as_list(raw.get("signature_tokens"))
        description = str(raw.get("description") or "").strip() or None
        priority_raw = raw.get("priority", 0)
        try:
            priority = int(priority_raw)
        except Exception:
            priority = 0

        kind = str(raw.get("kind") or raw.get("type") or "static").strip().lower()
        override = bool(raw.get("override"))

        info = CadConnectorInfo(
            id=connector_id,
            label=label,
            cad_format=cad_format,
            document_type=document_type,
            extensions=tuple(extensions),
            aliases=tuple(aliases),
            priority=priority,
            description=description,
            signature_tokens=tuple(signature_tokens),
        )

        if kind in {"keyvalue", "kv"}:
            key_aliases = _as_dict(raw.get("key_aliases"))
            connector = build_keyvalue_connector(
                connector_id=info.id,
                label=info.label,
                cad_format=info.cad_format,
                document_type=info.document_type,
                extensions=info.extensions,
                aliases=info.aliases,
                priority=info.priority,
                description=info.description,
                key_aliases=key_aliases,
                signature_tokens=info.signature_tokens,
            )
        else:
            attributes = _as_dict(raw.get("attributes"))
            connector = StaticCadConnector(info, attributes=attributes)

        entries.append(CadConnectorConfigEntry(connector=connector, replace=override))

    if errors:
        for err in errors:
            logger.warning("CAD connector config error: %s", err)

    return CadConnectorLoadResult(entries=entries, errors=errors)


def load_connector_config(path: Optional[str]) -> CadConnectorLoadResult:
    if not path:
        return CadConnectorLoadResult(entries=[], errors=[])

    config_path = Path(path).expanduser()
    if not config_path.exists():
        return CadConnectorLoadResult(
            entries=[],
            errors=[f"CAD connector config not found: {config_path}"],
        )

    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return CadConnectorLoadResult(
            entries=[],
            errors=[f"Failed to parse CAD connector config: {exc}"],
        )

    return load_connector_payload(payload, source=str(config_path))
