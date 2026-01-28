from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy.orm import Session

from yuantus.meta_engine.models.configuration import ConfigOption, ConfigOptionSet


class ConfigService:
    def __init__(self, session: Session):
        self.session = session

    def list_option_sets(self) -> List[ConfigOptionSet]:
        return (
            self.session.query(ConfigOptionSet)
            .order_by(ConfigOptionSet.name.asc())
            .all()
        )

    def get_option_set(self, option_set_id: str) -> Optional[ConfigOptionSet]:
        return self.session.get(ConfigOptionSet, option_set_id)

    def get_option_set_by_name(self, name: str) -> Optional[ConfigOptionSet]:
        return (
            self.session.query(ConfigOptionSet)
            .filter(ConfigOptionSet.name == name)
            .first()
        )

    def create_option_set(self, payload: Dict[str, Any]) -> ConfigOptionSet:
        name = (payload.get("name") or "").strip()
        if not name:
            raise ValueError("OptionSet name is required")

        existing = self.get_option_set_by_name(name)
        if existing:
            raise ValueError(f"OptionSet name already exists: {name}")

        option_set = ConfigOptionSet(
            id=payload.get("id") or str(uuid.uuid4()),
            name=name,
            label=payload.get("label") or name,
            description=payload.get("description"),
            item_type_id=payload.get("item_type_id"),
            is_active=bool(payload.get("is_active", True)),
            config=payload.get("config") or {},
        )
        self.session.add(option_set)
        self.session.flush()
        return option_set

    def update_option_set(self, option_set: ConfigOptionSet, payload: Dict[str, Any]) -> ConfigOptionSet:
        if "name" in payload and payload["name"]:
            name = payload["name"].strip()
            if name != option_set.name:
                existing = self.get_option_set_by_name(name)
                if existing and existing.id != option_set.id:
                    raise ValueError(f"OptionSet name already exists: {name}")
                option_set.name = name
        if "label" in payload:
            option_set.label = payload.get("label")
        if "description" in payload:
            option_set.description = payload.get("description")
        if "item_type_id" in payload:
            option_set.item_type_id = payload.get("item_type_id")
        if "is_active" in payload:
            option_set.is_active = bool(payload.get("is_active"))
        if "config" in payload:
            option_set.config = payload.get("config") or {}
        self.session.add(option_set)
        self.session.flush()
        return option_set

    def delete_option_set(self, option_set: ConfigOptionSet, force: bool = False) -> None:
        if option_set.options and not force:
            raise ValueError("OptionSet has options; use force=1 to delete")
        self.session.delete(option_set)
        self.session.flush()

    def add_option(self, option_set: ConfigOptionSet, payload: Dict[str, Any]) -> ConfigOption:
        key = (payload.get("key") or "").strip()
        if not key:
            raise ValueError("Option key is required")

        existing = (
            self.session.query(ConfigOption)
            .filter(
                ConfigOption.option_set_id == option_set.id,
                ConfigOption.key == key,
            )
            .first()
        )
        if existing:
            raise ValueError(f"Option key already exists: {key}")

        option = ConfigOption(
            id=payload.get("id") or str(uuid.uuid4()),
            option_set_id=option_set.id,
            key=key,
            label=payload.get("label") or key,
            value=payload.get("value") or key,
            sort_order=int(payload.get("sort_order") or 0),
            is_default=bool(payload.get("is_default", False)),
            extra=payload.get("extra"),
        )
        self.session.add(option)
        self.session.flush()
        return option

    def update_option(self, option: ConfigOption, payload: Dict[str, Any]) -> ConfigOption:
        if "key" in payload and payload["key"]:
            key = payload["key"].strip()
            if key != option.key:
                existing = (
                    self.session.query(ConfigOption)
                    .filter(
                        ConfigOption.option_set_id == option.option_set_id,
                        ConfigOption.key == key,
                    )
                    .first()
                )
                if existing and existing.id != option.id:
                    raise ValueError(f"Option key already exists: {key}")
                option.key = key
        if "label" in payload:
            option.label = payload.get("label")
        if "value" in payload:
            option.value = payload.get("value")
        if "sort_order" in payload:
            option.sort_order = int(payload.get("sort_order") or 0)
        if "is_default" in payload:
            option.is_default = bool(payload.get("is_default"))
        if "extra" in payload:
            option.extra = payload.get("extra")
        self.session.add(option)
        self.session.flush()
        return option

    def delete_option(self, option: ConfigOption) -> None:
        self.session.delete(option)
        self.session.flush()
