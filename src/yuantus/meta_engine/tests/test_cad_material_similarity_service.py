"""Phase 2 — unit tests for cad_material_similarity_service (scorer + read-only fetch)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from yuantus.models.base import Base
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType  # noqa: F401 (FK target registration)
from yuantus.meta_engine.lifecycle.models import LifecycleState  # noqa: F401 (FK target registration)
from yuantus.meta_engine.services import cad_material_similarity_service as sim

BAR_PROFILE = {
    "profile_id": "bar",
    "item_type": "Part",
    "compose": {"target": "specification", "template": "Φ{diameter}*{length}"},
}
TUBE_PROFILE = {
    "profile_id": "tube",
    "item_type": "Part",
    "compose": {
        "target": "specification",
        "template": "Φ{outer_diameter}*{wall_thickness}*{length}",
    },
}


# --------------------------------------------------------------------------- #
# pure scorer
# --------------------------------------------------------------------------- #
def test_identical_scores_one_with_contributions():
    props = {"material_category": "bar", "material": "Q235", "diameter": 20, "length": 100}
    result = sim.score_candidate(BAR_PROFILE, props, dict(props))
    assert result["score"] == 1.0
    assert "material_category" in result["field_contributions"]
    assert sim.DIMENSION_KEY in result["field_contributions"]


def test_same_category_different_size_drops_out_of_high_band():
    # §6.3: Φ20*100 vs Φ25*100 必须跌出 0.90 高相似带，但仍是候选(>=0.75)。
    target = {"material_category": "bar", "material": "Q235", "diameter": 20, "length": 100}
    candidate = {"material_category": "bar", "material": "Q235", "diameter": 25, "length": 100}
    score = sim.score_candidate(BAR_PROFILE, target, candidate)["score"]
    assert sim.CANDIDATE_THRESHOLD <= score < sim.HIGH_SIMILAR_THRESHOLD


def test_near_identical_size_is_high_similar():
    target = {"material_category": "bar", "material": "Q235", "diameter": 20, "length": 100}
    candidate = {"material_category": "bar", "material": "Q235", "diameter": 20.3, "length": 100}
    assert sim.score_candidate(BAR_PROFILE, target, candidate)["score"] >= sim.HIGH_SIMILAR_THRESHOLD


def test_dimension_is_numeric_not_spec_token_overlap():
    # specification token 高度重叠（共享 "Φ" 和 "100"），但直径数值不同 → 不得判高相似。
    target = {"material_category": "bar", "material": "Q235", "diameter": 20, "length": 100,
              "specification": "Φ20*100"}
    candidate = {"material_category": "bar", "material": "Q235", "diameter": 50, "length": 100,
                 "specification": "Φ50*100"}
    score = sim.score_candidate(BAR_PROFILE, target, candidate)["score"]
    assert score < sim.HIGH_SIMILAR_THRESHOLD


def test_input_normalization_category_alias_not_silently_dropped():
    # target 用 `category`（非 material_category）；归一后必须参与评分（contributions 含该键）。
    target = {"category": "bar", "material": "Q235", "diameter": 20, "length": 100}
    candidate = {"material_category": "bar", "material": "Q235", "diameter": 20, "length": 100}
    result = sim.score_candidate(BAR_PROFILE, target, candidate)
    assert "material_category" in result["field_contributions"]
    assert result["field_contributions"]["material_category"] == 1.0
    assert result["score"] == 1.0


def test_input_normalization_finish_standard_to_finish():
    target = {"material_category": "bar", "material": "Q235", "diameter": 20, "length": 100,
              "finish_standard": "galvanized"}
    candidate = {"material_category": "bar", "material": "Q235", "diameter": 20, "length": 100,
                 "finish": "galvanized"}
    result = sim.score_candidate(BAR_PROFILE, target, candidate)
    assert result["field_contributions"].get("finish") == 1.0


def test_missing_fields_do_not_lower_score():
    # 目标只有部分字段；缺字段不计入分母，identical 子集仍得满分。
    target = {"material_category": "bar", "material": "Q235", "diameter": 20, "length": 100}
    candidate = dict(target)
    candidate["name"] = "some name only on candidate"  # 单侧有值 → 不计入
    assert sim.score_candidate(BAR_PROFILE, target, candidate)["score"] == 1.0


# --------------------------------------------------------------------------- #
# read-only fetch + orchestration
# --------------------------------------------------------------------------- #
@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=[Item.__table__])
    session = sessionmaker(bind=engine)()
    rows = [
        ("p1", "Part", {"material_category": "bar", "material": "Q235", "diameter": 20, "length": 100}),
        ("p2", "Part", {"material_category": "bar", "material": "Q235", "diameter": 25, "length": 100}),
        ("p3", "Part", {"material_category": "bar", "material": "Q345", "diameter": 20, "length": 100}),
        ("p4", "Part", {"material_category": "tube", "material": "Q235", "outer_diameter": 20}),
        ("w1", "Widget", {"material_category": "bar", "material": "Q235", "diameter": 20, "length": 100}),
    ]
    for rid, itype, props in rows:
        session.add(Item(id=rid, item_type_id=itype, config_id=rid, generation=1,
                         is_current=True, properties=props))
    session.commit()
    yield session
    session.close()


def test_fetch_is_read_only_and_item_type_scoped(db):
    before = db.query(Item).count()
    target = {"material_category": "bar", "material": "Q235"}
    items, truncated = sim.fetch_similar_candidates(db, BAR_PROFILE, target)
    # read-only: no row delta
    assert db.query(Item).count() == before
    ids = {i.id for i in items}
    assert "w1" not in ids  # Widget excluded by item_type
    assert "p4" not in ids  # tube material_category != bar
    assert {"p1", "p2"} <= ids  # bar + Q235 anchor


def test_fetch_excludes_exact_match_ids(db):
    target = {"material_category": "bar", "material": "Q235"}
    items, _ = sim.fetch_similar_candidates(db, BAR_PROFILE, target, exclude_ids=["p1"])
    assert "p1" not in {i.id for i in items}


def test_fetch_no_anchor_returns_empty_not_full_scan(db):
    items, _ = sim.fetch_similar_candidates(db, BAR_PROFILE, {"name": "no anchor"})
    assert items == []


def test_find_similar_ranks_and_thresholds(db):
    target = {"material_category": "bar", "material": "Q235", "diameter": 20, "length": 100}
    result = sim.find_similar(db, BAR_PROFILE, target, exclude_ids=["p1"])
    cands = result["candidates"]
    assert cands, "expected at least one similar candidate"
    # p2 (Φ25) should be a candidate but not high-similar
    by_id = {c["id"]: c for c in cands}
    assert "p2" in by_id
    assert by_id["p2"]["high_similar"] is False
    # scores are sorted descending
    assert [c["score"] for c in cands] == sorted((c["score"] for c in cands), reverse=True)
