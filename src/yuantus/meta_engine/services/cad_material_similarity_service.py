"""
CAD Material similarity — field-weighted fuzzy scoring for the assistant (Phase 2).

取数与评分分离：
- `score_candidate` / `find_similar` 的评分部分是纯函数，作用于已解析 profile dict + properties。
- `fetch_similar_candidates` 是**只读** Item 查询（item_type 限定、material_category+material 宽松
  anchor、排除 exact-match ids、上限、稳定排序），不写任何业务表。

字段相似只做模糊排序；精确/高置信命中仍由
`cad_material_sync_service._find_matching_items` 负责。键名归一（category→material_category、
finish_standard→finish）避免错配被"空字段不计入分母"静默吞权重。量纲字段从 compose template
发现，数值感知比较优先于对 specification 的 token overlap。
"""
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import String, cast  # noqa: F401  (String/cast used via _json_text reuse)

from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.cad_material_sync_service import (
    _is_blank,
    _json_text,
    _template_fields,
)

DIMENSION_KEY = "_dimensions"

# 权重合计 1.00；按双方都有值的字段重归一（缺字段不计入分子与分母）。
SIMILARITY_WEIGHTS: Dict[str, float] = {
    "material_category": 0.18,
    "material": 0.22,
    DIMENSION_KEY: 0.30,
    "name": 0.10,
    "finish": 0.10,
    "heat_treatment": 0.05,
    "description": 0.05,
}

ENUM_FIELDS = ("material_category", "finish", "heat_treatment")
TEXT_FIELDS = ("name", "description")

CANDIDATE_THRESHOLD = 0.75
HIGH_SIMILAR_THRESHOLD = 0.90
DIMENSION_TOLERANCE = 0.02
CANDIDATE_CAP = 200
TOP_N = 10

_SUMMARY_KEYS = (
    "item_number",
    "drawing_no",
    "material_code",
    "material_category",
    "material",
    "specification",
    "name",
)
_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


# --------------------------------------------------------------------------- #
# input normalization (约束 4)
# --------------------------------------------------------------------------- #
def normalize_similarity_input(props: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """归一别名：category/material_profile→material_category；finish_standard 作为
    finish 的 companion（仅当 finish 缺失时回填）。返回新 dict，不改原值。"""
    out = dict(props or {})
    if _is_blank(out.get("material_category")):
        for alias in ("category", "material_profile"):
            if not _is_blank(out.get(alias)):
                out["material_category"] = out[alias]
                break
    if _is_blank(out.get("finish")) and not _is_blank(out.get("finish_standard")):
        out["finish"] = out["finish_standard"]
    return out


# --------------------------------------------------------------------------- #
# field comparison
# --------------------------------------------------------------------------- #
def _norm_text(value: Any) -> str:
    return " ".join(str(value).strip().lower().split())


def _enum_score(a: Any, b: Any) -> float:
    return 1.0 if _norm_text(a) == _norm_text(b) and _norm_text(a) else 0.0


def _token_jaccard(a: Any, b: Any) -> float:
    ta, tb = set(_norm_text(a).split()), set(_norm_text(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _text_score(a: Any, b: Any) -> float:
    return _token_jaccard(a, b)


def _material_score(a: Any, b: Any) -> float:
    na, nb = _norm_text(a), _norm_text(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if na.startswith(nb) or nb.startswith(na):
        return 0.6
    return _token_jaccard(a, b)


def _all_numbers(value: Any) -> List[float]:
    if value is None:
        return []
    return [float(m) for m in _NUMBER_RE.findall(str(value))]


def _number_seq_close(nums_a: List[float], nums_b: List[float]) -> float:
    """比较两组数字序列：任一空或个数不同记 0（量纲结构不同，如 blank_size
    "20*100" vs "20*100*5"），否则逐位取最差维(min)。数值字段自然退化为单元素序列。"""
    if not nums_a or not nums_b or len(nums_a) != len(nums_b):
        return 0.0
    return min(_num_close(x, y) for x, y in zip(nums_a, nums_b))


def _num_close(a: float, b: float) -> float:
    scale = max(abs(a), abs(b))
    if scale == 0:
        return 1.0 if a == b else 0.0
    rel = abs(a - b) / scale
    if rel <= DIMENSION_TOLERANCE:
        return 1.0
    # 超容差线性衰减；斜率 2 使一个 ~25% 偏差的维落到 ~0.5，配合 min 让
    # "同类不同尺寸"跌出 0.90 高相似带（满足 §6.3 验收）。
    return max(0.0, 1.0 - 2.0 * rel)


def _dimension_fields(profile: Dict[str, Any]) -> List[str]:
    """量纲字段从 compose template 引用发现（不是按 type=number；forging.blank_size 是 string）。"""
    compose = profile.get("compose") or {}
    template = str(compose.get("template") or "")
    if not template:
        return []
    return _template_fields(template)


def _dimension_score(
    target: Dict[str, Any], candidate: Dict[str, Any], dim_fields: List[str]
) -> Tuple[float, bool]:
    """数值感知优先；仅当拆分量纲两侧都取不到数值时，回退 specification（先正则抽数值，再 token）。
    每个量纲字段抽**完整数字序列**比较（blank_size="20*100" 这类字符串量纲含多个数字，不能只取首位），
    再跨字段取**最差维(min)**：所有维都得对上才算高相似（满足 §6.3，与 #701 §3.3.3 的"均值"不同——
    均值会被未变维拉高、跌不出 0.90）。返回 (score, present)；present=False 表示该分量不参与重归一。"""
    per_dim: List[float] = []
    for field in dim_fields:
        nums_a = _all_numbers(target.get(field))
        nums_b = _all_numbers(candidate.get(field))
        if not nums_a or not nums_b:
            continue
        per_dim.append(_number_seq_close(nums_a, nums_b))
    if per_dim:
        return min(per_dim), True

    spec_a, spec_b = target.get("specification"), candidate.get("specification")
    if _is_blank(spec_a) or _is_blank(spec_b):
        return 0.0, False
    nums_a, nums_b = _all_numbers(spec_a), _all_numbers(spec_b)
    if nums_a and nums_b and len(nums_a) == len(nums_b):
        return _number_seq_close(nums_a, nums_b), True
    return _text_score(spec_a, spec_b), True


# --------------------------------------------------------------------------- #
# scoring (pure)
# --------------------------------------------------------------------------- #
def score_candidate(
    profile: Dict[str, Any],
    target_props: Dict[str, Any],
    candidate_props: Dict[str, Any],
) -> Dict[str, Any]:
    target = normalize_similarity_input(target_props)
    candidate = normalize_similarity_input(candidate_props)
    dim_fields = _dimension_fields(profile)

    contributions: Dict[str, float] = {}
    numerator = denominator = 0.0
    for field, weight in SIMILARITY_WEIGHTS.items():
        if field == DIMENSION_KEY:
            score, present = _dimension_score(target, candidate, dim_fields)
            if not present:
                continue
        else:
            a, b = target.get(field), candidate.get(field)
            if _is_blank(a) or _is_blank(b):
                continue
            if field in ENUM_FIELDS:
                score = _enum_score(a, b)
            elif field == "material":
                score = _material_score(a, b)
            else:
                score = _text_score(a, b)
        contributions[field] = round(score, 4)
        numerator += weight * score
        denominator += weight

    final = round(numerator / denominator, 4) if denominator else 0.0
    return {"score": final, "field_contributions": contributions}


def _summary(props: Dict[str, Any]) -> Dict[str, Any]:
    return {k: props.get(k) for k in _SUMMARY_KEYS if props.get(k) is not None}


# --------------------------------------------------------------------------- #
# candidate fetch (read-only) + orchestration
# --------------------------------------------------------------------------- #
def fetch_similar_candidates(
    db,
    profile: Dict[str, Any],
    target_props: Dict[str, Any],
    *,
    exclude_ids: Optional[List[str]] = None,
    cap: int = CANDIDATE_CAP,
) -> Tuple[List[Any], bool]:
    """只读：item_type 限定 + material_category/material 宽松 anchor（退化到存在子集）+
    排除 exact-match ids + 稳定排序 + 上限。anchor 全空时返回零候选（不全表扫描）。
    返回 (items, truncated)。"""
    if db is None:
        return [], False
    target = normalize_similarity_input(target_props)
    item_type = str(profile.get("item_type") or "Part")

    anchor_keys = [
        key for key in ("material_category", "material") if not _is_blank(target.get(key))
    ]
    if not anchor_keys:
        return [], False

    query = db.query(Item).filter(Item.item_type_id == item_type)
    for key in anchor_keys:
        query = query.filter(_json_text(Item.properties[key]) == str(target[key]))
    if exclude_ids:
        query = query.filter(~Item.id.in_(list(exclude_ids)))
    query = query.order_by(Item.updated_at.desc(), Item.created_at.desc())

    rows = list(query.limit(cap + 1).all())
    truncated = len(rows) > cap
    return rows[:cap], truncated


def find_similar(
    db,
    profile: Dict[str, Any],
    target_props: Dict[str, Any],
    *,
    exclude_ids: Optional[List[str]] = None,
    top: int = TOP_N,
) -> Dict[str, Any]:
    """取候选 → 评分 → 过滤(>=0.75) → 稳定排序取 top。返回 candidates + 元信息。"""
    candidates, truncated = fetch_similar_candidates(
        db, profile, target_props, exclude_ids=exclude_ids
    )
    scored: List[Dict[str, Any]] = []
    for item in candidates:
        props = dict(getattr(item, "properties", None) or {})
        result = score_candidate(profile, target_props, props)
        if result["score"] < CANDIDATE_THRESHOLD:
            continue
        scored.append(
            {
                "id": getattr(item, "id", None),
                "score": result["score"],
                "high_similar": result["score"] >= HIGH_SIMILAR_THRESHOLD,
                "field_contributions": result["field_contributions"],
                "properties": _summary(props),
            }
        )
    # candidates 已按 updated_at/created_at 降序取出；stable sort by score 保留该次序为 tiebreak。
    scored.sort(key=lambda candidate: candidate["score"], reverse=True)
    return {
        "candidates": scored[:top],
        "truncated": truncated,
        "fetched": len(candidates),
    }
