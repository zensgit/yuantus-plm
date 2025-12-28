from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from .base import CadConnector, CadConnectorInfo, normalize_cad_format


@dataclass(frozen=True)
class CadResolvedMetadata:
    cad_format: Optional[str]
    document_type: Optional[str]
    connector_id: Optional[str]


class CadConnectorRegistry:
    def __init__(self) -> None:
        self._by_id: Dict[str, CadConnector] = {}
        self._by_format: Dict[str, CadConnector] = {}
        self._by_extension: Dict[str, List[CadConnector]] = {}

    def clear(self) -> None:
        self._by_id.clear()
        self._by_format.clear()
        self._by_extension.clear()

    def _index_connector(self, connector: CadConnector) -> None:
        for fmt in connector.info.normalized_formats():
            existing = self._by_format.get(fmt)
            if existing is None or existing.info.priority <= connector.info.priority:
                self._by_format[fmt] = connector

        for ext in connector.info.normalized_extensions():
            group = self._by_extension.setdefault(ext, [])
            group.append(connector)
            group.sort(key=lambda item: item.info.priority, reverse=True)

    def _rebuild_indexes(self) -> None:
        self._by_format.clear()
        self._by_extension.clear()
        for connector in self._by_id.values():
            self._index_connector(connector)

    def register(self, connector: CadConnector, *, replace: bool = False) -> None:
        connector_id = connector.info.id
        if connector_id in self._by_id:
            if not replace:
                raise ValueError(f"Connector '{connector_id}' already registered")
            self._by_id.pop(connector_id, None)
            self._rebuild_indexes()
        self._by_id[connector_id] = connector
        self._index_connector(connector)

    def list(self) -> List[CadConnectorInfo]:
        return [connector.info for connector in self._by_id.values()]

    def find_by_format(self, cad_format: str) -> Optional[CadConnector]:
        normalized = normalize_cad_format(cad_format)
        if not normalized:
            return None
        return self._by_format.get(normalized)

    def find_by_id(self, connector_id: str) -> Optional[CadConnector]:
        if not connector_id:
            return None
        return self._by_id.get(connector_id)

    def find_by_extension(self, extension: str) -> Optional[CadConnector]:
        ext = extension.lower().lstrip(".")
        candidates = self._by_extension.get(ext)
        if not candidates:
            return None
        return candidates[0]

    def detect_by_content(
        self,
        content: Optional[bytes],
        *,
        filename: Optional[str] = None,
        source_system: Optional[str] = None,
    ) -> Optional[CadConnector]:
        if not content and not filename and not source_system:
            return None

        text = ""
        if content:
            snippet = content[:65536]
            for encoding in ("utf-8", "utf-16", "latin-1"):
                try:
                    text = snippet.decode(encoding, errors="ignore")
                    break
                except Exception:
                    text = ""

        parts = []
        if source_system:
            parts.append(str(source_system))
        if filename:
            parts.append(str(filename))
        if text:
            parts.append(text)
        if not parts:
            return None

        haystack = "\n".join(parts).upper()
        best: Optional[CadConnector] = None
        best_score = (-1, -1, -1)
        for connector in self._by_id.values():
            tokens = connector.info.signature_tokens or ()
            if not tokens:
                continue
            hits = 0
            longest = 0
            for token in tokens:
                token_norm = normalize_cad_format(token) or str(token).strip().upper()
                if not token_norm:
                    continue
                if token_norm in haystack:
                    hits += 1
                    longest = max(longest, len(token_norm))
            if hits:
                score = (hits, longest, connector.info.priority)
                if score > best_score:
                    best = connector
                    best_score = score
        return best

    def resolve(self, cad_format: Optional[str], extension: Optional[str]) -> Optional[CadConnector]:
        if cad_format:
            by_format = self.find_by_format(cad_format)
            if by_format:
                return by_format
        if extension:
            return self.find_by_extension(extension)
        return None

    def resolve_metadata(
        self, cad_format: Optional[str], extension: Optional[str]
    ) -> CadResolvedMetadata:
        connector = self.resolve(cad_format, extension)
        if not connector:
            normalized = normalize_cad_format(cad_format)
            return CadResolvedMetadata(
                cad_format=normalized,
                document_type=None,
                connector_id=None,
            )
        return CadResolvedMetadata(
            cad_format=connector.info.cad_format,
            document_type=connector.info.document_type,
            connector_id=connector.info.id,
        )
