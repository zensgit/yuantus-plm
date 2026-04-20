from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Optional
import uuid

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from yuantus.context import get_request_context
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.models.numbering import NumberingSequence
from yuantus.meta_engine.services.item_number_keys import (
    ensure_item_number_aliases,
    get_item_number,
)


DEFAULT_NUMBERING_RULES = {
    "Document": {"prefix": "DOC-", "width": 6, "start": 1},
    "Part": {"prefix": "PART-", "width": 6, "start": 1},
}


@dataclass(frozen=True)
class NumberingRule:
    prefix: str
    width: int
    start: int = 1


@dataclass(frozen=True)
class NumberingScope:
    tenant_id: str
    org_id: str


class NumberingService:
    def __init__(self, session: Session):
        self.session = session

    def apply(self, item_type: ItemType, properties: Optional[dict]) -> dict:
        props = dict(properties or {})
        explicit = get_item_number(props)
        if explicit:
            return ensure_item_number_aliases(props, explicit)

        generated = self.generate(item_type)
        if not generated:
            return props
        return ensure_item_number_aliases(props, generated)

    def generate(self, item_type: ItemType) -> Optional[str]:
        rule = self.resolve_rule(item_type)
        if rule is None:
            return None
        value = self._allocate_counter(item_type_id=item_type.id, rule=rule)
        return f"{rule.prefix}{value:0{rule.width}d}"

    def resolve_rule(self, item_type: ItemType) -> Optional[NumberingRule]:
        raw = self._raw_rule_config(item_type)
        if raw is None:
            default = DEFAULT_NUMBERING_RULES.get(item_type.id)
            if default is None:
                return None
            return NumberingRule(**default)

        if not isinstance(raw, dict):
            raise ValueError("ItemType.ui_layout.numbering must be an object")

        enabled = raw.get("enabled", True)
        if enabled is False:
            return None

        default = DEFAULT_NUMBERING_RULES.get(item_type.id, {})
        prefix = str(raw.get("prefix") or default.get("prefix") or "").strip()
        if not prefix:
            raise ValueError("numbering prefix is required")

        width = raw.get("width", default.get("width", 6))
        start = raw.get("start", default.get("start", 1))
        try:
            width_int = int(width)
            start_int = int(start)
        except (TypeError, ValueError) as exc:
            raise ValueError("numbering width/start must be integers") from exc

        if width_int <= 0:
            raise ValueError("numbering width must be > 0")
        if start_int <= 0:
            raise ValueError("numbering start must be > 0")

        return NumberingRule(prefix=prefix, width=width_int, start=start_int)

    def _raw_rule_config(self, item_type: ItemType) -> Optional[Any]:
        ui_layout = getattr(item_type, "ui_layout", None)
        if not isinstance(ui_layout, dict):
            return None
        return ui_layout.get("numbering")

    def _scope(self) -> NumberingScope:
        ctx = get_request_context()
        tenant_id = str(ctx.tenant_id).strip() if ctx.tenant_id else "default"
        org_id = str(ctx.org_id).strip() if ctx.org_id else "default"
        return NumberingScope(tenant_id=tenant_id or "default", org_id=org_id or "default")

    def _allocate_counter(self, *, item_type_id: str, rule: NumberingRule) -> int:
        bind = self.session.get_bind()
        dialect_name = getattr(getattr(bind, "dialect", None), "name", "")
        if dialect_name == "postgresql":
            return self._allocate_counter_postgresql(item_type_id=item_type_id, rule=rule)
        if dialect_name == "sqlite":
            return self._allocate_counter_sqlite(item_type_id=item_type_id, rule=rule)
        return self._allocate_counter_generic(item_type_id=item_type_id, rule=rule)

    def _allocate_counter_postgresql(self, *, item_type_id: str, rule: NumberingRule) -> int:
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        return self._allocate_counter_upsert(
            dialect_insert=pg_insert,
            item_type_id=item_type_id,
            rule=rule,
        )

    def _allocate_counter_sqlite(self, *, item_type_id: str, rule: NumberingRule) -> int:
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        return self._allocate_counter_upsert(
            dialect_insert=sqlite_insert,
            item_type_id=item_type_id,
            rule=rule,
        )

    def _allocate_counter_upsert(self, *, dialect_insert, item_type_id: str, rule: NumberingRule) -> int:
        scope = self._scope()
        now = datetime.utcnow()
        stmt = dialect_insert(NumberingSequence).values(
            id=str(uuid.uuid4()),
            item_type_id=item_type_id,
            tenant_id=scope.tenant_id,
            org_id=scope.org_id,
            prefix=rule.prefix,
            width=rule.width,
            last_value=rule.start,
            created_at=now,
            updated_at=now,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["item_type_id", "tenant_id", "org_id", "prefix"],
            set_={
                "last_value": NumberingSequence.last_value + 1,
                "width": rule.width,
                "updated_at": now,
            },
        )
        result = self.session.execute(stmt.returning(NumberingSequence.last_value))
        return int(result.scalar_one())

    def _allocate_counter_generic(self, *, item_type_id: str, rule: NumberingRule) -> int:
        scope = self._scope()
        filters = (
            NumberingSequence.item_type_id == item_type_id,
            NumberingSequence.tenant_id == scope.tenant_id,
            NumberingSequence.org_id == scope.org_id,
            NumberingSequence.prefix == rule.prefix,
        )

        for _ in range(8):
            row = (
                self.session.query(NumberingSequence)
                .filter(*filters)
                .one_or_none()
            )
            if row is None:
                nested = self.session.begin_nested()
                try:
                    row = NumberingSequence(
                        item_type_id=item_type_id,
                        tenant_id=scope.tenant_id,
                        org_id=scope.org_id,
                        prefix=rule.prefix,
                        width=rule.width,
                        last_value=rule.start,
                    )
                    self.session.add(row)
                    self.session.flush()
                    nested.commit()
                    return int(row.last_value)
                except IntegrityError:
                    nested.rollback()
                    self.session.expire_all()
                    continue

            previous = int(row.last_value)
            result = self.session.execute(
                update(NumberingSequence)
                .where(*filters, NumberingSequence.last_value == previous)
                .values(
                    last_value=previous + 1,
                    width=rule.width,
                    updated_at=datetime.utcnow(),
                )
            )
            if result.rowcount == 1:
                self.session.flush()
                return previous + 1

            self.session.expire_all()

        raise RuntimeError("Failed to allocate numbering sequence after retries")


def apply_auto_numbering(session: Session, item_type: ItemType, properties: Optional[dict]) -> dict:
    return NumberingService(session).apply(item_type, properties)


def make_item_type(item_type_id: str, *, numbering: Optional[dict] = None) -> Any:
    ui_layout = {"numbering": numbering} if numbering is not None else None
    return SimpleNamespace(id=item_type_id, ui_layout=ui_layout)
