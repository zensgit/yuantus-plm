from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.numbering import NumberingSequence
from yuantus.meta_engine.services.numbering_service import (
    NumberingRule,
    NumberingService,
    NumberingScope,
    make_item_type,
)
from yuantus.models.base import Base


def test_apply_generates_item_number_when_missing() -> None:
    session = MagicMock()
    service = NumberingService(session)
    item_type = make_item_type("Part")

    with patch.object(service, "_allocate_counter", return_value=1):
        props = service.apply(item_type, {"name": "Bracket"})

    assert props["item_number"] == "PART-000001"
    assert props["number"] == "PART-000001"


def test_apply_keeps_explicit_item_number() -> None:
    session = MagicMock()
    service = NumberingService(session)
    item_type = make_item_type("Part")

    with patch.object(service, "_allocate_counter") as allocate:
        props = service.apply(item_type, {"item_number": "P-100", "name": "Bracket"})

    allocate.assert_not_called()
    assert props["item_number"] == "P-100"
    assert props["number"] == "P-100"


def test_apply_promotes_explicit_legacy_number_to_canonical_item_number() -> None:
    session = MagicMock()
    service = NumberingService(session)
    item_type = make_item_type("Part")

    props = service.apply(item_type, {"number": "LEG-9", "name": "Legacy Part"})

    assert props["item_number"] == "LEG-9"
    assert props["number"] == "LEG-9"


def test_resolve_rule_rejects_missing_prefix_for_custom_type() -> None:
    session = MagicMock()
    service = NumberingService(session)

    with pytest.raises(ValueError, match="numbering prefix is required"):
        service.resolve_rule(make_item_type("Custom Part", numbering={"enabled": True}))


def test_resolve_rule_rejects_invalid_width() -> None:
    session = MagicMock()
    service = NumberingService(session)

    with pytest.raises(ValueError, match="numbering width/start must be integers"):
        service.resolve_rule(make_item_type("Part", numbering={"width": "oops"}))


def test_generate_dispatches_to_postgresql_branch() -> None:
    session = MagicMock()
    bind = MagicMock()
    bind.dialect.name = "postgresql"
    session.get_bind.return_value = bind
    service = NumberingService(session)

    with patch.object(service, "_allocate_counter_postgresql", return_value=17) as allocate:
        value = service.generate(make_item_type("Part"))

    allocate.assert_called_once()
    assert value == "PART-000017"


def test_generate_dispatches_to_generic_branch_for_other_dialects() -> None:
    session = MagicMock()
    bind = MagicMock()
    bind.dialect.name = "mysql"
    session.get_bind.return_value = bind
    service = NumberingService(session)

    with patch.object(service, "_allocate_counter_generic", return_value=19) as allocate:
        value = service.generate(make_item_type("Part"))

    allocate.assert_called_once()
    assert value == "PART-000019"


def test_generic_allocation_retries_after_insert_race() -> None:
    session = MagicMock()
    service = NumberingService(session)
    query = session.query.return_value.filter.return_value
    query.one_or_none.side_effect = [None, None]
    savepoint1 = MagicMock()
    savepoint2 = MagicMock()
    session.begin_nested.side_effect = [savepoint1, savepoint2]
    session.flush.side_effect = [
        IntegrityError("insert", {}, Exception("duplicate")),
        None,
    ]

    with patch.object(
        service,
        "_scope",
        return_value=NumberingScope(tenant_id="tenant-1", org_id="org-1"),
    ):
        value = service._allocate_counter_generic(
            item_type_id="Part",
            rule=NumberingRule(prefix="PART-", width=6, start=1),
        )

    assert value == 1
    savepoint1.rollback.assert_called_once()
    savepoint2.commit.assert_called_once()
    session.expire_all.assert_called_once()


def test_generic_allocation_retries_after_conflicting_update() -> None:
    session = MagicMock()
    service = NumberingService(session)
    query = session.query.return_value.filter.return_value
    query.one_or_none.side_effect = [
        SimpleNamespace(last_value=4),
        SimpleNamespace(last_value=5),
    ]
    session.execute.side_effect = [
        SimpleNamespace(rowcount=0),
        SimpleNamespace(rowcount=1),
    ]

    with patch.object(
        service,
        "_scope",
        return_value=NumberingScope(tenant_id="tenant-1", org_id="org-1"),
    ):
        value = service._allocate_counter_generic(
            item_type_id="Part",
            rule=NumberingRule(prefix="PART-", width=6, start=1),
        )

    assert value == 6
    session.expire_all.assert_called_once()


def test_sqlite_allocation_is_monotonic_and_unique_under_parallel_calls(tmp_path: Path) -> None:
    db_path = tmp_path / "numbering.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine, tables=[NumberingSequence.__table__])
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    item_type = make_item_type("Part")

    def _worker() -> str:
        session = SessionLocal()
        try:
            value = NumberingService(session).generate(item_type)
            session.commit()
            return value
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=8) as executor:
        values = list(executor.map(lambda _: _worker(), range(8)))

    assert sorted(values) == [f"PART-{idx:06d}" for idx in range(1, 9)]


def test_floor_allocated_value_bootstraps_from_existing_item_numbers() -> None:
    session = MagicMock()
    service = NumberingService(session)
    session.query.return_value.filter.return_value.all.return_value = [
        SimpleNamespace(properties={"item_number": "PART-000017"}),
        SimpleNamespace(properties={"number": "PART-000003"}),
        SimpleNamespace(properties={"item_number": "DOC-000099"}),
        SimpleNamespace(properties={"item_number": "PART-ABC"}),
    ]

    value = service._floor_allocated_value(
        item_type_id="Part",
        rule=NumberingRule(prefix="PART-", width=6, start=1),
    )

    assert value == 18
    session.query.assert_called_once_with(Item)


def test_floor_allocated_value_uses_python_fallback_for_non_sqlite_postgresql() -> None:
    session = MagicMock()
    bind = MagicMock()
    bind.dialect.name = "mysql"
    session.get_bind.return_value = bind
    service = NumberingService(session)

    with patch.object(service, "_floor_allocated_value_python", return_value=18) as fallback:
        value = service._floor_allocated_value(
            item_type_id="Part",
            rule=NumberingRule(prefix="PART-", width=6, start=1),
        )

    fallback.assert_called_once_with(
        item_type_id="Part",
        rule=NumberingRule(prefix="PART-", width=6, start=1),
    )
    assert value == 18


def test_floor_allocated_value_sqlite_uses_db_aggregation(tmp_path: Path) -> None:
    db_path = tmp_path / "numbering-floor.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine, tables=[Item.__table__])
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    try:
        session.add_all(
            [
                Item(
                    id="item-1",
                    item_type_id="Part",
                    config_id="cfg-1",
                    properties={"item_number": "PART-000017"},
                ),
                Item(
                    id="item-2",
                    item_type_id="Part",
                    config_id="cfg-2",
                    properties={"number": "PART-000021"},
                ),
                Item(
                    id="item-3",
                    item_type_id="Part",
                    config_id="cfg-3",
                    properties={"item_number": "PART-ABC"},
                ),
                Item(
                    id="item-4",
                    item_type_id="Part",
                    config_id="cfg-4",
                    properties={"item_number": " DOC-000999 "},
                ),
                Item(
                    id="item-5",
                    item_type_id="Document",
                    config_id="cfg-5",
                    properties={"item_number": "PART-999999"},
                ),
            ]
        )
        session.commit()

        service = NumberingService(session)
        with patch.object(
            service,
            "_floor_allocated_value_python",
            side_effect=AssertionError("python fallback should not be used for sqlite"),
        ):
            value = service._floor_allocated_value(
                item_type_id="Part",
                rule=NumberingRule(prefix="PART-", width=6, start=1),
            )

        assert value == 22
    finally:
        session.close()


def test_generate_sqlite_respects_db_floor_without_python_scan(tmp_path: Path) -> None:
    db_path = tmp_path / "numbering-generate.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine, tables=[Item.__table__, NumberingSequence.__table__])
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    try:
        session.add(
            Item(
                id="item-1",
                item_type_id="Part",
                config_id="cfg-1",
                properties={"item_number": "PART-000020"},
            )
        )
        session.commit()

        service = NumberingService(session)
        with patch.object(
            service,
            "_floor_allocated_value_python",
            side_effect=AssertionError("python fallback should not be used for sqlite"),
        ):
            value = service.generate(make_item_type("Part"))
            session.commit()

        assert value == "PART-000021"
    finally:
        session.close()


def test_generic_allocation_respects_existing_item_number_floor_when_sequence_lags() -> None:
    session = MagicMock()
    service = NumberingService(session)

    row_query = MagicMock()
    item_query = MagicMock()

    def _query(model):
        if model is NumberingSequence:
            return row_query
        if model is Item:
            return item_query
        raise AssertionError(f"unexpected query model: {model}")

    session.query.side_effect = _query
    row_query.filter.return_value.one_or_none.return_value = SimpleNamespace(last_value=2)
    item_query.filter.return_value.all.return_value = [
        SimpleNamespace(properties={"item_number": "PART-000020"})
    ]
    session.execute.return_value = SimpleNamespace(rowcount=1)

    with patch.object(
        service,
        "_scope",
        return_value=NumberingScope(tenant_id="tenant-1", org_id="org-1"),
    ):
        value = service._allocate_counter_generic(
            item_type_id="Part",
            rule=NumberingRule(prefix="PART-", width=6, start=1),
        )

    assert value == 21
    session.flush.assert_called_once()
