from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
GRAPHQL_DIR = REPO_ROOT / "yuantus" / "meta_engine" / "web" / "graphql"


def test_graphql_loaders_use_item_number_helper_for_number_fields() -> None:
    text = (GRAPHQL_DIR / "loaders.py").read_text(encoding="utf-8")

    assert "from yuantus.meta_engine.services.item_number_keys import get_item_number" in text
    assert "number=get_item_number(props) or getattr(item, \"number\", None)" in text
    assert "parent_number=get_item_number(parent_props) if parent else None" in text


def test_graphql_schema_uses_shared_number_filter_and_canonical_component_number() -> None:
    text = (GRAPHQL_DIR / "schema.py").read_text(encoding="utf-8")

    assert "ITEM_NUMBER_READ_KEYS" in text
    assert "def _item_number_filter_clause" in text
    assert "query = query.where(_item_number_filter_clause(Item, filter.number))" in text
    assert "component_number=get_item_number(child_props)" in text
